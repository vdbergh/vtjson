from __future__ import annotations

import datetime
import ipaddress
import math
import pathlib
import re
import sys
import types
import typing
import urllib.parse
import warnings
from collections.abc import Sequence, Sized
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Type, TypeVar, Union, cast

try:
    from typing import Literal

    supports_Literal = True
except ImportError:
    supports_Literal = False

if hasattr(typing, "is_typeddict"):
    supports_TypedDict = True
else:
    supports_TypedDict = False

try:
    from typing import NotRequired, Required

    supports_NotRequired = True
except ImportError:
    supports_NotRequired = False

try:
    from typing import Annotated

    supports_Annotated = True
except ImportError:
    supports_Annotated = False

if hasattr(typing, "get_origin"):
    supports_Generics = True
else:
    supports_Generics = False

try:
    Sequence[str]
    supports_Generic_ABC = True
except Exception:
    supports_Generic_ABC = False

try:
    typing.get_type_hints(int, include_extras=True)
    supports_structural = True
except Exception:
    supports_structural = False

try:
    from types import UnionType

    supports_UnionType = True
except Exception:
    supports_UnionType = False

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import (
        Protocol,
    )

import dns.resolver
import email_validator
import idna

T = TypeVar("T")


def safe_cast(t: Type[T], object_: Any) -> T:
    validate(t, object_)
    return cast(T, object_)


class compiled_schema:
    def __validate__(
        self,
        object_: object,
        name: str,
        strict: bool,
        subs: Mapping[str, object],
    ) -> str:
        return ""


class comparable(Protocol):
    def __eq__(self, x: Any) -> bool: ...

    def __lt__(self, x: Any) -> bool: ...

    def __le__(self, x: Any) -> bool: ...

    def __gt__(self, x: Any) -> bool: ...

    def __ge__(self, x: Any) -> bool: ...


HAS_MAGIC = True
try:
    import magic as magic_
except Exception:
    HAS_MAGIC = False


class ValidationError(Exception):
    pass


class SchemaError(Exception):
    pass


__version__ = "2.1.5"


@dataclass
class Apply:
    skip_first: bool | None = None
    name: str | None = None
    labels: Sequence[str] | None = None

    def __call__(self, schemas: tuple[object, ...]) -> object:
        if len(schemas) == 0:
            raise SchemaError("Called Apply with an empty tuple")
        if self.skip_first:
            schemas = schemas[1:]
        if len(schemas) == 0:
            raise SchemaError("Called Apply with an empty tuple")
        if len(schemas) == 1:
            ret = schemas[0]
        else:
            ret = intersect(*schemas)
        if self.labels is not None:
            ret = set_label(ret, *self.labels)
        if self.name is not None:
            ret = set_name(ret, self.name)
        return ret


skip_first = Apply(skip_first=True)

_dns_resolver: dns.resolver.Resolver | None = None


def _get_type_hints(schema: object) -> dict[str, object]:
    if not supports_structural:
        raise SchemaError(
            "Structural subtyping in not supported in this " "Python version"
        )
    if isinstance(schema, type) and hasattr(schema, "__annotations__"):
        type_hints = typing.get_type_hints(schema, include_extras=True)
    else:
        raise SchemaError("The schema does not have type hints")
    return type_hints


def _to_dict(
    type_hints: Mapping[str, object], total: bool = True
) -> dict[object, object]:
    d: dict[object, object] = {}
    if not supports_Generics:
        raise SchemaError("Generic types are not supported")
    for k, v in type_hints.items():
        v_ = v
        k_: str | optional_key = k
        value_type = typing.get_origin(v)
        if supports_NotRequired and value_type in (Required, NotRequired):
            v_ = typing.get_args(v)[0]
        if total and supports_NotRequired and value_type == NotRequired:
            k_ = optional_key(k)
        elif not total and (not supports_NotRequired or value_type != Required):
            k_ = optional_key(k)
        d[k_] = v_
    return d


def _get_dns_resolver() -> dns.resolver.Resolver:
    global _dns_resolver
    if _dns_resolver is not None:
        return _dns_resolver
    _dns_resolver = dns.resolver.Resolver()
    _dns_resolver.cache = dns.resolver.LRUCache()
    _dns_resolver.timeout = 10
    _dns_resolver.lifetime = 10
    return _dns_resolver


def _c(s: object) -> str:
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


def _wrong_type_message(
    object_: object,
    name: str,
    type_name: str,
    explanation: str | None = None,
    skip_value: bool = False,
) -> str:
    if not skip_value:
        message = f"{name} (value:{_c(object_)}) is not of type '{type_name}'"
    else:
        message = f"{name} is not of type '{type_name}'"
    if explanation is not None:
        message += f": {explanation}"
    return message


class _validate_meta(type):
    __schema__: object
    __strict__: bool
    __subs__: Mapping[str, object]
    __dbg__: bool

    def __instancecheck__(cls, object_: object) -> bool:
        valid = _validate(
            cls.__schema__, object_, "object", strict=cls.__strict__, subs=cls.__subs__
        )
        if cls.__dbg__ and valid != "":
            print(f"DEBUG: {valid}")
        return valid == ""


def make_type(
    schema: object,
    name: str | None = None,
    strict: bool = True,
    debug: bool = False,
    subs: Mapping[str, object] = {},
) -> _validate_meta:
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
            "__dbg__": debug,
            "__subs__": subs,
        },
    )


class optional_key:
    key: object

    def __init__(self, key: object) -> None:
        self.key = key

    def __eq__(self, key: object) -> bool:
        if not isinstance(key, optional_key):
            return False
        return self.key == key.key

    def __hash__(self) -> int:
        return hash(self.key)


class _union(compiled_schema):
    schemas: list[compiled_schema]

    def __init__(
        self,
        schemas: tuple[object, ...],
        _deferred_compiles: _mapping | None = None,
    ) -> None:
        self.schemas = [
            _compile(s, _deferred_compiles=_deferred_compiles) for s in schemas
        ]

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        messages = []
        for schema in self.schemas:
            message = schema.__validate__(object_, name=name, strict=strict, subs=subs)
            if message == "":
                return ""
            else:
                messages.append(message)
        return " and ".join(messages)


class union:
    schemas: tuple[object, ...]

    def __init__(self, *schemas: object) -> None:
        self.schemas = schemas

    def __compile__(self, _deferred_compiles: _mapping | None = None) -> _union:
        return _union(self.schemas, _deferred_compiles=_deferred_compiles)


class _intersect(compiled_schema):
    schema: list[compiled_schema]

    def __init__(
        self,
        schemas: tuple[object, ...],
        _deferred_compiles: _mapping | None = None,
    ) -> None:
        self.schemas = [
            _compile(s, _deferred_compiles=_deferred_compiles) for s in schemas
        ]

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        for schema in self.schemas:
            message = schema.__validate__(object_, name=name, strict=strict, subs=subs)
            if message != "":
                return message
        return ""


class intersect:
    schemas: tuple[object, ...]

    def __init__(self, *schemas: object) -> None:
        self.schemas = schemas

    def __compile__(self, _deferred_compiles: _mapping | None = None) -> _intersect:
        return _intersect(self.schemas, _deferred_compiles=_deferred_compiles)


class _complement(compiled_schema):
    schema: compiled_schema

    def __init__(
        self, schema: object, _deferred_compiles: _mapping | None = None
    ) -> None:
        self.schema = _compile(schema, _deferred_compiles=_deferred_compiles)

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        message = self.schema.__validate__(object_, name=name, strict=strict, subs=subs)
        if message != "":
            return ""
        else:
            return f"{name} does not match the complemented schema"


class complement:
    schema: object

    def __init__(self, schema: object) -> None:
        self.schema = schema

    def __compile__(self, _deferred_compiles: _mapping | None = None) -> _complement:
        return _complement(self.schema, _deferred_compiles=_deferred_compiles)


class _lax(compiled_schema):
    schema: compiled_schema

    def __init__(
        self, schema: object, _deferred_compiles: _mapping | None = None
    ) -> None:
        self.schema = _compile(schema, _deferred_compiles=_deferred_compiles)

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        return self.schema.__validate__(object_, name=name, strict=False, subs=subs)


class lax:
    schema: object

    def __init__(self, schema: object) -> None:
        self.schema = schema

    def __compile__(self, _deferred_compiles: _mapping | None = None) -> _lax:
        return _lax(self.schema, _deferred_compiles=_deferred_compiles)


class _strict(compiled_schema):
    schema: compiled_schema

    def __init__(
        self, schema: object, _deferred_compiles: _mapping | None = None
    ) -> None:
        self.schema = _compile(schema, _deferred_compiles=_deferred_compiles)

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        return self.schema.__validate__(object_, name=name, strict=True, subs=subs)


class strict:
    def __init__(self, schema: object) -> None:
        self.schema = schema

    def __compile__(self, _deferred_compiles: _mapping | None = None) -> _strict:
        return _strict(self.schema, _deferred_compiles=_deferred_compiles)


class _set_label(compiled_schema):
    schema: compiled_schema
    labels: set[str]
    debug: bool

    def __init__(
        self,
        schema: object,
        labels: set[str],
        debug: bool,
        _deferred_compiles: _mapping | None = None,
    ) -> None:
        self.schema = _compile(schema, _deferred_compiles=_deferred_compiles)
        self.labels = labels
        self.debug = debug

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
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
            return _validate(subs[key], object_, name=name, strict=True, subs=subs)
        else:
            return self.schema.__validate__(object_, name=name, strict=True, subs=subs)


class set_label:
    schema: object
    labels: set[str]
    debug: bool

    def __init__(self, schema: object, *labels: str, debug: bool = False) -> None:
        self.schema = schema
        for L in labels:
            if not isinstance(L, str):
                raise SchemaError(f"The label {L} is not a string")
        self.labels = set(labels)
        if not isinstance(debug, bool):
            raise SchemaError(f"The option {debug} is not a boolean")
        self.debug = debug

    def __compile__(self, _deferred_compiles: _mapping | None = None) -> _set_label:
        return _set_label(
            self.schema, self.labels, self.debug, _deferred_compiles=_deferred_compiles
        )


class quote(compiled_schema):
    schema: _const

    def __init__(self, schema: object) -> None:
        self.schema = _const(schema, strict_eq=True)

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        return self.schema.__validate__(object_, name=name, strict=strict, subs=subs)


class _set_name(compiled_schema):
    reason: bool
    schema: compiled_schema
    __name__: str

    def __init__(
        self,
        schema: object,
        name: str,
        reason: bool = False,
        _deferred_compiles: _mapping | None = None,
    ) -> None:
        self.schema = _compile(schema, _deferred_compiles=_deferred_compiles)
        self.__name__ = name
        self.reason = reason

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        message = self.schema.__validate__(object_, name=name, strict=strict, subs=subs)
        if message != "":
            if not self.reason:
                return _wrong_type_message(object_, name, self.__name__)
            else:
                return _wrong_type_message(
                    object_, name, self.__name__, explanation=message, skip_value=True
                )
        return ""


class set_name:
    reason: bool
    schema: object
    name: str

    def __init__(self, schema: object, name: str, reason: bool = False) -> None:
        if not isinstance(name, str):
            raise SchemaError(f"The name {_c(name)} is not a string")
        self.schema = schema
        self.name = name
        self.reason = reason

    def __compile__(self, _deferred_compiles: _mapping | None = None) -> _set_name:
        return _set_name(
            self.schema,
            self.name,
            reason=self.reason,
            _deferred_compiles=_deferred_compiles,
        )


class regex(compiled_schema):
    regex: str
    fullmatch: bool
    __name__: str
    pattern: re.Pattern[str]

    def __init__(
        self,
        regex: str,
        name: str | None = None,
        fullmatch: bool = True,
        flags: int = 0,
    ) -> None:
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

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, str):
            return _wrong_type_message(object_, name, self.__name__)
        try:
            if self.fullmatch and self.pattern.fullmatch(object_):
                return ""
            elif not self.fullmatch and self.pattern.match(object_):
                return ""
        except Exception:
            pass
        return _wrong_type_message(object_, name, self.__name__)


class glob(compiled_schema):
    pattern: str
    __name__: str

    def __init__(self, pattern: str, name: str | None = None) -> None:
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

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, str):
            return _wrong_type_message(object_, name, self.__name__)
        try:
            if pathlib.PurePath(object_).match(self.pattern):
                return ""
            else:
                return _wrong_type_message(object_, name, self.__name__)
        except Exception as e:
            return _wrong_type_message(object_, name, self.__name__, str(e))


class magic(compiled_schema):
    mime_type: str
    __name__: str

    def __init__(self, mime_type: str, name: str | None = None) -> None:
        if not HAS_MAGIC:
            raise SchemaError("Failed to load python-magic")

        if not isinstance(mime_type, str):
            raise SchemaError(f"{repr(mime_type)} is not a string")

        self.mime_type = mime_type

        if name is None:
            self.__name__ = f"magic({repr(mime_type)})"
        else:
            self.__name__ = name

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, (str, bytes)):
            return _wrong_type_message(object_, name, self.__name__)
        try:
            object_mime_type = magic_.from_buffer(object_, mime=True)
        except Exception as e:
            return _wrong_type_message(object_, name, self.__name__, str(e))
        if object_mime_type != self.mime_type:
            return _wrong_type_message(
                object_,
                name,
                self.__name__,
                f"{repr(object_mime_type)} is different from {repr(self.mime_type)}",
            )
        return ""


class div(compiled_schema):
    divisor: int
    remainder: int
    __name__: str

    def __init__(
        self, divisor: int, remainder: int = 0, name: str | None = None
    ) -> None:
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

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, int):
            return _wrong_type_message(object_, name, "int")
        elif (object_ - self.remainder) % self.divisor == 0:
            return ""
        else:
            return _wrong_type_message(object_, name, self.__name__)


class close_to(compiled_schema):
    kw: dict[str, float]
    x: int | float
    __name__: str

    def __init__(
        self,
        x: int | float,
        rel_tol: int | float | None = None,
        abs_tol: int | float | None = None,
    ) -> None:
        self.kw = {}
        if not isinstance(x, (int, float)):
            raise SchemaError(f"{repr(x)} is not a number")
        if rel_tol is not None:
            if not isinstance(rel_tol, (int, float)):
                raise SchemaError(
                    f"The relative tolerance {repr(rel_tol)} is not a number"
                )
            self.kw["rel_tol"] = rel_tol
        if abs_tol is not None:
            if not isinstance(abs_tol, (int, float)):
                raise SchemaError(
                    f"The absolute tolerance {repr(abs_tol)} is not a number"
                )
            self.kw["abs_tol"] = abs_tol

        kwl = [str(x)] + [f"{k}={v}" for (k, v) in self.kw.items()]
        kwl_ = ",".join(kwl)
        self.__name__ = f"close_to({kwl_})"
        self.x = x

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, (float, int)):
            return _wrong_type_message(object_, name, "number")
        elif math.isclose(object_, self.x, **self.kw):
            return ""
        else:
            return _wrong_type_message(object_, name, self.__name__)


class gt(compiled_schema):
    lb: comparable

    def __init__(self, lb: comparable) -> None:
        try:
            lb <= lb
        except Exception:
            raise SchemaError(
                f"The lower bound {lb} does not support comparison"
            ) from None
        self.lb = lb

    def message(self, name: str, object_: object) -> str:
        return f"{name} (value:{_c(object_)}) is not strictly greater than {self.lb}"

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        try:
            if self.lb < object_:
                return ""
            else:
                return self.message(name, object_)
        except Exception as e:
            return f"{self.message(name, object_)}: {str(e)}"


class ge(compiled_schema):
    lb: comparable

    def __init__(self, lb: comparable) -> None:
        try:
            lb <= lb
        except Exception:
            raise SchemaError(
                f"The lower bound {lb} does not support comparison"
            ) from None
        self.lb = lb

    def message(self, name: str, object_: object) -> str:
        return f"{name} (value:{_c(object_)}) is not greater than or equal to {self.lb}"

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        try:
            if self.lb <= object_:
                return ""
            else:
                return self.message(name, object_)
        except Exception as e:
            return f"{self.message(name, object_)}: {str(e)}"


class lt(compiled_schema):
    ub: comparable

    def __init__(self, ub: comparable) -> None:
        try:
            ub <= ub
        except Exception:
            raise SchemaError(
                f"The upper bound {ub} does not support comparison"
            ) from None
        self.ub = ub

    def message(self, name: str, object_: object) -> str:
        return f"{name} (value:{_c(object_)}) is not strictly less than {self.ub}"

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        try:
            if self.ub > object_:
                return ""
            else:
                return self.message(name, object_)
        except Exception as e:
            return f"{self.message(name, object_)}: {str(e)}"


class le(compiled_schema):
    ub: comparable

    def __init__(self, ub: comparable) -> None:
        try:
            ub <= ub
        except Exception:
            raise SchemaError(
                f"The upper bound {ub} does not support comparison"
            ) from None
        self.ub = ub

    def message(self, name: str, object_: object) -> str:
        return f"{name} (value:{_c(object_)}) is not less than or equal to {self.ub}"

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        try:
            if self.ub >= object_:
                return ""
            else:
                return self.message(name, object_)
        except Exception as e:
            return f"{self.message(name, object_)}: {str(e)}"


class interval(compiled_schema):
    lb_s: str
    ub_s: str

    def __init__(
        self,
        lb: comparable | types.EllipsisType,
        ub: comparable | types.EllipsisType,
        strict_lb: bool = False,
        strict_ub: bool = False,
    ) -> None:

        self.lb_s = "..." if lb == ... else repr(lb)
        self.ub_s = "..." if ub == ... else repr(ub)

        ld = "]" if strict_lb else "["
        ud = "[" if strict_ub else "]"

        if lb is not ...:
            lower: gt | ge
            if strict_lb:
                lower = gt(lb)
            else:
                lower = ge(lb)

        if ub is not ...:
            upper: lt | le
            if strict_ub:
                upper = lt(ub)
            else:
                upper = le(ub)

        if lb is not ... and ub is not ...:
            try:
                lb <= ub
            except Exception:
                raise SchemaError(
                    f"The upper and lower bound in the interval"
                    f" {ld}{self.lb_s},{self.ub_s}{ud} are incomparable"
                ) from None
            setattr(self, "__validate__", _intersect((lower, upper)).__validate__)
        elif ub is not ...:
            try:
                ub <= ub
            except Exception:
                raise SchemaError(
                    f"The upper bound in the interval"
                    f" {ld}{self.lb_s},{self.ub_s}{ud} does not support comparison"
                ) from None
            setattr(self, "__validate__", upper.__validate__)
        elif lb is not ...:
            try:
                lb <= lb
            except Exception:
                raise SchemaError(
                    f"The lower bound in the interval"
                    f" {ld}{self.lb_s},{self.ub_s}{ud} does not support comparison"
                ) from None
            setattr(self, "__validate__", lower.__validate__)
        else:
            setattr(self, "__validate__", anything().__validate__)


class size(compiled_schema):
    interval_: interval

    def __init__(self, lb: int, ub: int | types.EllipsisType | None = None) -> None:
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
        self.interval_ = interval(lb, ub)

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, Sized):
            return f"{name} (value:{_c(object_)}) has no len()"

        L = len(object_)

        return self.interval_.__validate__(L, f"len({name})", strict, subs)


class _deferred(compiled_schema):
    collection: _mapping
    key: object

    def __init__(self, collection: _mapping, key: object) -> None:
        self.collection = collection
        self.key = key

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if self.key not in self.collection:
            raise ValidationError(f"{name}: key {self.key} is unknown")
        return self.collection[self.key].__validate__(
            object_, name=name, strict=strict, subs=subs
        )


class _mapping:
    mapping: dict[int, tuple[object, compiled_schema, bool]]

    def __init__(self) -> None:
        self.mapping = {}

    def __setitem__(self, key: object, value: compiled_schema) -> None:
        self.mapping[id(key)] = (key, value, False)

    def __getitem__(self, key: object) -> compiled_schema:
        return self.mapping[id(key)][1]

    def __delitem__(self, key: object) -> None:
        del self.mapping[id(key)]

    def __contains__(self, key: object) -> bool:
        return id(key) in self.mapping

    def in_use(self, key: object) -> bool:
        return self.mapping[id(key)][2]

    def set_in_use(self, key: object, value: bool) -> None:
        m = self.mapping[id(key)]
        self.mapping[id(key)] = (m[0], m[1], value)


class _validate_schema(compiled_schema):
    schema: object

    def __init__(self, schema: object) -> None:
        if not hasattr(schema, "__validate__"):
            raise SchemaError(f"schema {repr(schema)} " "cannot be used for validation")
        setattr(self, "__validate__", schema.__validate__)


def compile(schema: object) -> compiled_schema:
    return _compile(schema, _deferred_compiles=None)


def _compile(
    schema: object, _deferred_compiles: _mapping | None = None
) -> compiled_schema:
    if _deferred_compiles is None:
        _deferred_compiles = _mapping()
    # avoid infinite loop in case of a recursive schema
    if schema in _deferred_compiles:
        if isinstance(_deferred_compiles[schema], _deferred):
            _deferred_compiles.set_in_use(schema, True)
            return _deferred_compiles[schema]
    _deferred_compiles[schema] = _deferred(_deferred_compiles, schema)

    # real work starts here
    if supports_Generics:
        origin = typing.get_origin(schema)
    else:
        origin = object()

    ret: compiled_schema
    if isinstance(schema, type) and issubclass(schema, compiled_schema):
        try:
            ret = schema()
        except Exception:
            raise SchemaError(
                f"{repr(schema.__name__)} does " f"not have a no-argument constructor"
            ) from None
    elif hasattr(schema, "__validate__"):
        ret = _validate_schema(schema)
    elif hasattr(schema, "__compile__"):
        ret = schema.__compile__(_deferred_compiles=_deferred_compiles)
    elif isinstance(schema, compiled_schema):
        ret = schema
    elif supports_TypedDict and typing.is_typeddict(schema):
        ret = _compile(
            protocol(schema, dict=True), _deferred_compiles=_deferred_compiles
        )
    elif isinstance(schema, type) and hasattr(schema, "_is_protocol"):
        assert hasattr(schema, "__name__") and isinstance(schema.__name__, str)
        ret = _compile(protocol(schema), _deferred_compiles=_deferred_compiles)
    elif (
        isinstance(schema, type)
        and issubclass(schema, tuple)
        and hasattr(schema, "_fields")
    ):
        ret = _compile(
            intersect(tuple, protocol(schema)), _deferred_compiles=_deferred_compiles
        )
    elif schema == Any:
        ret = anything()
    elif hasattr(schema, "__name__") and hasattr(schema, "__supertype__"):
        ret = _NewType(
            schema,
            _deferred_compiles=_deferred_compiles,
        )
    elif origin == tuple:
        ret = _Tuple(typing.get_args(schema), _deferred_compiles=_deferred_compiles)
    elif isinstance(origin, type) and issubclass(origin, Sequence):
        ret = _List(
            typing.get_args(schema)[0],
            type_schema=origin,
            _deferred_compiles=_deferred_compiles,
        )
    elif isinstance(origin, type) and issubclass(origin, Mapping):
        ret = _Dict(
            typing.get_args(schema),
            type_schema=origin,
            _deferred_compiles=_deferred_compiles,
        )
    elif origin == Union:
        ret = _Union(typing.get_args(schema), _deferred_compiles=_deferred_compiles)
    elif supports_Literal and origin == Literal:
        ret = _Literal(typing.get_args(schema), _deferred_compiles=_deferred_compiles)
    elif supports_Annotated and origin == Annotated:
        ret = _Annotated(typing.get_args(schema), _deferred_compiles=_deferred_compiles)
    elif supports_UnionType and isinstance(schema, UnionType):
        ret = _Union(schema.__args__, _deferred_compiles=_deferred_compiles)
    elif isinstance(schema, type):
        ret = _type(schema)
    elif callable(schema):
        ret = _callable(schema)
    elif isinstance(schema, Sequence) and not isinstance(schema, str):
        ret = _sequence(schema, _deferred_compiles=_deferred_compiles)
    elif isinstance(schema, Mapping):
        ret = _dict(schema, _deferred_compiles=_deferred_compiles)
    elif isinstance(schema, set):
        ret = _set(schema, _deferred_compiles=_deferred_compiles)
    else:
        ret = _const(schema)

    # back to updating the cache
    if _deferred_compiles.in_use(schema):
        _deferred_compiles[schema] = ret
    else:
        del _deferred_compiles[schema]
    return ret


def _validate(
    schema: object,
    object_: object,
    name: str = "object",
    strict: bool = True,
    subs: Mapping[str, object] = {},
) -> str:
    return compile(schema).__validate__(object_, name=name, strict=strict, subs=subs)


def validate(
    schema: object,
    object_: object,
    name: str = "object",
    strict: bool = True,
    subs: Mapping[str, object] = {},
) -> None:
    message = _validate(
        schema,
        object_,
        name=name,
        strict=strict,
        subs=subs,
    )
    if message != "":
        raise ValidationError(message)


# Some predefined schemas


class number(compiled_schema):
    # functionally equivalent to float
    def __init__(self) -> None:
        warnings.warn(
            "The schema 'number' is deprecated. Use 'float' instead.",
            DeprecationWarning,
        )

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if isinstance(object_, (int, float)):
            return ""
        else:
            return _wrong_type_message(object_, name, "number")


class email(compiled_schema):
    kw: dict[str, Any]

    def __init__(self, **kw: Any) -> None:
        self.kw = kw
        if "dns_resolver" not in kw:
            self.kw["dns_resolver"] = _get_dns_resolver()
        if "check_deliverability" not in kw:
            self.kw["check_deliverability"] = False

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, str):
            return _wrong_type_message(
                object_, name, "email", f"{_c(object_)} is not a string"
            )
        try:
            email_validator.validate_email(object_, **self.kw)
            return ""
        except Exception as e:
            return _wrong_type_message(object_, name, "email", str(e))


class ip_address(compiled_schema):

    __name__: str
    method: Callable[[Any], Any]

    def __init__(self, version: Literal[4, 6] | None = None) -> None:
        if version is not None and version not in (4, 6):
            raise SchemaError("version is not 4 or 6")
        if version is None:
            self.__name__ = "ip_address"
        else:
            self.__name__ = f"ip_address(version={version})"
        if version == 4:
            self.method = ipaddress.IPv4Address
        elif version == 6:
            self.method = ipaddress.IPv6Address
        else:
            self.method = ipaddress.ip_address

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, (int, str, bytes)):
            return _wrong_type_message(object_, name, self.__name__)
        try:
            self.method(object_)
        except ValueError as e:
            return _wrong_type_message(object_, name, self.__name__, explanation=str(e))
        return ""


class url(compiled_schema):
    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, str):
            return _wrong_type_message(object_, name, "url")
        result = urllib.parse.urlparse(object_)
        if all([result.scheme, result.netloc]):
            return ""
        return _wrong_type_message(object_, name, "url")


class date_time(compiled_schema):
    format: str | None
    __name__: str

    def __init__(self, format: str | None = None) -> None:
        self.format = format
        if format is not None:
            self.__name__ = f"date_time({repr(format)})"
        else:
            self.__name__ = "date_time"

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, str):
            return _wrong_type_message(object_, name, self.__name__)
        if self.format is not None:
            try:
                datetime.datetime.strptime(object_, self.format)
            except Exception as e:
                return _wrong_type_message(object_, name, self.__name__, str(e))
        else:
            try:
                datetime.datetime.fromisoformat(object_)
            except Exception as e:
                return _wrong_type_message(object_, name, self.__name__, str(e))
        return ""


class date(compiled_schema):
    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, str):
            return _wrong_type_message(object_, name, "date")
        try:
            datetime.date.fromisoformat(object_)
        except Exception as e:
            return _wrong_type_message(object_, name, "date", str(e))
        return ""


class time(compiled_schema):
    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, str):
            return _wrong_type_message(object_, name, "date")
        try:
            datetime.time.fromisoformat(object_)
        except Exception as e:
            return _wrong_type_message(object_, name, "time", str(e))
        return ""


class nothing(compiled_schema):
    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        return _wrong_type_message(object_, name, "nothing")


class anything(compiled_schema):
    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        return ""


class domain_name(compiled_schema):
    re_asci: re.Pattern[str]
    ascii_only: bool
    resolve: bool
    __name__: str

    def __init__(self, ascii_only: bool = True, resolve: bool = False) -> None:
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

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, str):
            return _wrong_type_message(object_, name, self.__name__)
        if self.ascii_only:
            if not self.re_ascii.fullmatch(object_):
                return _wrong_type_message(
                    object_, name, self.__name__, "Non-ascii characters"
                )
        try:
            idna.encode(object_, uts46=False)
        except idna.core.IDNAError as e:
            return _wrong_type_message(object_, name, self.__name__, str(e))

        if self.resolve:
            try:
                _get_dns_resolver().resolve(object_)
            except Exception as e:
                return _wrong_type_message(object_, name, self.__name__, str(e))
        return ""


class at_least_one_of(compiled_schema):
    args: tuple[object, ...]
    __name__: str

    def __init__(self, *args: object) -> None:
        self.args = args
        args_s = [repr(a) for a in args]
        self.__name__ = f"{self.__class__.__name__}({','.join(args_s)})"

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, Mapping):
            return _wrong_type_message(object_, name, self.__name__)
        try:
            if any([a in object_ for a in self.args]):
                return ""
            else:
                return _wrong_type_message(object_, name, self.__name__)
        except Exception as e:
            return _wrong_type_message(object_, name, self.__name__, str(e))


class at_most_one_of(compiled_schema):
    args: tuple[object, ...]
    __name__: str

    def __init__(self, *args: object) -> None:
        self.args = args
        args_s = [repr(a) for a in args]
        self.__name__ = f"{self.__class__.__name__}({','.join(args_s)})"

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, Mapping):
            return _wrong_type_message(object_, name, self.__name__)
        try:
            if sum([a in object_ for a in self.args]) <= 1:
                return ""
            else:
                return _wrong_type_message(object_, name, self.__name__)
        except Exception as e:
            return _wrong_type_message(object_, name, self.__name__, str(e))


class one_of(compiled_schema):
    args: tuple[object, ...]
    __name__: str

    def __init__(self, *args: object) -> None:
        self.args = args
        args_s = [repr(a) for a in args]
        self.__name__ = f"{self.__class__.__name__}({','.join(args_s)})"

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, Mapping):
            return _wrong_type_message(object_, name, self.__name__)
        try:
            if sum([a in object_ for a in self.args]) == 1:
                return ""
            else:
                return _wrong_type_message(object_, name, self.__name__)
        except Exception as e:
            return _wrong_type_message(object_, name, self.__name__, str(e))


class keys(compiled_schema):
    args: tuple[object, ...]

    def __init__(self, *args: object) -> None:
        self.args = args

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, Mapping):
            return _wrong_type_message(object_, name, "Mapping")  # TODO: __name__
        for k in self.args:
            if k not in object_:
                return f"{name}[{repr(k)}] is missing"
        return ""


class _ifthen(compiled_schema):
    if_schema: compiled_schema
    then_schema: compiled_schema
    else_schema: compiled_schema | None

    def __init__(
        self,
        if_schema: object,
        then_schema: object,
        else_schema: object | None = None,
        _deferred_compiles: _mapping | None = None,
    ) -> None:
        self.if_schema = _compile(if_schema, _deferred_compiles=_deferred_compiles)
        self.then_schema = _compile(then_schema, _deferred_compiles=_deferred_compiles)
        if else_schema is not None:
            self.else_schema = _compile(
                else_schema, _deferred_compiles=_deferred_compiles
            )
        else:
            self.else_schema = else_schema

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if (
            self.if_schema.__validate__(object_, name=name, strict=strict, subs=subs)
            == ""
        ):
            return self.then_schema.__validate__(
                object_, name=name, strict=strict, subs=subs
            )
        elif self.else_schema is not None:
            return self.else_schema.__validate__(
                object_, name=name, strict=strict, subs=subs
            )
        return ""


class ifthen:
    if_schema: object
    then_schema: object
    else_schema: object | None

    def __init__(
        self,
        if_schema: object,
        then_schema: object,
        else_schema: object | None = None,
    ) -> None:
        self.if_schema = if_schema
        self.then_schema = then_schema
        self.else_schema = else_schema

    def __compile__(self, _deferred_compiles: _mapping | None = None) -> _ifthen:
        return _ifthen(
            self.if_schema,
            self.then_schema,
            else_schema=self.else_schema,
            _deferred_compiles=_deferred_compiles,
        )


class _cond(compiled_schema):
    conditions: list[tuple[compiled_schema, compiled_schema]]

    def __init__(
        self,
        args: tuple[tuple[object, object], ...],
        _deferred_compiles: _mapping | None = None,
    ) -> None:
        self.conditions = []
        for c in args:
            self.conditions.append(
                (
                    _compile(c[0], _deferred_compiles=_deferred_compiles),
                    _compile(c[1], _deferred_compiles=_deferred_compiles),
                )
            )

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        for c in self.conditions:
            if c[0].__validate__(object_, name=name, strict=strict, subs=subs) == "":
                return c[1].__validate__(object_, name=name, strict=strict, subs=subs)
        return ""


class cond:
    args: tuple[tuple[object, object], ...]

    def __init__(self, *args: tuple[object, object]) -> None:
        for c in args:
            if not isinstance(c, tuple) or len(c) != 2:
                raise SchemaError(f"{repr(c)} is not a tuple of length two")
        self.args = args

    def __compile__(self, _deferred_compiles: _mapping | None = None) -> _cond:
        return _cond(self.args, _deferred_compiles=_deferred_compiles)


class _fields(compiled_schema):
    d: dict[str, compiled_schema]

    def __init__(
        self, d: Mapping[str, object], _deferred_compiles: _mapping | None = None
    ) -> None:
        self.d = {}
        for k, v in d.items():
            self.d[k] = _compile(v, _deferred_compiles=_deferred_compiles)

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        for k, v in self.d.items():
            name_ = f"{name}.{k}"
            if not hasattr(object_, k):
                return f"{name_} is missing"
            ret = self.d[k].__validate__(
                getattr(object_, k), name=name_, strict=strict, subs=subs
            )
            if ret != "":
                return ret
        return ""


class fields:
    def __init__(self, d: object) -> None:
        if not isinstance(d, Mapping):
            raise SchemaError(f"{repr(d)} is not a Mapping")
        for k in d:
            if not isinstance(k, str):
                raise SchemaError(f"key {repr(k)} in {repr(d)} is not a string")
        self.d = d

    def __compile__(self, _deferred_compiles: _mapping | None = None) -> _fields:
        return _fields(self.d, _deferred_compiles=_deferred_compiles)


class _filter(compiled_schema):
    filter: Callable[[Any], object]
    schema: compiled_schema
    filter_name: str

    def __init__(
        self,
        filter: Callable[[Any], object],
        schema: object,
        filter_name: str | None = None,
        _deferred_compiles: _mapping | None = None,
    ) -> None:
        self.filter = filter
        self.schema = _compile(schema, _deferred_compiles=_deferred_compiles)
        if filter_name is not None:
            self.filter_name = filter_name
        else:
            try:
                self.filter_name = self.filter.__name__
            except Exception:
                self.filter_name = "filter"
            if self.filter_name == "<lambda>":
                self.filter_name = "filter"

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        try:
            object_ = self.filter(object_)
        except Exception as e:
            return (
                f"Applying {self.filter_name} to {name} "
                f"(value: {_c(object_)}) failed: {str(e)}"
            )
        name = f"{self.filter_name}({name})"
        return self.schema.__validate__(
            object_, name="object", strict=strict, subs=subs
        )


class filter:
    filter: Callable[[Any], object]
    schema: object
    filter_name: str | None

    def __init__(
        self,
        filter: Callable[[Any], object],
        schema: object,
        filter_name: str | None = None,
    ) -> None:
        if filter_name is not None and not isinstance(filter_name, str):
            raise SchemaError("The filter name is not a string")
        if not callable(filter):
            raise SchemaError("The filter is not callable")
        self.filter = filter
        self.schema = schema
        self.filter_name = filter_name

    def __compile__(self, _deferred_compiles: _mapping | None = None) -> _filter:
        return _filter(
            self.filter,
            self.schema,
            filter_name=self.filter_name,
            _deferred_compiles=None,
        )


class _type(compiled_schema):
    schema: type

    def __init__(self, schema: type, math_numbers: bool = True) -> None:
        if math_numbers:
            if schema == float:
                setattr(self, "__validate__", self.__validate_float__)
            if schema == complex:
                setattr(self, "__validate__", self.__validate_complex__)
        self.schema = schema

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        try:
            if self.schema == float and isinstance(object_, int):
                return ""
            if not isinstance(object_, self.schema):
                return _wrong_type_message(object_, name, self.schema.__name__)
            else:
                return ""
        except Exception as e:
            return f"{self.schema} is not a valid type: {str(e)}"

    def __validate_float__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        # consider int as a subtype of float
        if isinstance(object_, (int, float)):
            return ""
        else:
            return _wrong_type_message(object_, name, "float")

    def __validate_complex__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        # consider int, float as subtypes of complex
        if isinstance(object_, (int, float, complex)):
            return ""
        else:
            return _wrong_type_message(object_, name, "complex")

    def __str__(self) -> str:
        return self.schema.__name__


class _sequence(compiled_schema):
    type_schema: Type[Sequence[object]]
    schema: list[compiled_schema]
    fill: compiled_schema

    def __init__(
        self,
        schema: Sequence[object],
        type_schema: type | None = None,
        _deferred_compiles: _mapping | None = None,
    ) -> None:
        if type_schema is None:
            self.type_schema = type(schema)
        else:
            self.type_schema = type_schema
        self.schema = [
            _compile(o, _deferred_compiles=_deferred_compiles)
            for o in schema
            if o is not ...
        ]
        if len(schema) > 0 and schema[-1] is ...:
            if len(schema) >= 2:
                self.fill = self.schema[-1]
                self.schema = self.schema[:-1]
            else:
                self.fill = _type(object)
                self.schema = []
            setattr(self, "__validate__", self.__validate_ellipsis__)

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, self.type_schema):
            return _wrong_type_message(object_, name, self.type_schema.__name__)
        ls = len(self.schema)
        lo = len(object_)
        if strict:
            if lo > ls:
                return f"{name}[{ls}] is not in the schema"
        if ls > lo:
            return f"{name}[{lo}] is missing"
        for i in range(ls):
            name_ = f"{name}[{i}]"
            ret = self.schema[i].__validate__(object_[i], name_, strict, subs)
            if ret != "":
                return ret
        return ""

    def __validate_ellipsis__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, self.type_schema):
            return _wrong_type_message(object_, name, self.type_schema.__name__)
        ls = len(self.schema)
        lo = len(object_)
        if ls > lo:
            return f"{name}[{lo}] is missing"
        for i in range(ls):
            name_ = f"{name}[{i}]"
            ret = self.schema[i].__validate__(object_[i], name_, strict, subs)
            if ret != "":
                return ret
        for i in range(ls, lo):
            name_ = f"{name}[{i}]"
            ret = self.fill.__validate__(object_[i], name_, strict, subs)
            if ret != "":
                return ret
        return ""

    def __str__(self) -> str:
        return str(self.schema)


class _const(compiled_schema):
    schema: object

    def __init__(self, schema: object, strict_eq: bool = False) -> None:
        self.schema = schema
        if isinstance(schema, float) and not strict_eq:
            setattr(self, "__validate__", close_to(schema).__validate__)

    def message(self, name: str, object_: object) -> str:
        return f"{name} (value:{_c(object_)}) is not equal to {repr(self.schema)}"

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if object_ != self.schema:
            return self.message(name, object_)
        return ""

    def __str__(self) -> str:
        return str(self.schema)


class _callable(compiled_schema):
    schema: Callable[[Any], bool]
    __name__: str

    def __init__(self, schema: Callable[[Any], bool]) -> None:
        self.schema = schema
        try:
            self.__name__ = self.schema.__name__
        except Exception:
            self.__name__ = str(self.schema)

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        try:
            if self.schema(object_):
                return ""
            else:
                return _wrong_type_message(object_, name, self.__name__)
        except Exception as e:
            return _wrong_type_message(object_, name, self.__name__, str(e))

    def __str__(self) -> str:
        return str(self.schema)


class _dict(compiled_schema):
    min_keys: set[object]
    const_keys: set[object]
    other_keys: set[compiled_schema]
    schema: dict[object, compiled_schema]
    type_schema: Type[Mapping[object, object]]

    def __init__(
        self,
        schema: Mapping[object, object],
        type_schema: type | None = None,
        _deferred_compiles: _mapping | None = None,
    ) -> None:
        if type_schema is None:
            self.type_schema = type(schema)
        else:
            self.type_schema = type_schema
        self.min_keys = set()
        self.const_keys = set()
        self.other_keys = set()
        self.schema = {}
        for k in schema:
            compiled_schema = _compile(schema[k], _deferred_compiles=_deferred_compiles)
            optional = True
            if isinstance(k, optional_key):
                key = k.key
            elif isinstance(k, str) and len(k) > 0 and k[-1] == "?":
                key = k[:-1]
            else:
                optional = False
                key = k
            c = _compile(key, _deferred_compiles=_deferred_compiles)
            if isinstance(c, _const):
                if not optional:
                    self.min_keys.add(key)
                self.const_keys.add(key)
                self.schema[key] = compiled_schema
            else:
                self.other_keys.add(c)
                self.schema[c] = compiled_schema

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, self.type_schema):
            return _wrong_type_message(object_, name, self.type_schema.__name__)

        for k in self.min_keys:
            if k not in object_:
                name_ = f"{name}[{repr(k)}]"
                return f"{name_} is missing"

        for k in object_:
            vals = []
            name_ = f"{name}[{repr(k)}]"
            if k in self.const_keys:
                val = self.schema[k].__validate__(
                    object_[k], name=name_, strict=strict, subs=subs
                )
                if val == "":
                    continue
                else:
                    vals.append(val)

            for kk in self.other_keys:
                if kk.__validate__(k, name="key", strict=strict, subs=subs) == "":
                    val = self.schema[kk].__validate__(
                        object_[k], name=name_, strict=strict, subs=subs
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

    def __str__(self) -> str:
        return str(self.schema)


class _set(compiled_schema):
    schema: compiled_schema
    schema_: set[object]

    def __init__(
        self, schema: set[object], _deferred_compiles: _mapping | None = None
    ) -> None:
        self.schema_ = schema
        if len(schema) == 0:
            self.schema = _const(set())
            setattr(self, "__validate__", self.__validate_empty_set__)
        elif len(schema) == 1:
            self.schema = _compile(
                tuple(schema)[0], _deferred_compiles=_deferred_compiles
            )
            setattr(self, "__validate__", self.__validate_singleton__)
        else:
            self.schema = _union(tuple(schema), _deferred_compiles=_deferred_compiles)

    def __validate_empty_set__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        return self.schema.__validate__(object_, name=name, strict=True, subs=subs)

    def __validate_singleton__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, set):
            return _wrong_type_message(object_, name, "set")
        for i, o in enumerate(object_):
            name_ = f"{name}{{{i}}}"
            v = self.schema.__validate__(o, name=name_, strict=True, subs=subs)
            if v != "":
                return v
        return ""

    def __validate__(
        self,
        object_: object,
        name: str = "object",
        strict: bool = True,
        subs: Mapping[str, object] = {},
    ) -> str:
        if not isinstance(object_, set):
            return _wrong_type_message(object_, name, "set")
        for i, o in enumerate(object_):
            name_ = f"{name}{{{i}}}"
            v = self.schema.__validate__(o, name=name_, strict=True, subs=subs)
            if v != "":
                return v
        return ""

    def __str__(self) -> str:
        return str(self.schema_)


class protocol:
    type_dict: dict[object, object]
    dict: bool
    __name__: str

    def __init__(self, schema: object, dict: bool = False):
        if not isinstance(dict, bool):
            raise SchemaError("bool flag is not a bool")
        type_hints = _get_type_hints(schema)
        self.dict = dict
        total = True
        if hasattr(schema, "__total__") and isinstance(schema.__total__, bool):
            total = schema.__total__
        self.type_dict = _to_dict(type_hints, total=total)
        if hasattr(schema, "__name__") and isinstance(schema.__name__, str):
            self.__name__ = schema.__name__
        else:
            self.__name__ = "schema"

    def __compile__(
        self, _deferred_compiles: _mapping | None = None
    ) -> compiled_schema:
        if not self.dict:
            return _set_name(
                fields(self.type_dict),
                self.__name__,
                reason=True,
                _deferred_compiles=_deferred_compiles,
            )
        else:
            return _set_name(
                dict(self.type_dict),
                self.__name__,
                reason=True,
                _deferred_compiles=_deferred_compiles,
            )


class _Literal(compiled_schema):
    def __init__(
        self, schema: tuple[object, ...], _deferred_compiles: _mapping | None = None
    ) -> None:
        setattr(
            self,
            "__validate__",
            _union(schema, _deferred_compiles=_deferred_compiles).__validate__,
        )


class _Union(compiled_schema):
    def __init__(
        self, schema: tuple[object, ...], _deferred_compiles: _mapping | None = None
    ) -> None:
        setattr(
            self,
            "__validate__",
            _union(schema, _deferred_compiles=_deferred_compiles).__validate__,
        )


class _List(compiled_schema):
    def __init__(
        self,
        schema: object,
        type_schema: type | None = None,
        _deferred_compiles: _mapping | None = None,
    ) -> None:
        setattr(
            self,
            "__validate__",
            _sequence(
                [schema, ...],
                type_schema=type_schema,
                _deferred_compiles=_deferred_compiles,
            ).__validate__,
        )


class _Tuple(compiled_schema):
    def __init__(
        self, schema: tuple[object, ...], _deferred_compiles: _mapping | None = None
    ) -> None:
        setattr(
            self,
            "__validate__",
            _sequence(schema, _deferred_compiles=_deferred_compiles).__validate__,
        )


class _Dict(compiled_schema):
    def __init__(
        self,
        schema: tuple[object, ...],
        type_schema: type | None = None,
        _deferred_compiles: _mapping | None = None,
    ) -> None:
        k, v = schema
        setattr(
            self,
            "__validate__",
            _dict(
                {k: v}, type_schema=type_schema, _deferred_compiles=_deferred_compiles
            ).__validate__,
        )


class _NewType(compiled_schema):
    def __init__(
        self, schema: object, _deferred_compiles: _mapping | None = None
    ) -> None:
        assert hasattr(schema, "__name__") and hasattr(schema, "__supertype__")
        c = _set_name(
            schema.__supertype__, schema.__name__, _deferred_compiles=_deferred_compiles
        )
        setattr(
            self,
            "__validate__",
            c.__validate__,
        )


class _Annotated(compiled_schema):
    def __init__(
        self, schema: tuple[object, ...], _deferred_compiles: _mapping | None = None
    ) -> None:
        collect: list[object] = []
        for s in schema:
            if not isinstance(s, Apply):
                collect.append(s)
            else:
                collect = [s(tuple(collect))]
        collect_ = tuple(collect)
        c: compiled_schema
        if len(collect_) == 0:
            c = anything()
        elif len(collect_) == 1:
            c = _compile(collect_[0], _deferred_compiles=_deferred_compiles)
        else:
            c = _intersect(collect_, _deferred_compiles=_deferred_compiles)
        setattr(
            self,
            "__validate__",
            c.__validate__,
        )
