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


__version__ = "1.9.2"


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


class _validate_meta(type):
    def __instancecheck__(cls, object):
        valid = _validate(
            cls.__schema__, object, "object", strict=cls.__strict__, subs=cls.__subs__
        )
        if cls.__debug__ and valid != "":
            print(f"DEBUG: {valid}")
        return valid == ""


def make_type(schema, name=None, strict=True, debug=False, subs={}):
    if name is None:
        if hasattr(schema, "__name__"):
            name = schema.__name__
        else:
            name = "schema"
    return _validate_meta(
        name,
        (),
        {
            "__schema__": schema,
            "__strict__": strict,
            "__debug__": debug,
            "__subs__": subs,
        },
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

    def __validate__(self, object, name="object", strict=True, subs={}):
        messages = []
        for schema in self.schemas:
            message = schema.__validate__(object, name=name, strict=strict, subs=subs)
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

    def __validate__(self, object, name="object", strict=True, subs={}):
        for schema in self.schemas:
            message = schema.__validate__(object, name=name, strict=strict, subs=subs)
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

    def __validate__(self, object, name="object", strict=True, subs={}):
        message = self.schema.__validate__(object, name=name, strict=strict, subs=subs)
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

    def __validate__(self, object, name="object", strict=True, subs={}):
        return self.schema.__validate__(object, name=name, strict=False, subs=subs)


class lax:
    def __init__(self, schema):
        self.schema = schema

    def __compile__(self, _deferred_compiles=None):
        return _lax(self.schema, _deferred_compiles=_deferred_compiles)


class _strict:
    def __init__(self, schema, _deferred_compiles=None):
        self.schema = compile(schema, _deferred_compiles=_deferred_compiles)

    def __validate__(self, object, name="object", strict=True, subs={}):
        return self.schema.__validate__(object, name=name, strict=True, subs=subs)


class strict:
    def __init__(self, schema):
        self.schema = schema

    def __compile__(self, _deferred_compiles=None):
        return _strict(self.schema, _deferred_compiles=_deferred_compiles)


class _set_label:
    def __init__(self, schema, labels, debug, _deferred_compiles=None):
        self.schema = compile(schema, _deferred_compiles=_deferred_compiles)
        self.labels = labels
        self.debug = debug

    def __validate__(self, object, name="object", strict=True, subs={}):
        common_labels = tuple(set(subs.keys()).intersection(self.labels))
        if len(common_labels) >= 2:
            raise ValidationError(
                f"multiple substitutions for {name} "
                f"(applicable keys:{common_labels})"
            )
        elif len(common_labels) == 1:
            key = common_labels[0]
            if self.debug:
                print(f"The schema for {name} (key:{key}) was replaced")
            # We have to recompile subs[key]. This seems unavoidable as it is not
            # known at schema creation time.
            #
            # But the user can always pre-compile subs[key].
            return _validate(subs[key], object, name=name, strict=True, subs=subs)
        else:
            return self.schema.__validate__(object, name=name, strict=True, subs=subs)


class set_label:
    def __init__(self, schema, *labels, debug=False):
        self.schema = schema
        for L in labels:
            if not isinstance(L, str):
                raise SchemaError(f"The label {L} is not a string")
        self.labels = set(labels)
        if not isinstance(debug, bool):
            raise SchemaError(f"The option {debug} is not a boolean")
        self.debug = debug

    def __compile__(self, _deferred_compiles=None):
        return _set_label(
            self.schema, self.labels, self.debug, _deferred_compiles=_deferred_compiles
        )


class quote:
    def __init__(self, schema):
        self.schema = _const(schema)

    def __validate__(self, object, name="object", strict=True, subs={}):
        return self.schema.__validate__(object, name=name, strict=strict, subs=subs)


class _set_name:
    def __init__(self, schema, name, _deferred_compiles=None):
        self.schema = compile(schema, _deferred_compiles=_deferred_compiles)
        self.__name__ = name

    def __validate__(self, object, name="object", strict=True, subs={}):
        message = self.schema.__validate__(object, name=name, strict=strict, subs=subs)
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

    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
        if not isinstance(object, int):
            return _wrong_type_message(object, name, "int")
        elif (object - self.remainder) % self.divisor == 0:
            return ""
        else:
            return _wrong_type_message(object, name, self.__name__)


class gt:
    def __init__(self, lb):
        try:
            lb <= lb
        except Exception:
            raise SchemaError(
                f"The lower bound {lb} does not support comparison"
            ) from None
        self.lb = lb

    def message(self, name, object):
        return f"{name} (value:{_c(object)}) is not strictly greater than {self.lb}"

    def __validate__(self, object, name="object", strict=True, subs={}):
        try:
            if self.lb < object:
                return ""
            else:
                return self.message(name, object)
        except Exception as e:
            return f"{self.message(name, object)}: {str(e)}"


class ge:
    def __init__(self, lb):
        try:
            lb <= lb
        except Exception:
            raise SchemaError(
                f"The lower bound {lb} does not support comparison"
            ) from None
        self.lb = lb

    def message(self, name, object):
        return f"{name} (value:{_c(object)}) is not greater than or equal to {self.lb}"

    def __validate__(self, object, name="object", strict=True, subs={}):
        try:
            if self.lb <= object:
                return ""
            else:
                return self.message(name, object)
        except Exception as e:
            return f"{self.message(name, object)}: {str(e)}"


class lt:
    def __init__(self, ub):
        try:
            ub <= ub
        except Exception:
            raise SchemaError(
                f"The upper bound {ub} does not support comparison"
            ) from None
        self.ub = ub

    def message(self, name, object):
        return f"{name} (value:{_c(object)}) is not strictly less than {self.ub}"

    def __validate__(self, object, name="object", strict=True, subs={}):
        try:
            if self.ub > object:
                return ""
            else:
                return self.message(name, object)
        except Exception as e:
            return f"{self.message(name, object)}: {str(e)}"


class le:
    def __init__(self, ub):
        try:
            ub <= ub
        except Exception:
            raise SchemaError(
                f"The upper bound {ub} does not support comparison"
            ) from None
        self.ub = ub

    def message(self, name, object):
        return f"{name} (value:{_c(object)}) is not less than or equal to {self.ub}"

    def __validate__(self, object, name="object", strict=True, subs={}):
        try:
            if self.ub >= object:
                return ""
            else:
                return self.message(name, object)
        except Exception as e:
            return f"{self.message(name, object)}: {str(e)}"


class interval:
    def __init__(self, lb, ub, strict_lb=False, strict_ub=False):
        self.lb = lb
        self.ub = ub

        self.lb_s = "..." if lb == ... else repr(lb)
        self.ub_s = "..." if ub == ... else repr(ub)

        ld = "]" if strict_lb else "["
        ud = "[" if strict_ub else "]"

        if lb is not ...:
            if strict_lb:
                lower = gt(lb)
            else:
                lower = ge(lb)

        if ub is not ...:
            if strict_ub:
                upper = lt(ub)
            else:
                upper = le(ub)

        if lb is ... and ub is ...:
            self.__validate__ = anything().__validate__
        elif lb is ...:
            try:
                ub <= ub
            except Exception:
                raise SchemaError(
                    f"The upper bound in the interval"
                    f" {ld}{self.lb_s},{self.ub_s}{ud} does not support comparison"
                ) from None
            self.__validate__ = upper.__validate__
        elif ub is ...:
            try:
                lb <= lb
            except Exception:
                raise SchemaError(
                    f"The lower bound in the interval"
                    f" {ld}{self.lb_s},{self.ub_s}{ud} does not support comparison"
                ) from None
            self.__validate__ = lower.__validate__
        else:
            try:
                lb <= ub
            except Exception:
                raise SchemaError(
                    f"The upper and lower bound in the interval"
                    f" {ld}{self.lb_s},{self.ub_s}{ud} are incomparable"
                ) from None
            self.__validate__ = _intersect((lower, upper)).__validate__

    # Not used but necessary for the protocol
    def __validate__(self, object, name="object", strict=True, subs={}):
        return ""


class size:
    def __init__(self, lb, ub=None):
        if ub is None:
            ub = lb
        if not isinstance(lb, int):
            raise SchemaError(
                f"the lower size bound (value: {repr(lb)}) is not of type 'int'"
            )
        if lb < 0:
            raise SchemaError(
                f"the lower size bound (value: {repr(lb)}) is smaller than 0"
            )
        if not isinstance(ub, int) and ub != ...:
            raise SchemaError(
                f"the upper size bound (value:{repr(ub)}) is not of type 'int'"
            )
        if isinstance(ub, int) and ub < lb:
            raise SchemaError(
                f"the lower size bound (value: {repr(lb)}) is bigger "
                f"than the upper bound (value: {repr(ub)})"
            )
        self.interval = interval(lb, ub)

    def __validate__(self, object, name="object", strict=True, subs={}):
        try:
            L = len(object)
        except Exception:
            return f"{name} (value:{_c(object)}) has no len()"
        return self.interval.__validate__(L, f"len({name})", strict, subs)


class _deferred:
    def __init__(self, collection, key):
        self.collection = collection
        self.key = key
        self.in_use = False

    def __validate__(self, object, name="object", strict=True, subs={}):
        if self.key not in self.collection:
            raise ValidationError(f"{name}: key {self.key} is unknown")
        return self.collection[self.key].__validate__(
            object, name=name, strict=strict, subs=subs
        )


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
        ret = _set(schema, _deferred_compiles=_deferred_compiles)
    else:
        ret = _const(schema)

    # back to updating the cache
    if _deferred_compiles[schema].in_use:
        _deferred_compiles[schema] = ret
    else:
        del _deferred_compiles[schema]
    return ret


def _validate(schema, object, name="object", strict=True, subs={}):
    schema = compile(schema)
    return schema.__validate__(object, name=name, strict=strict, subs=subs)


def validate(schema, object, name="object", strict=True, subs={}):
    message = _validate(schema, object, name=name, strict=strict, subs=subs)
    if message != "":
        raise ValidationError(message)


# Some predefined schemas


class number:
    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
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
    def __validate__(self, object, name="object", strict=True, subs={}):
        try:
            ipaddress.ip_address(object)
            return ""
        except ValueError:
            return _wrong_type_message(object, name, "ip_address")


class url:
    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
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
    def __validate__(self, object, name="object", strict=True, subs={}):
        try:
            datetime.date.fromisoformat(object)
        except Exception as e:
            return _wrong_type_message(object, name, "date", str(e))
        return ""


class time:
    def __validate__(self, object, name="object", strict=True, subs={}):
        try:
            datetime.time.fromisoformat(object)
        except Exception as e:
            return _wrong_type_message(object, name, "time", str(e))
        return ""


class nothing:
    def __validate__(self, object, name="object", strict=True, subs={}):
        return _wrong_type_message(object, name, "nothing")


class anything:
    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
        if (
            self.if_schema.__validate__(object, name=name, strict=strict, subs=subs)
            == ""
        ):
            return self.then_schema.__validate__(
                object, name=name, strict=strict, subs=subs
            )
        elif self.else_schema is not None:
            return self.else_schema.__validate__(
                object, name=name, strict=strict, subs=subs
            )
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

    def __validate__(self, object, name="object", strict=True, subs={}):
        for c in self.conditions:
            if c[0].__validate__(object, name=name, strict=strict, subs=subs) == "":
                return c[1].__validate__(object, name=name, strict=strict, subs=subs)
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

    def __validate__(self, object, name="object", strict=True, subs={}):
        for k, v in self.d.items():
            name_ = f"{name}.{k}"
            if not hasattr(object, k):
                return f"{name_} is missing"
            ret = self.d[k].__validate__(
                getattr(object, k), name=name_, strict=strict, subs=subs
            )
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


class _filter:
    def __init__(self, filter, schema, filter_name=None, _deferred_compiles=None):
        self.filter = filter
        self.schema = compile(schema, _deferred_compiles=_deferred_compiles)
        if filter_name is not None:
            self.filter_name = filter_name
        else:
            try:
                self.filter_name = self.filter.__name__
            except Exception:
                self.filter_name = "filter"
            if self.filter_name == "<lambda>":
                self.filter_name = "filter"

    def __validate__(self, object, name="object", strict=True, subs={}):
        try:
            object = self.filter(object)
        except Exception as e:
            return (
                f"Applying {self.filter_name} to {name} "
                f"(value: {_c(object)}) failed: {str(e)}"
            )
        name = f"{self.filter_name}({name})"
        return self.schema.__validate__(object, name="object", strict=strict, subs=subs)


class filter:
    def __init__(self, filter, schema, filter_name=None):
        if filter_name is not None and not isinstance(filter_name, str):
            raise SchemaError("The filter name is not a string")
        if not callable(filter):
            raise SchemaError("The filter is not callable")
        self.filter = filter
        self.schema = schema
        self.filter_name = filter_name

    def __compile__(self, _deferred_compiles=None):
        return _filter(
            self.filter,
            self.schema,
            filter_name=self.filter_name,
            _deferred_compiles=None,
        )


class _type:
    def __init__(self, schema):
        self.schema = schema
        if isinstance(schema, _GenericAlias):
            raise SchemaError("Parametrized generics are not supported!")

    def __validate__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
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
            ret = self.schema[i].__validate__(object[i], name_, strict, subs)
            if ret != "":
                return ret
        return ""

    def __validate_ellipsis__(self, object, name="object", strict=True, subs={}):
        if self.type_schema is not type(object):
            return _wrong_type_message(object, name, type(self.schema).__name__)
        ls = len(self.schema)
        lo = len(object)
        if ls > lo:
            return f"{name}[{lo}] is missing"
        for i in range(ls):
            name_ = f"{name}[{i}]"
            ret = self.schema[i].__validate__(object[i], name_, strict, subs)
            if ret != "":
                return ret
        for i in range(ls, lo):
            name_ = f"{name}[{i}]"
            ret = self.fill.__validate__(object[i], name_, strict, subs)
            if ret != "":
                return ret
        return ""

    def __str__(self):
        return str(self.schema)


class _const:
    def __init__(self, schema):
        self.schema = schema
        if isinstance(schema, float):
            self.__validate__ = self.__validate_float__

    def message(self, name, object):
        return f"{name} (value:{_c(object)}) is not equal to {repr(self.schema)}"

    def __validate__(self, object, name="object", strict=True, subs={}):
        if object != self.schema:
            return self.message(name, object)
        return ""

    def message_float(self, name, object):
        return f"{name} (value:{_c(object)}) is not close to {repr(self.schema)}"

    def __validate_float__(self, object, name="object", strict=True, subs={}):
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

    def __validate__(self, object, name="object", strict=True, subs={}):
        try:
            if self.schema(object):
                return ""
            else:
                return _wrong_type_message(object, name, self.__name__)
        except Exception as e:
            return _wrong_type_message(object, name, self.__name__, str(e))

    def __str__(self):
        return str(self.schema)


class _dict:
    def __init__(self, schema, _deferred_compiles=None):
        self.min_keys = set()
        self.const_keys = set()
        self.other_keys = set()
        self.schema = {}
        for k in schema:
            compiled_schema = compile(schema[k], _deferred_compiles=_deferred_compiles)
            optional = True
            if isinstance(k, optional_key):
                key = k.key
            elif isinstance(k, str) and len(k) > 0 and k[-1] == "?":
                key = k[:-1]
            else:
                optional = False
                key = k
            c = compile(key, _deferred_compiles=_deferred_compiles)
            if isinstance(c, _const):
                if not optional:
                    self.min_keys.add(key)
                self.const_keys.add(key)
                self.schema[key] = compiled_schema
            else:
                self.other_keys.add(c)
                self.schema[c] = compiled_schema

    def __validate__(self, object, name="object", strict=True, subs={}):
        if not isinstance(object, dict):
            return _wrong_type_message(object, name, "dict")

        for k in self.min_keys:
            name_ = f"{name}[{repr(k)}]"
            if k not in object:
                return f"{name_} is missing"

        for k in object:
            vals = []
            name_ = f"{name}[{repr(k)}]"
            if k in self.const_keys:
                val = self.schema[k].__validate__(
                    object[k], name=name_, strict=strict, subs=subs
                )
                if val == "":
                    continue
                else:
                    vals.append(val)

            for kk in self.other_keys:
                if kk.__validate__(k, name="key", strict=strict, subs=subs) == "":
                    val = self.schema[kk].__validate__(
                        object[k], name=name_, strict=strict, subs=subs
                    )
                    if val == "":
                        break
                    else:
                        vals.append(val)
            else:
                if len(vals) > 0:
                    return " and ".join(vals)
                elif strict:
                    return f"{name_} is not in the schema"
        return ""

    def __str__(self):
        return str(self.schema)


class _set:
    def __init__(self, schema, _deferred_compiles=None):
        self.schema_ = schema
        if len(schema) == 0:
            self.schema = _const(set())
            self.__validate__ = self.__validate_empty_set__
        elif len(schema) == 1:
            self.schema = compile(
                tuple(schema)[0], _deferred_compiles=_deferred_compiles
            )
            self.__validate__ = self.__validate_singleton__
        else:
            self.schema = _union(schema, _deferred_compiles=_deferred_compiles)

    def __validate_empty_set__(self, object, name="object", strict=True, subs={}):
        return self.schema.__validate__(object, name=name, strict=True, subs=subs)

    def __validate_singleton__(self, object, name="object", strict=True, subs={}):
        if not isinstance(object, set):
            return _wrong_type_message(object, name, "set")
        for i, o in enumerate(object):
            name_ = f"{name}{{{i}}}"
            v = self.schema.__validate__(o, name=name_, strict=True, subs=subs)
            if v != "":
                return v
        return ""

    def __validate__(self, object, name="object", strict=True, subs={}):
        if not isinstance(object, set):
            return _wrong_type_message(object, name, "set")
        for i, o in enumerate(object):
            name_ = f"{name}{{{i}}}"
            v = self.schema.__validate__(o, name=name_, strict=True, subs=subs)
            if v != "":
                return v
        return ""

    def __str__(self):
        return str(self.schema_)
