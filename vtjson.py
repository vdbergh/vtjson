import datetime
import ipaddress
import math
import re
import urllib.parse

import dns.resolver
import email_validator
import idna


class ValidationError(Exception):
    pass


class SchemaError(Exception):
    pass


try:
    from types import GenericAlias as _GenericAlias
except ImportError:
    # For compatibility with older Pythons
    class _GenericAlias(type):
        pass


__version__ = "1.5.1"


_dns_resolver = None


def _get_dns_resolver():
    global _dns_resolver
    if _dns_resolver is not None:
        return _dns_resolver
    _dns_resolver = dns.resolver.Resolver()
    _dns_resolver.cache = dns.resolver.LRUCache()
    _dns_resolver.timeout = 10
    _dns_resolver.lifetime = 10
    return _dns_resolver


def _c(s):
    ss = str(s)
    if len(ss) > 0:
        c = ss[-1]
    else:
        c = ""
    if len(ss) < 120:
        ret = ss
    else:
        ret = f"{ss[:99]}...[TRUNCATED]..."
        if not isinstance(s, str) and c in r"])}":
            ret += c
    if isinstance(s, str):
        return repr(ret)
    else:
        return ret


def _wrong_type_message(object, name, type_name, explanation=None):
    message = f"{name} (value:{_c(object)}) is not of type '{type_name}'"
    if explanation is not None:
        message += f": {explanation}"
    return message


def _keys2(dict):
    ret = set()
    for k in dict:
        if isinstance(k, optional_key):
            ret.add((k.key, k, True))
        elif isinstance(k, str) and len(k) > 0 and k[-1] == "?":
            ret.add((k[:-1], k, True))
        else:
            ret.add((k, k, False))
    return ret


def _keys(dict):
    return {k[0] for k in _keys2(dict)}


class _validate_meta(type):
    def __instancecheck__(cls, object):
        valid = _validate(cls.__schema__, object, "object", strict=cls.__strict__)
        if cls.__debug__ and valid != "":
            print(f"DEBUG: {valid}")
        return valid == ""


def make_type(schema, name=None, strict=True, debug=False):
    if name is None:
        if hasattr(schema, "__name__"):
            name = schema.__name__
        else:
            name = "schema"
    return _validate_meta(
        name, (), {"__schema__": schema, "__strict__": strict, "__debug__": debug}
    )


class optional_key:
    def __init__(self, key):
        self.key = key

    def __eq__(self, key):
        return self.key == key.key

    def __hash__(self):
        return hash(self.key)


class union:
    def __init__(self, *schemas):
        self.schemas = [compile(s) for s in schemas]

    def __validate__(self, object, name, strict):
        messages = []
        for schema in self.schemas:
            message = schema.__validate__(object, name=name, strict=strict)
            if message == "":
                return ""
            else:
                messages.append(message)
        return " and ".join(messages)


class intersect:
    def __init__(self, *schemas):
        self.schemas = [compile(s) for s in schemas]

    def __validate__(self, object, name, strict):
        for schema in self.schemas:
            message = schema.__validate__(object, name=name, strict=strict)
            if message != "":
                return message
        return ""


class complement:
    def __init__(self, schema):
        self.schema = compile(schema)

    def __validate__(self, object, name, strict):
        message = self.schema.__validate__(object, name=name, strict=strict)
        if message != "":
            return ""
        else:
            return f"{name} does not match the complemented schema"


class lax:
    def __init__(self, schema):
        self.schema = compile(schema)

    def __validate__(self, object, name, strict):
        return self.schema.__validate__(object, name=name, strict=False)


class strict:
    def __init__(self, schema):
        self.schema = compile(schema)

    def __validate__(self, object, name, strict):
        return self.schema.__validate__(object, name=name, strict=True)


class quote:
    def __init__(self, schema):
        self.schema = _object(schema)

    def __validate__(self, object, name, strict):
        return self.schema.__validate__(object, name, strict)


class set_name:
    def __init__(self, schema, name):
        if not isinstance(name, str):
            raise SchemaError(f"The name {_c(name)} is not a string")
        self.schema = compile(schema)
        self.__name__ = name

    def __validate__(self, object, name, strict):
        message = self.schema.__validate__(object, name=name, strict=strict)
        if message != "":
            return _wrong_type_message(object, name, self.__name__)
        return ""


class regex:
    def __init__(self, regex, name=None, fullmatch=True, flags=0):
        self.regex = regex
        self.fullmatch = fullmatch
        if name is not None:
            if not isinstance(name, str):
                raise SchemaError(f"The regex name {_c(name)} is not a string")
            self.__name__ = name
        else:
            _flags = "" if flags == 0 else f", flags={flags}"
            _fullmatch = "" if fullmatch else ", fullmatch=False"
            self.__name__ = f"regex({repr(regex)}{_fullmatch}{_flags})"

        schema_error = False
        try:
            self.pattern = re.compile(regex, flags)
        except Exception as e:
            schema_error = True
            message = str(e)
        if schema_error:
            _name = f" (name: {repr(name)})" if name is not None else ""
            raise SchemaError(
                f"{regex}{_name} is an invalid regular expression: {message}"
            )

    def __validate__(self, object, name, strict):
        try:
            if self.fullmatch and self.pattern.fullmatch(object):
                return ""
            elif not self.fullmatch and self.pattern.match(object):
                return ""
        except Exception:
            pass
        return _wrong_type_message(object, name, self.__name__)


class interval:
    def __init__(self, lb, ub):
        self.lb = lb
        self.ub = ub
        self.lb_s = "..." if lb == ... else repr(lb)
        self.ub_s = "..." if ub == ... else repr(ub)

        schema_error = False
        if lb is ... and ub is ...:
            self.__validate__ = self.__validate_none__
        elif lb is ...:
            try:
                ub <= ub
            except Exception:
                schema_error = True
            if schema_error:
                raise SchemaError(
                    f"The upper bound in the interval"
                    f" [{self.lb_s},{self.ub_s}] does not support comparison"
                )
            self.__validate__ = self.__validate_ub__
        elif ub is ...:
            try:
                lb <= lb
            except Exception:
                schema_error = True
            if schema_error:
                raise SchemaError(
                    f"The lower bound in the interval"
                    f" [{self.lb_s},{self.ub_s}] does not support comparison"
                )
            self.__validate__ = self.__validate_lb__
        else:
            try:
                lb <= ub
            except Exception:
                schema_error = True
            if schema_error:
                raise SchemaError(
                    f"The upper and lower bound in the interval"
                    f" [{self.lb_s},{self.ub_s}] are incomparable"
                )

    def message(self, name, object):
        return (
            f"{name} (value:{_c(object)}) is not in the interval "
            f"[{self.lb_s},{self.ub_s}]"
        )

    def __validate__(self, object, name, strict):
        try:
            if self.lb <= object <= self.ub:
                return ""
            else:
                return self.message(name, object)
        except Exception as e:
            return f"{self.message(name, object)}: {str(e)}"

    def __validate_ub__(self, object, name, strict):
        try:
            if object <= self.ub:
                return ""
            else:
                return self.message(name, object)
        except Exception as e:
            return f"{self.message(name, object)}: {str(e)}"

    def __validate_lb__(self, object, name, strict):
        try:
            if object >= self.lb:
                return ""
            else:
                return self.message(name, object)
        except Exception as e:
            return f"{self.message(name, object)}: {str(e)}"

    def __validate_none__(self, object, name, strict):
        return ""


def compile(schema):
    if isinstance(schema, type) and hasattr(schema, "__validate__"):
        schema_error = False
        try:
            return schema()
        except Exception:
            schema_error = True
        if schema_error:
            raise SchemaError(
                f"{repr(schema.__name__)} does " f"not have a no-argument constructor"
            )
    elif hasattr(schema, "__validate__"):
        return schema
    elif isinstance(schema, type) or isinstance(schema, _GenericAlias):
        return _type(schema)
    elif callable(schema):
        return _callable(schema)
    elif isinstance(schema, tuple) or isinstance(schema, list):
        return _sequence(schema)
    elif isinstance(schema, dict):
        return _dict(schema)
    elif isinstance(schema, set):
        return union(*schema)
    else:
        return _object(schema)


def _validate(schema, object, name="object", strict=True):
    schema = compile(schema)
    return schema.__validate__(object, name=name, strict=strict)


def validate(schema, object, name="object", strict=True):
    message = _validate(schema, object, name=name, strict=strict)
    if message != "":
        raise ValidationError(message)


# Some predefined schemas


class number:
    def __validate__(self, object, name, strict):
        if isinstance(object, (int, float)):
            return ""
        else:
            return _wrong_type_message(object, name, "number")


class email:
    def __init__(self, *args, **kw):
        self.args = args
        self.kw = kw
        if "dns_resolver" not in kw:
            self.kw["dns_resolver"] = _get_dns_resolver()
        if "check_deliverability" not in kw:
            self.kw["check_deliverability"] = False

    def __validate__(self, object, name, strict):
        try:
            email_validator.validate_email(object, *self.args, **self.kw)
            return ""
        except Exception as e:
            return _wrong_type_message(object, name, "email", str(e))


class ip_address:
    def __validate__(self, object, name, strict):
        try:
            ipaddress.ip_address(object)
            return ""
        except ValueError:
            return _wrong_type_message(object, name, "ip_address")


class url:
    def __validate__(self, object, name, strict):
        result = urllib.parse.urlparse(object)
        if all([result.scheme, result.netloc]):
            return ""
        return _wrong_type_message(object, name, "url")


class date_time:
    def __init__(self, format=None):
        self.format = format
        if format is not None:
            self.__name__ = f"date_time({repr(format)})"
        else:
            self.__name__ = "date_time"

    def __validate__(self, object, name, strict):
        if self.format is not None:
            try:
                datetime.datetime.strptime(object, self.format)
            except Exception as e:
                return _wrong_type_message(object, name, self.__name__, str(e))
        else:
            try:
                datetime.datetime.fromisoformat(object)
            except Exception as e:
                return _wrong_type_message(object, name, self.__name__, str(e))
        return ""


class date:
    def __validate__(self, object, name, strict):
        try:
            datetime.date.fromisoformat(object)
        except Exception as e:
            return _wrong_type_message(object, name, "date", str(e))
        return ""


class time:
    def __validate__(self, object, name, strict):
        try:
            datetime.time.fromisoformat(object)
        except Exception as e:
            return _wrong_type_message(object, name, "time", str(e))
        return ""


class domain_name:
    def __init__(self, ascii_only=True, resolve=False):
        self.re_ascii = re.compile(r"[\x00-\x7F]*")
        self.ascii_only = ascii_only
        self.resolve = resolve
        arg_string = ""
        if not ascii_only:
            arg_string += ", ascii_only=False"
        if resolve:
            arg_string += ", resolve=True"
        if arg_string != "":
            arg_string = arg_string[2:]
        self.__name__ = (
            "domain_name" if not arg_string else f"domain_name({arg_string})"
        )

    def __validate__(self, object, name, strict):
        if self.ascii_only:
            if not self.re_ascii.fullmatch(object):
                return _wrong_type_message(
                    object, name, self.__name__, "Non-ascii characters"
                )
        try:
            idna.encode(object, uts46=False)
        except idna.core.IDNAError as e:
            return _wrong_type_message(object, name, self.__name__, str(e))

        if self.resolve:
            try:
                _get_dns_resolver().resolve(object)
            except Exception as e:
                return _wrong_type_message(object, name, self.__name__, str(e))
        return ""


class at_least_one_of:
    def __init__(self, *args):
        self.args = args
        args_s = [repr(a) for a in args]
        self.__name__ = f"{self.__class__.__name__}({','.join(args_s)})"

    def __validate__(self, object, name, strict):
        if not isinstance(object, dict):
            return _wrong_type_message(object, name, "dict")
        if any([a in object for a in self.args]):
            return ""
        else:
            return _wrong_type_message(object, name, self.__name__)


class at_most_one_of:
    def __init__(self, *args):
        self.args = args
        args_s = [repr(a) for a in args]
        self.__name__ = f"{self.__class__.__name__}({','.join(args_s)})"

    def __validate__(self, object, name, strict):
        if not isinstance(object, dict):
            return _wrong_type_message(object, name, "dict")
        if sum([a in object for a in self.args]) <= 1:
            return ""
        else:
            return _wrong_type_message(object, name, self.__name__)


class one_of:
    def __init__(self, *args):
        self.args = args
        args_s = [repr(a) for a in args]
        self.__name__ = f"{self.__class__.__name__}({','.join(args_s)})"

    def __validate__(self, object, name, strict):
        if not isinstance(object, dict):
            return _wrong_type_message(object, name, "dict")
        if sum([a in object for a in self.args]) == 1:
            return ""
        else:
            return _wrong_type_message(object, name, self.__name__)


class _dict:
    def __init__(self, schema):
        self.schema = {}
        for k, v in schema.items():
            self.schema[k] = compile(v)
        self.keys = _keys(self.schema)
        self.keys2 = _keys2(self.schema)

    def __validate__(self, object, name, strict):
        if type(object) is not dict:
            return _wrong_type_message(object, name, type(self.schema).__name__)
        if strict:
            for x in object:
                if x not in self.keys:
                    return f"{name}['{x}'] is not in the schema"
        for k_, k, o in self.keys2:
            # (k_,k,o)=(normalized key, key, optional)
            name_ = f"{name}['{k_}']"
            if k_ not in object:
                if o:
                    continue
                else:
                    return f"{name_} is missing"
            else:
                ret = self.schema[k].__validate__(object[k_], name=name_, strict=strict)
                if ret != "":
                    return ret
        return ""

    def __str__(self):
        return str(self.schema)


class _type:
    def __init__(self, schema):
        self.schema = schema
        if isinstance(schema, _GenericAlias):
            raise SchemaError("Parametrized generics are not supported!")

    def __validate__(self, object, name, strict):
        try:
            if not isinstance(object, self.schema):
                return _wrong_type_message(object, name, self.schema.__name__)
            else:
                return ""
        except Exception as e:
            return f"{self.schema} is not a valid type: {str(e)}"

    def __str__(self):
        return self.schema.__name__


class _sequence:
    def __init__(self, schema):
        self.type_schema = type(schema)
        self.schema = [compile(o) if o is not ... else ... for o in schema]
        if len(schema) > 0 and schema[-1] is ...:
            if len(schema) >= 2:
                self.fill = self.schema[-2]
                self.schema = self.schema[:-2]
            else:
                self.fill = _type(object)
                self.schema = []
            self.__validate__ = self.__validate_ellipsis__

    def __validate__(self, object, name, strict):
        if self.type_schema is not type(object):
            return _wrong_type_message(object, name, type(self.schema).__name__)
        ls = len(self.schema)
        lo = len(object)
        if strict:
            if lo > ls:
                return f"{name}[{ls}] is not in the schema"
        if ls > lo:
            return f"{name}[{lo}] is missing"
        for i in range(ls):
            name_ = f"{name}[{i}]"
            ret = self.schema[i].__validate__(object[i], name_, strict)
            if ret != "":
                return ret
        return ""

    def __validate_ellipsis__(self, object, name, strict):
        if self.type_schema is not type(object):
            return _wrong_type_message(object, name, type(self.schema).__name__)
        ls = len(self.schema)
        lo = len(object)
        if ls > lo:
            return f"{name}[{lo}] is missing"
        for i in range(ls):
            name_ = f"{name}[{i}]"
            ret = self.schema[i].__validate__(object[i], name_, strict)
            if ret != "":
                return ret
        for i in range(ls + 1, lo):
            name_ = f"{name}[{i}]"
            ret = self.fill.__validate__(object[i], name_, strict)
            if ret != "":
                return ret
        return ""

    def __str__(self):
        return str(self.schema)


class _object:
    def __init__(self, schema):
        self.schema = schema
        if isinstance(schema, float):
            self.__validate__ = self.__validate_float__

    def message(self, name, object):
        return f"{name} (value:{_c(object)}) is not equal to {repr(self.schema)}"

    def __validate__(self, object, name, strict):
        if object != self.schema:
            return self.message(name, object)
        return ""

    def message_float(self, name, object):
        return f"{name} (value:{_c(object)}) is not close to {repr(self.schema)}"

    def __validate_float__(self, object, name, strict):
        try:
            if math.isclose(self.schema, object):
                return ""
            else:
                return self.message_float(name, object)
        except Exception:
            return self.message_float(name, object)

    def __str__(self):
        return str(self.schema)


class _callable:
    def __init__(self, schema):
        self.schema = schema
        try:
            self.__name__ = self.schema.__name__
        except Exception:
            self.__name__ = str(self.schema)

    def __validate__(self, object, name, strict):
        try:
            if self.schema(object):
                return ""
            else:
                return _wrong_type_message(object, name, self.__name__)
        except Exception as e:
            return _wrong_type_message(object, name, self.__name__, str(e))

    def __str__(self):
        return str(self.schema)
