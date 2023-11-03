import ipaddress
import re
import types
import urllib.parse

from email_validator import EmailNotValidError, validate_email


class validate_meta(type):
    def __instancecheck__(cls, object):
        valid = validate(cls.__schema__, object, "object", strict=cls.__strict__)
        if cls.__debug__ and valid != "":
            print(f"DEBUG: {valid}")
        return valid == ""


def make_type(schema, name=None, strict=True, debug=False):
    if name is None:
        if hasattr(schema, "__name__"):
            name = schema.__name__
        else:
            name = "schema"
    return validate_meta(
        name, (), {"__schema__": schema, "__strict__": strict, "__debug__": debug}
    )


class optional_key:
    def __init__(self, key):
        self.key = key


class union:
    def __init__(self, *schemas):
        self.schemas = schemas

    def __validate__(self, object, name, strict):
        messages = []
        for schema in self.schemas:
            message = validate(schema, object, name=name, strict=strict)
            if message == "":
                return ""
            else:
                messages.append(message)
        return " and ".join(messages)


class regex:
    def __init__(self, regex, name=None):
        self.regex = regex
        if name is not None:
            self.__name__ = name
        else:
            self.__name__ = f"regex({regex})"
        self.message = ""
        try:
            self.pattern = re.compile(regex)
        except Exception as e:
            self.message = (
                f"{regex} (name: {name}) is an invalid regular expression: {str(e)}"
            )

    def __validate__(self, object, name, strict):
        if self.message != "":
            return self.message
        try:
            if self.pattern.fullmatch(object):
                return ""
        except:
            pass

        return f"{name} (value:{object}) is not of type {self.__name__}"


def _keys(dict):
    ret = set()
    for k in dict:
        if isinstance(k, optional_key):
            ret.add(k.key)
        elif isinstance(k, str) and len(k) > 0 and k[-1] == "?":
            ret.add(k[:-1])
        else:
            ret.add(k)
    return ret


def validate_type(schema, object, name):
    assert isinstance(schema, type)
    b = False
    try:
        b = isinstance(object, schema)
    except Exception as e:
        return f"{schema} is not a valid type"
    if not isinstance(object, schema):
        return f"{name} (value:{object}) is not of type {schema.__name__}"
    else:
        return ""


def validate_sequence(schema, object_, name, strict):
    assert isinstance(schema, list) or isinstance(schema, tuple)

    def enum_ellipsis(l):
        """If the last entry is an ellipsis then the next to last
        entry is repeated zero or more times."""
        last = object
        has_ellipsis = False
        optional = len(l)
        if len(l) > 0 and l[-1] == ...:
            has_ellipsis = True
            optional = len(l) - 2

        for i, ll in enumerate(l):
            if ll == ... and i == len(l) - 1:
                yield True, last
            else:
                last = ll
                yield i >= optional, ll
        while True:
            if has_ellipsis:
                yield True, last
            else:
                yield True, None

    def enum(l):
        for ll in l:
            yield ll
        while True:
            yield None

    if type(schema) != type(object_):
        return f"{name} is not of type {type(schema).__name__}"

    sch = enum_ellipsis(schema)
    obj = enum(object_)
    i = 0
    while True:
        name_ = f"{name}[{i}]"
        i += 1
        o, u = next(sch)
        v = next(obj)
        if u is None and v is None:
            return ""
        elif u is None:
            if strict:
                return f"{name_} is not in the schema"
            else:
                return ""
        elif v is None:
            if not o:
                return f"{name_} is missing"
            else:
                return ""
        else:
            ret = validate(u, v, name=name_, strict=strict)
            if ret != "":
                return ret
    assert False


def validate_dict(schema, object, name, strict):
    assert isinstance(schema, dict)
    if type(schema) != type(object):
        return f"{name} is not of type {type(schema).__name__}"
    if strict:
        _k = _keys(schema)
        for x in object:
            if x not in _k:
                return f"{name}['{x}'] is not in the schema"
    for k in schema:
        k_ = k
        if isinstance(k, optional_key):
            k_ = k.key
            if k_ not in object:
                continue
        if isinstance(k, str) and len(k) > 0 and k[-1] == "?":
            k_ = k[:-1]
            if k_ not in object:
                continue
        name_ = f"{name}['{k_}']"
        if k_ not in object:
            return f"{name_} is missing"
        else:
            ret = validate(schema[k], object[k_], name=name_, strict=strict)
            if ret != "":
                return ret
    return ""


def validate(schema, object, name="object", strict=True):
    if hasattr(schema, "__validate__"):  # duck typing
        return schema.__validate__(object, name, strict)
    elif isinstance(schema, type):
        return validate_type(schema, object, name)
    elif isinstance(schema, list) or isinstance(schema, tuple):
        return validate_sequence(schema, object, name, strict)
    elif isinstance(schema, dict):
        return validate_dict(schema, object, name, strict)
    elif object != schema:
        return f"{name} (value:{object}) is not equal to {repr(schema)}"
    return ""


# Some predefined schemas

number = make_type(union(int, float), "number")


class email:
    @staticmethod
    def __validate__(object, name, strict):
        try:
            validate_email(object, check_deliverability=False)
            return ""
        except EmailNotValidError as e:
            return f"{name} (value:{object}) is not a valid email address: {str(e)}"


class ip_address:
    @staticmethod
    def __validate__(object, name, strict):
        try:
            ipaddress.ip_address(object)
            return ""
        except ValueError:
            return f"{name} (value:{object}) is not of type ip_address"


class url:
    @staticmethod
    def __validate__(object, name, strict):
        result = urllib.parse.urlparse(object)
        if all([result.scheme, result.netloc]):
            return ""
        return f"{name} (value:{object}) is not of type url"
