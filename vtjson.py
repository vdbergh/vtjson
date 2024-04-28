import collections
import datetime
import ipaddress
import math
import pathlib
import re
import urllib.parse

import dns.resolver
import email_validator
import idna

MAGIC_AVAILABLE = True
try:
    import magic as magic_
except Exception:
    MAGIC_AVAILABLE = False


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


__version__ = "1.7.10"


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


class _union:
    def __init__(self, schemas, _deferred_compiles=None):
        self.schemas = [
            compile(s, _deferred_compiles=_deferred_compiles) for s in schemas
        ]

    def __validate__(self, object, name, strict):
        messages = []
        for schema in self.schemas:
            message = schema.__validate__(object, name=name, strict=strict)
            if message == "":
                return ""
            else:
                messages.append(message)
        return " and ".join(messages)


class union:
    def __init__(self, *schemas):
        self.schemas = schemas

    def __compile__(self, _deferred_compiles=None):
        return _union(self.schemas, _deferred_compiles=_deferred_compiles)


class _intersect:
    def __init__(self, schemas, _deferred_compiles=None):
        self.schemas = [
            compile(s, _deferred_compiles=_deferred_compiles) for s in schemas
        ]

    def __validate__(self, object, name, strict):
        for schema in self.schemas:
            message = schema.__validate__(object, name=name, strict=strict)
            if message != "":
                return message
        return ""


class intersect:
    def __init__(self, *schemas):
        self.schemas = schemas

    def __compile__(self, _deferred_compiles=None):
        return _intersect(self.schemas, _deferred_compiles=_deferred_compiles)


class _complement:
    def __init__(self, schema, _deferred_compiles=None):
        self.schema = compile(schema, _deferred_compiles=_deferred_compiles)

    def __validate__(self, object, name, strict):
        message = self.schema.__validate__(object, name=name, strict=strict)
        if message != "":
            return ""
        else:
            return f"{name} does not match the complemented schema"


class complement:
    def __init__(self, schema):
        self.schema = schema

    def __compile__(self, _deferred_compiles=None):
        return _complement(self.schema, _deferred_compiles=_deferred_compiles)


class _lax:
    def __init__(self, schema, _deferred_compiles=None):
        self.schema = compile(schema, _deferred_compiles=_deferred_compiles)

    def __validate__(self, object, name, strict):
        return self.schema.__validate__(object, name=name, strict=False)


class lax:
    def __init__(self, schema):
        self.schema = schema

    def __compile__(self, _deferred_compiles=None):
        return _lax(self.schema, _deferred_compiles=_deferred_compiles)


class _strict:
    def __init__(self, schema, _deferred_compiles=None):
        self.schema = compile(schema, _deferred_compiles=_deferred_compiles)

    def __validate__(self, object, name, strict):
        return self.schema.__validate__(object, name=name, strict=True)


class strict:
    def __init__(self, schema):
        self.schema = schema

    def __compile__(self, _deferred_compiles=None):
        return _strict(self.schema, _deferred_compiles=_deferred_compiles)


class quote:
    def __init__(self, schema):
        self.schema = _object(schema)

    def __validate__(self, object, name, strict):
        return self.schema.__validate__(object, name, strict)


class _set_name:
    def __init__(self, schema, name, _deferred_compiles=None):
        self.schema = compile(schema, _deferred_compiles=_deferred_compiles)
        self.__name__ = name

    def __validate__(self, object, name, strict):
        message = self.schema.__validate__(object, name=name, strict=strict)
        if message != "":
            return _wrong_type_message(object, name, self.__name__)
        return ""


class set_name:
    def __init__(self, schema, name):
        if not isinstance(name, str):
            raise SchemaError(f"The name {_c(name)} is not a string")
        self.schema = schema
        self.name = name

    def __compile__(self, _deferred_compiles=None):
        return _set_name(self.schema, self.name, _deferred_compiles=_deferred_compiles)


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

        try:
            self.pattern = re.compile(regex, flags)
        except Exception as e:
            _name = f" (name: {repr(name)})" if name is not None else ""
            raise SchemaError(
                f"{regex}{_name} is an invalid regular expression: {str(e)}"
            ) from None

    def __validate__(self, object, name, strict):
        try:
            if self.fullmatch and self.pattern.fullmatch(object):
                return ""
            elif not self.fullmatch and self.pattern.match(object):
                return ""
        except Exception:
            pass
        return _wrong_type_message(object, name, self.__name__)


class glob:
    def __init__(self, pattern, name=None):
        self.pattern = pattern

        if name is None:
            self.__name__ = f"glob({repr(pattern)})"
        else:
            self.__name__ = name

        try:
            pathlib.PurePath("").match(pattern)
        except Exception as e:
            _name = f" (name: {repr(name)})" if name is not None else ""
            raise SchemaError(
                f"{repr(pattern)}{_name} is not a valid filename pattern: {str(e)}"
            ) from None

    def __validate__(self, object, name, strict):
        try:
            if pathlib.PurePath(object).match(self.pattern):
                return ""
            else:
                return _wrong_type_message(object, name, self.__name__)
        except Exception as e:
            return _wrong_type_message(object, name, self.__name__, str(e))


class magic:
    def __init__(self, mime_type, name=None):
        if not MAGIC_AVAILABLE:
            raise SchemaError("Failed to load python-magic")

        if not isinstance(mime_type, str):
            raise SchemaError(f"{repr(mime_type)} is not a string")

        self.mime_type = mime_type

        if name is None:
            self.__name__ = f"magic({repr(mime_type)})"
        else:
            self.__name__ = name

    def __validate__(self, object, name, strict):
        try:
            object_mime_type = magic_.from_buffer(object, mime=True)
        except Exception as e:
            return _wrong_type_message(object, name, self.__name__, str(e))
        if object_mime_type != self.mime_type:
            return _wrong_type_message(
                object,
                name,
                self.__name__,
                f"{repr(object_mime_type)} is different from {repr(self.mime_type)}",
            )
        return ""


class div:
    def __init__(self, divisor, remainder=0, name=None):
        if not isinstance(divisor, int):
            raise SchemaError(f"The divisor {repr(divisor)} is not an integer")
        if divisor == 0:
            raise SchemaError("The divisor cannot be zero")
        if not isinstance(remainder, int):
            raise SchemaError(f"The remainder {repr(remainder)} is not an integer")
        self.divisor = divisor
        self.remainder = remainder

        if name is None:
            _divisor = str(divisor)
            _remainder = ""
            if remainder != 0:
                _remainder = "," + str(remainder)
            self.__name__ = f"div({_divisor+_remainder})"
        else:
            self.__name__ = name

    def __validate__(self, object, name, strict):
        if not isinstance(object, int):
            return _wrong_type_message(object, name, "int")
        elif (object - self.remainder) % self.divisor == 0:
            return ""
        else:
            return _wrong_type_message(object, name, self.__name__)


class interval:
    def __init__(self, lb, ub):
        self.lb = lb
        self.ub = ub
        self.lb_s = "..." if lb == ... else repr(lb)
        self.ub_s = "..." if ub == ... else repr(ub)

        if lb is ... and ub is ...:
            self.__validate__ = self.__validate_none__
        elif lb is ...:
            try:
                ub <= ub
            except Exception:
                raise SchemaError(
                    f"The upper bound in the interval"
                    f" [{self.lb_s},{self.ub_s}] does not support comparison"
                ) from None
            self.__validate__ = self.__validate_ub__
        elif ub is ...:
            try:
                lb <= lb
            except Exception:
                raise SchemaError(
                    f"The lower bound in the interval"
                    f" [{self.lb_s},{self.ub_s}] does not support comparison"
                ) from None
            self.__validate__ = self.__validate_lb__
        else:
            try:
                lb <= ub
            except Exception:
                raise SchemaError(
                    f"The upper and lower bound in the interval"
                    f" [{self.lb_s},{self.ub_s}] are incomparable"
                ) from None

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


class size:
    def __init__(self, lb, ub):
        if not isinstance(lb, int):
            raise SchemaError(f"{repr(lb)} is not of type 'int'")
        if lb < -0:
            raise SchemaError(f"{repr(lb)} is not >= 0")
        if not isinstance(ub, int) and ub != ...:
            raise SchemaError(f"{repr(ub)} is not of type 'int'")
        if isinstance(ub, int) and ub < lb:
            raise SchemaError(f"{repr(ub)} is not >= {repr(lb)}")
        self.interval = interval(lb, ub)

    def __validate__(self, object, name, strict):
        try:
            L = len(object)
        except Exception:
            return f"{name} (value:{_c(object)}) has no len()"
        return self.interval.__validate__(L, f"len({name})", strict)


class _deferred:
    def __init__(self, collection, key):
        self.collection = collection
        self.key = key
        self.in_use = False

    def __validate__(self, object, name, strict):
        if self.key not in self.collection:
            raise ValidationError(f"{name}: key {self.key} is unknown")
        return self.collection[self.key].__validate__(object, name, strict)


class _mapping:
    def __init__(self):
        self.mapping = {}

    def __setitem__(self, key, value):
        self.mapping[id(key)] = (key, value)

    def __getitem__(self, key):
        return self.mapping[id(key)][1]

    def __delitem__(self, key):
        del self.mapping[id(key)]

    def __contains__(self, key):
        return id(key) in self.mapping


def compile(schema, _deferred_compiles=None):
    if _deferred_compiles is None:
        _deferred_compiles = _mapping()
    # avoid infinite loop in case of a recursive schema
    if schema in _deferred_compiles:
        if isinstance(_deferred_compiles[schema], _deferred):
            _deferred_compiles[schema].in_use = True
            return _deferred_compiles[schema]
    _deferred_compiles[schema] = _deferred(_deferred_compiles, schema)

    # real work starts here
    if isinstance(schema, type) and hasattr(schema, "__validate__"):
        try:
            ret = schema()
        except Exception:
            raise SchemaError(
                f"{repr(schema.__name__)} does " f"not have a no-argument constructor"
            ) from None
    elif hasattr(schema, "__validate__"):
        ret = schema
    elif hasattr(schema, "__compile__"):
        ret = schema.__compile__(_deferred_compiles=_deferred_compiles)
    elif isinstance(schema, type) or isinstance(schema, _GenericAlias):
        ret = _type(schema)
    elif callable(schema):
        ret = _callable(schema)
    elif isinstance(schema, tuple) or isinstance(schema, list):
        ret = _sequence(schema, _deferred_compiles=_deferred_compiles)
    elif isinstance(schema, dict):
        ret = _dict(schema, _deferred_compiles=_deferred_compiles)
    elif isinstance(schema, set):
        ret = _union(schema, _deferred_compiles=_deferred_compiles)
    else:
        ret = _object(schema)

    # back to updating the cache
    if _deferred_compiles[schema].in_use:
        _deferred_compiles[schema] = ret
    else:
        del _deferred_compiles[schema]
    return ret


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
        if not isinstance(object, str):
            return _wrong_type_message(
                object, name, "email", f"{_c(object)} is not a string"
            )
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


class nothing:
    def __validate__(self, object, name, strict):
        return _wrong_type_message(object, name, "nothing")


class anything:
    def __validate__(self, object, name, strict):
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
        try:
            if any([a in object for a in self.args]):
                return ""
            else:
                return _wrong_type_message(object, name, self.__name__)
        except Exception as e:
            return _wrong_type_message(object, name, self.__name__, str(e))


class at_most_one_of:
    def __init__(self, *args):
        self.args = args
        args_s = [repr(a) for a in args]
        self.__name__ = f"{self.__class__.__name__}({','.join(args_s)})"

    def __validate__(self, object, name, strict):
        try:
            if sum([a in object for a in self.args]) <= 1:
                return ""
            else:
                return _wrong_type_message(object, name, self.__name__)
        except Exception as e:
            return _wrong_type_message(object, name, self.__name__, str(e))


class one_of:
    def __init__(self, *args):
        self.args = args
        args_s = [repr(a) for a in args]
        self.__name__ = f"{self.__class__.__name__}({','.join(args_s)})"

    def __validate__(self, object, name, strict):
        try:
            if sum([a in object for a in self.args]) == 1:
                return ""
            else:
                return _wrong_type_message(object, name, self.__name__)
        except Exception as e:
            return _wrong_type_message(object, name, self.__name__, str(e))


class keys:
    def __init__(self, *args):
        self.args = args

    def __validate__(self, object, name, strict):
        for k in self.args:
            if k not in object:
                return f"{name}[{repr(k)}] is missing"
        return ""


class _ifthen:
    def __init__(
        self, if_schema, then_schema, else_schema=None, _deferred_compiles=None
    ):
        self.if_schema = compile(if_schema, _deferred_compiles=_deferred_compiles)
        self.then_schema = compile(then_schema, _deferred_compiles=_deferred_compiles)
        if else_schema is not None:
            self.else_schema = compile(
                else_schema, _deferred_compiles=_deferred_compiles
            )
        else:
            self.else_schema = else_schema

    def __validate__(self, object, name, strict):
        if self.if_schema.__validate__(object, name, strict) == "":
            return self.then_schema.__validate__(object, name, strict)
        elif self.else_schema is not None:
            return self.else_schema.__validate__(object, name, strict)
        return ""


class ifthen:
    def __init__(self, if_schema, then_schema, else_schema=None):
        self.if_schema = if_schema
        self.then_schema = then_schema
        self.else_schema = else_schema

    def __compile__(self, _deferred_compiles=None):
        return _ifthen(
            self.if_schema,
            self.then_schema,
            else_schema=self.else_schema,
            _deferred_compiles=_deferred_compiles,
        )


class _cond:
    def __init__(self, args, _deferred_compiles=None):
        self.conditions = []
        for c in args:
            self.conditions.append(
                (
                    compile(c[0], _deferred_compiles=_deferred_compiles),
                    compile(c[1], _deferred_compiles=_deferred_compiles),
                )
            )

    def __validate__(self, object, name, strict):
        for c in self.conditions:
            if c[0].__validate__(object, name, strict) == "":
                return c[1].__validate__(object, name, strict)
        return ""


class cond:
    def __init__(self, *args):
        for c in args:
            if not isinstance(c, tuple) or len(c) != 2:
                raise SchemaError(f"{repr(c)} is not a tuple of length two")
        self.args = args

    def __compile__(self, _deferred_compiles=None):
        return _cond(self.args, _deferred_compiles=_deferred_compiles)


class _fields:
    def __init__(self, d, _deferred_compiles=None):
        self.d = {}
        for k, v in d.items():
            self.d[k] = compile(v, _deferred_compiles=_deferred_compiles)

    def __validate__(self, object, name, strict):
        for k, v in self.d.items():
            name_ = f"{name}.{k}"
            if not hasattr(object, k):
                return f"{name_} is missing"
            ret = self.d[k].__validate__(getattr(object, k), name=name_, strict=strict)
            if ret != "":
                return ret
        return ""


class fields:
    def __init__(self, d):
        if not isinstance(d, dict):
            raise SchemaError(f"{repr(d)} is not a dictionary")
        for k in d:
            if not isinstance(k, str):
                raise SchemaError(f"key {repr(k)} in {repr(d)} is not a string")
        self.d = d

    def __compile__(self, _deferred_compiles=None):
        return _fields(self.d, _deferred_compiles=_deferred_compiles)


class _dict:
    def __init__(self, schema, _deferred_compiles=None):
        self.schema = collections.OrderedDict()
        for k, v in schema.items():
            self.schema[k] = compile(v, _deferred_compiles=_deferred_compiles)
        self.keys = _keys(self.schema)
        self.keys2 = _keys2(self.schema)

    def __validate__(self, object, name, strict):
        if not isinstance(object, dict):
            return _wrong_type_message(object, name, "dict")
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
        if strict:
            for x in object:
                if x not in self.keys:
                    return f"{name}['{x}'] is not in the schema"
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
    def __init__(self, schema, _deferred_compiles=None):
        self.type_schema = type(schema)
        self.schema = [
            compile(o, _deferred_compiles=_deferred_compiles) if o is not ... else ...
            for o in schema
        ]
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
        for i in range(ls, lo):
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
