import ipaddress
import re
import urllib.parse
from collections.abc import Sequence

from email_validator import EmailNotValidError, validate_email


class ellipsis_list(Sequence):
    def __init__(self, L, length=0):
        self.L = L
        self.length = length
        self.has_ellipsis = False
        if len(L) > 0 and L[-1] == ...:
            self.has_ellipsis = True
            if len(L) >= 2:
                self.last = L[-2]
            else:
                self.last = object
        if not self.has_ellipsis:
            self.len = len(self.L)
        elif self.length <= len(self.L) - 2:
            self.len = len(self.L) - 2
        else:
            self.len = self.length

    def __len__(self):
        return self.len

    def __getitem__(self, index):
        if not self.has_ellipsis or index < len(self.L) - 2:
            return self.L[index]
        elif index < self.length:
            return self.last
        else:
            raise IndexError(index)


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
        except Exception:
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
    try:
        if not isinstance(object, schema):
            return f"{name} (value:{object}) is not of type {schema.__name__}"
        else:
            return ""
    except Exception:
        return f"{schema} is not a valid type"


def validate_sequence(schema, object, name, strict):
    assert isinstance(schema, list) or isinstance(schema, tuple)
    if type(schema) is not type(object):
        return f"{name} is not of type {type(schema).__name__}"
    L = len(object)
    schema = ellipsis_list(schema, length=L)
    if strict and L > len(schema):
        name_ = f"{name}[{len(schema)}]"
        return f"{name_} is not in the schema"
    for i in range(len(schema)):
        name_ = f"{name}[{i}]"
        if i >= L:
            return f"{name_} does not exist"
        else:
            ret = validate(schema[i], object[i], name=name_, strict=strict)
            if ret != "":
                return ret
    return ""


def validate_dict(schema, object, name, strict):
    assert isinstance(schema, dict)
    if type(schema) is not type(object):
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
