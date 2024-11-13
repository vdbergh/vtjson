from __future__ import annotations

import json
import re
import sys
import unittest
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import (
    Any,
    Dict,
    Generator,
    List,
    NamedTuple,
    NewType,
    Tuple,
    TypeVar,
    Union,
    overload,
)
from urllib.parse import urlparse

import vtjson

try:
    from typing import NotRequired, Required
except Exception:
    pass

try:
    from typing import Literal
except Exception:
    pass

try:
    from typing import TypedDict
except Exception:
    pass

try:
    from typing import Annotated
except Exception:
    pass

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


try:
    from typing import assert_type

    has_assert_type = True
except Exception:
    has_assert_type = False

from vtjson import (
    Apply,
    SchemaError,
    ValidationError,
    anything,
    at_least_one_of,
    at_most_one_of,
    close_to,
    compile,
    compiled_schema,
    complement,
    cond,
    date,
    date_time,
    div,
    domain_name,
    email,
    fields,
    filter,
    ge,
    glob,
    gt,
    ifthen,
    intersect,
    interval,
    ip_address,
    keys,
    lax,
    le,
    lt,
    magic,
    make_type,
    nothing,
    number,
    one_of,
    optional_key,
    protocol,
    quote,
    regex,
    safe_cast,
    set_label,
    set_name,
    size,
    strict,
    time,
    union,
    url,
    validate,
)


def show(mc: Any) -> None:
    exception = mc.exception
    print(f"{exception.__class__.__name__}: {str(mc.exception)}")


class TestValidation(unittest.TestCase):
    def test_recursion(self) -> None:
        object_: object
        a: Dict[str, object] = {}
        a["a?"] = a
        object_ = {"a": {}}
        validate(a, object_)
        object_ = {"a": {"a": {}}}
        validate(a, object_)
        object_ = {"a": {"a": {"a": {}}}}
        validate(a, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = {"a": {"a": {"b": {}}}}
            validate(a, object_)
        show(mc)

        person: Dict[str, object] = {}
        person["mother"] = union(person, "unknown")
        person["father"] = union(person, "unknown")
        person["name"] = str
        object_ = {
            "name": "John",
            "father": {"name": "Carlo", "father": "unknown", "mother": "unknown"},
            "mother": {"name": "Iris", "father": "unknown", "mother": "unknown"},
        }
        validate(person, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = {
                "name": "John",
                "father": {"name": "Carlo", "father": "unknown", "mother": "unknown"},
                "mother": {"name": "Iris", "father": "unknown", "mother": "Sarah"},
            }
            validate(person, object_)
        show(mc)

        a = {}
        a["a?"] = intersect(a)
        object_ = {"a": {}}
        validate(a, object_)
        object_ = {"a": {"a": {}}}
        validate(a, object_)
        object_ = {"a": {"a": {"a": {}}}}
        validate(a, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = {"a": {"a": {"b": {}}}}
            validate(a, object_)
        show(mc)

        a = {}
        b: Dict[str, object] = {}
        a["a?"] = union(b, a)
        object_ = {"a": {}}
        validate(a, object_)
        object_ = {"a": {"a": {}}}
        validate(a, object_)
        object_ = {"a": {"a": {"a": {}}}}
        validate(a, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = {"a": {"a": {"b": {}}}}
            validate(a, object_)
        show(mc)

        a = {}
        b = {}
        a["b"] = union(b, None)
        b["a"] = union(a, None)
        object_ = {"b": {"a": {"b": None}}}
        validate(a, object_)
        with self.assertRaises(ValidationError) as mc:
            validate(b, object_)
        show(mc)

    def test_immutable(self) -> None:
        schema: object
        object_: object
        L = ["a"]
        schema = compile(L)
        object_ = ["a"]
        validate(schema, object_)
        L[0] = "b"
        validate(schema, object_)
        L2 = {"a": 1}
        schema = compile(L2)
        object_ = {"a": 1}
        validate(schema, object_)
        L2["b"] = 2
        validate(schema, object_)

    def test_glob(self) -> None:
        schema: object
        object_: object
        schema = glob("*.txt")
        object_ = "hello.txt"
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = "hello.doc"
            validate(schema, object_)
        show(mc)
        with self.assertRaises(SchemaError) as mc_:
            schema = glob({})  # type: ignore
        show(mc_)
        with self.assertRaises(SchemaError) as mc_:
            schema = glob({}, name="Invalid")  # type: ignore
        show(mc_)
        with self.assertRaises(ValidationError) as mc:
            schema = glob("*.txt", name="text_file")
            object_ = "hello.doc"
            validate(schema, object_)
        show(mc)

    def test_magic(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(SchemaError) as mc_:
            schema = magic({})  # type: ignore
        show(mc_)
        schema = magic("text/plain")
        with self.assertRaises(ValidationError) as mc:
            object_ = []
            validate(schema, object_)
        show(mc)
        object_ = "hello world"
        validate(schema, object_)
        object_ = "hello world".encode()
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            schema = magic("application/pdf")
            validate(schema, object_)
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            schema = magic("application/pdf", name="pdf_data")
            validate(schema, object_)
        show(mc)

    def test_dict(self) -> None:
        schema: object
        object_: object
        schema = {regex("[a-z]+"): "lc", regex("[A-Z]+"): "UC"}
        with self.assertRaises(ValidationError) as mc:
            object_ = []
            validate(schema, object_)
        show(mc)
        object_ = {"aa": "lc"}
        validate(schema, object_)
        object_ = {"aa": "lc", "bbb": "lc", "AA": "UC"}
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = {"aa": "LC"}
            validate(schema, object_)
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            object_ = {11: "lc"}
            validate(schema, object_)
        show(mc)
        schema = {11: 11, regex("[a-z]+"): "lc", regex("[A-Z]+"): "uc"}
        object_ = {11: 11}
        validate(schema, object_)
        object_ = {11: 11, 12: 12}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)
        validate(schema, object_, strict=False)
        schema = lax(schema)
        validate(schema, object_)
        schema = {"+": 11, regex("[a-z]+"): "lc", regex("[A-Z]+"): "uc"}
        object_ = {}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)
        schema = {"+?": 11, regex("[a-z]+"): "lc", regex("[A-Z]+"): "uc"}
        validate(schema, object_)
        schema = {optional_key(11): 11, regex("[a-z]+"): "lc", regex("[A-Z]+"): "uc"}
        validate(schema, object_)
        schema = {regex("[a-c]"): 4, regex("[b-d]"): 5}
        object_ = {"b": 4}
        validate(schema, object_)
        object_ = {"b": 5}
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = {"b": 6}
            validate(schema, object_)
        show(mc)
        schema = {"a": 1, regex("a"): 2}
        object_ = {"a": 1}
        validate(schema, object_)
        object_ = {"a": 2}
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = {"a": 3}
            validate(schema, object_)
        show(mc)

        class fake_string:
            def __init__(self, s: str) -> None:
                self.s = s

            def __str__(self) -> str:
                return self.s

        schema = {fake_string("a"): 1}
        object_ = {"a": 1}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)

        self.assertTrue("fake_string" in str(mc.exception))

        schema = {str: 1}
        object_ = {fake_string("a"): 1}

        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)

        self.assertTrue("fake_string" in str(mc.exception))

    def test_div(self) -> None:
        schema: object
        object_: object
        schema = div(2)
        object_ = 2
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = 3
            validate(schema, object_)
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            object_ = "3"
            validate(schema, object_)
        show(mc)
        with self.assertRaises(SchemaError) as mc_:
            schema = div({})  # type: ignore
        show(mc_)
        with self.assertRaises(ValidationError) as mc:
            schema = div(2, name="even")
            object_ = 3
            validate(schema, object_)
        show(mc)
        schema = div(2, 1)
        object_ = 3
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = 2
            validate(schema, object_)
        show(mc)
        with self.assertRaises(SchemaError) as mc_:
            schema = div(1, {})  # type: ignore
        show(mc_)
        with self.assertRaises(ValidationError) as mc:
            schema = div(2, 1, name="odd")
            object_ = 2
            validate(schema, object_)
        show(mc)

    def test_close_to(self) -> None:
        schema: object
        with self.assertRaises(SchemaError) as mc_:
            schema = close_to
            validate(schema, 1.0)
        show(mc_)
        with self.assertRaises(SchemaError) as mc_:
            schema = close_to({})  # type: ignore
        show(mc_)
        with self.assertRaises(SchemaError) as mc_:
            schema = close_to(1.0, abs_tol={})  # type: ignore
        show(mc_)
        with self.assertRaises(SchemaError) as mc_:
            schema = close_to(1.0, rel_tol={})  # type: ignore
        show(mc_)

        schema = close_to(1.0)
        validate(schema, 1.0)

        with self.assertRaises(ValidationError) as mc:
            validate(schema, 1.1)
        show(mc)

        schema = close_to(1.0, abs_tol=0.2)
        validate(schema, 1.1)

        with self.assertRaises(ValidationError) as mc:
            validate(schema, 1.3)
        show(mc)

    def test_at_most_one_of(self) -> None:
        schema: object
        object_: object
        schema = at_most_one_of("cat", "dog")
        object_ = {}
        validate(schema, object_)
        object_ = {"cat": None}
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = {"cat": None, "dog": None}
            validate(schema, object_)
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            object_ = 1
            validate(schema, object_)
        show(mc)

    def test_at_least_one_of(self) -> None:
        schema: object
        object_: object
        schema = at_least_one_of("cat", "dog")
        with self.assertRaises(ValidationError) as mc:
            object_ = {}
            validate(schema, object_)
        show(mc)
        object_ = {"cat": None}
        validate(schema, object_)
        object_ = {"cat": None, "dog": None}
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = 1
            validate(schema, object_)
        show(mc)

    def test_one_of(self) -> None:
        schema: object
        object_: object
        schema = one_of("cat", "dog")
        with self.assertRaises(ValidationError) as mc:
            object_ = {}
            validate(schema, object_)
        show(mc)
        object_ = {"cat": None}
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = {"cat": None, "dog": None}
            validate(schema, object_)
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            object_ = 1
            validate(schema, object_)
        show(mc)

    def test_keys(self) -> None:
        schema: object
        object_: object
        schema = keys("a", "b")
        object_ = {"a": 1, "b": 2}
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = {"a": 1}
            validate(schema, object_)
        show(mc)

    def test_ifthen(self) -> None:
        schema: object
        object_: object
        schema = ifthen(keys("a"), keys("b"))
        object_ = {"a": 1, "b": 1}
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            object_ = {"a": 1}
            validate(schema, object_)
        show(mc)
        object_ = {"c": 1}
        validate(schema, object_)
        with self.assertRaises(ValidationError) as mc:
            schema = ifthen(keys("a"), keys("b"), keys("d"))
            validate(schema, object_)
        show(mc)
        object_ = {"d": 1}
        validate(schema, object_)

    def test_filter(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(SchemaError) as mc_:
            schema = filter(1, 2)  # type: ignore
        show(mc_)
        with self.assertRaises(SchemaError) as mc_:
            schema = filter(1, 2, filter_name={})  # type: ignore
        show(mc_)
        schema = filter(json.loads, {"a": str})
        validate(schema, '{"a": "b"}')
        with self.assertRaises(ValidationError) as mc:
            validate(schema, '{"a": 1}')
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, {"a": 1})
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, "{'a': 1}")
        show(mc)
        schema = filter(json.loads, {"a": str}, filter_name="json.loads")
        validate(schema, '{"a": "b"}')
        with self.assertRaises(ValidationError) as mc:
            validate(schema, '{"a": 1}')
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, {"a": 1})
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, "{'a': 1}")
        show(mc)

        schema = intersect(str, filter(urlparse, fields({"scheme": "http"})))
        object_ = "http://example.org"
        validate(schema, object_, "url")
        with self.assertRaises(ValidationError) as mc:
            object_ = "https://example.org"
            validate(schema, object_, "url")
        show(mc)

    def test_const(self) -> None:
        schema: object
        schema = "a"
        validate(schema, "a")
        with self.assertRaises(ValidationError) as mc:
            validate(schema, "b")
        show(mc)
        schema = 1.0
        validate(schema, 1.0)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, 1.1)
        show(mc)

    def test_cond(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(SchemaError) as mc_:
            schema = cond("a", "b", "c")  # type: ignore
        show(mc_)

        schema = cond((0, 0), (1, 1))
        object_ = 1
        validate(schema, object_)

        schema = cond((0, 0), (1, 1))
        object_ = 0
        validate(schema, object_)

        schema = cond((0, 0), (1, 1))
        object_ = 2
        validate(schema, object_)

        schema = cond((0, 0), (1, 1), (object_, 1))
        object_ = 2
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)

    def test_fields(self) -> None:
        object_: object
        with self.assertRaises(SchemaError) as mc_:
            fields("dummy")
        show(mc_)
        with self.assertRaises(SchemaError) as mc_:
            fields({1: "a"})
        show(mc_)
        datetime_utc = intersect(datetime, fields({"tzinfo": timezone.utc}))
        object_ = datetime(2024, 4, 17)
        with self.assertRaises(ValidationError) as mc:
            validate(datetime_utc, object_)
        show(mc)
        object_ = datetime(2024, 4, 17, tzinfo=timezone.utc)
        validate(datetime_utc, object_)

    def test_strict(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(ValidationError) as mc:
            schema = {"a?": 1, "b": 2}
            object_ = {"b": 2, "c": 3}
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"a": 1, "c": 3}
            validate(schema, object_)
        show(mc)

        object_ = {"a": 1, "b": 2}
        validate(schema, object_)

        object_ = {"b": 2}
        validate(schema, object_)

    def test_missing_keys(self) -> None:
        schema: object
        object_: object
        schema = {"a?": 1, "b": 2}
        object_ = {"b": 2, "c": 3}
        validate(schema, object_, strict=False)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"a": 1, "c": 3}
            validate(schema, object_, strict=False)
        show(mc)

        object_ = {"a": 1, "b": 2}
        validate(schema, object_, strict=False)

        object_ = {"b": 2}
        validate(schema, object_, strict=False)

        schema = {"a?": 1, "b": 2}
        object_ = {"b": 2, "c": 3}
        validate(schema, object_, strict=False)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"a": 1, "c": 3}
            validate(schema, object_, strict=False)
        show(mc)

        object_ = {"a": 1, "b": 2}
        validate(schema, object_, strict=False)

        object_ = {"b": 2}
        validate(schema, object_, strict=False)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", "b"]
            object_ = ["a"]
            validate(schema, object_, strict=False)

        object_ = ["a", "b"]
        validate(schema, object_, strict=False)

        object_ = ["a", "b", "c"]
        validate(schema, object_, strict=False)

        with self.assertRaises(ValidationError) as mc:
            object_ = ["a", "b", "c"]
            validate(schema, object_, strict=True)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = {
                "s?": 1,
            }
            object_ = {
                "s": 2,
            }
            validate(schema, object_, strict=True)
        show(mc)

    def test_compile(self) -> None:
        schema: object
        object_: object
        schema = {"a?": 1}
        object_ = {"a": 1}
        validate(schema, object_)

        schema = compile(schema)
        validate(schema, object_)

    def test_union(self) -> None:
        schema: object
        object_: object
        schema = {"a?": 1, "b": union(2, 3)}
        object_ = {"b": 2, "c": 3}
        validate(schema, object_, strict=False)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"b": 4, "c": 3}
            validate(schema, object_)
        show(mc)

    def test_set_label(self) -> None:
        schema: object
        object_: object
        schema = {1: "a"}
        object_ = {1: "b"}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)
        schema = {1: set_label("a", "x")}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)
        validate(schema, object_, subs={"x": anything})
        with self.assertRaises(SchemaError) as mc_:
            schema = {1: set_label("a", {})}  # type: ignore
        show(mc_)
        with self.assertRaises(SchemaError) as mc_:
            schema = {1: set_label("a", "x", debug={})}  # type: ignore
        show(mc_)
        schema = {1: set_label("a", "x", debug=True)}
        validate(schema, object_, subs={"x": anything})
        schema = {1: set_label("a", "x", debug=True)}
        validate(schema, object_, subs={"x": anything})
        schema = {1: set_label("a", "x", "y", debug=True)}
        validate(schema, object_, subs={"x": anything})
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_, subs={"x": anything, "y": anything})
        show(mc)
        validate(schema, object_, subs={"x": "b"})

    def test_quote(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(ValidationError) as mc:
            schema = str
            object_ = str
            validate(schema, object_)
        show(mc)

        schema = quote(str)
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            schema = quote({1, 2})
            object_ = 1
            validate(schema, object_)
        show(mc)

        schema = quote({1, 2})
        object_ = {1, 2}
        validate(schema, object_)

        schema = quote(1.0 + 1e-14)
        with self.assertRaises(ValidationError) as mc:
            object_ = 1.0
            validate(schema, object_)
        show(mc)

        validate(schema, 1.0 + 1e-14)

        schema = 1.0
        validate(schema, 1.0 + 1e-14)

    def test_date_time(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(ValidationError) as mc:
            schema = date_time
            object_ = "2000-30-30"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = "2000-12-300"
            validate(schema, object_)
        show(mc)

        object_ = "2000-12-30"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            schema = date_time("%Y^%m^%d")
            object_ = "2000^12^300"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = "2000^12-30"
            validate(schema, object_)
        show(mc)

        object_ = "2000^12^30"
        validate(schema, object_)

    def test_date(self) -> None:
        schema: object
        object_: object
        schema = date
        object_ = "2023-10-10"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = "2023-10-10T01:01:01"
            validate(schema, object_)
        show(mc)

    def test_time(self) -> None:
        schema: object
        object_: object
        schema = time
        object_ = "01:01:01"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = "2023-10-10T01:01:01"
            validate(schema, object_)
        show(mc)

    def test_nothing(self) -> None:
        schema: object
        object_: object
        schema = nothing
        object_ = "dummy"
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)

    def test_anything(self) -> None:
        schema = anything
        validate(schema, "dummy")

    def test_set(self) -> None:
        schema: object
        object_: object
        schema = set()
        object_ = set()
        validate(schema, object_)
        object_ = {"a"}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)
        schema = {str}
        object_ = set()
        validate(schema, object_)
        object_ = {"a"}
        validate(schema, object_)
        object_ = {"a", "b"}
        validate(schema, object_)
        object_ = {1}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)
        object_ = {"a", 1}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)
        schema = {int, str}
        object_ = {1.0}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)
        object_ = {1}
        validate(schema, object_)
        object_ = {1, 2.0}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object_)
        show(mc)

    def test_intersect(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(ValidationError) as mc:
            schema = intersect(url, regex(r"^https", fullmatch=False))
            object_ = "ftp://example.com"
            validate(schema, object_)
        show(mc)

        object_ = "https://example.com"
        validate(schema, object_)

        def ordered_pair(o: Any) -> bool:
            ret: bool = o[0] <= o[1]
            return ret

        with self.assertRaises(ValidationError) as mc:
            schema = intersect((int, int), ordered_pair)
            object_ = (3, 2)
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = (1, 3, 2)
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = ("a", "b")
            validate(schema, object_)
        show(mc)

        object_ = (1, 2)
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            schema = intersect(
                (int, int), set_name(lambda o: o[0] <= o[1], "ordered_pair")
            )
            object_ = (3, 2)
            validate(schema, object_)
        show(mc)

    def test_complement(self) -> None:
        schema: object
        object_: object
        schema = intersect(url, complement(regex(r"^https", fullmatch=False)))
        object_ = "ftp://example.com"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = "https://example.com"
            validate(schema, object_)
        show(mc)

    def test_set_name(self) -> None:
        schema: object
        schema = set_name("a", "dummy")
        c: Any = compile(schema)
        self.assertTrue(c.__name__ == "dummy")

        with self.assertRaises(ValidationError) as mc:
            validate(schema, "b")
        show(mc)
        self.assertTrue("dummy" in str(mc.exception))

        validate(schema, "a")

        with self.assertRaises(SchemaError) as mc_:
            schema = set_name("a", {})  # type: ignore
        show(mc_)

        schema = set_name(datetime, "dummy", reason=True)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, "12-34-56")
        show(mc)
        self.assertTrue("datetime" in str(mc.exception))
        self.assertTrue("dummy" in str(mc.exception))

    def test_lax(self) -> None:
        schema: object
        object_: object
        schema = lax(["a", "b", "c"])
        object_ = ["a", "b", "c", "d"]
        validate(schema, object_)

    def test_strict_wrapper(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(ValidationError) as mc:
            schema = strict(["a", "b", "c"])
            object_ = ["a", "b", "c", "d"]
            validate(schema, object_, strict=False)
        show(mc)

    def test_make_type(self) -> None:
        schema: object
        object_: object
        global url
        schema = {"a": 1}
        t = make_type(schema, "example", debug=True)
        self.assertTrue(t.__name__ == "example")
        self.assertFalse(isinstance({"a": 2}, t))
        self.assertTrue(isinstance({"a": 1}, t))
        self.assertFalse(isinstance({"a": 1, "b": 1}, t))

        t = make_type(schema, "example", strict=False, debug=True)
        self.assertTrue(t.__name__ == "example")
        self.assertTrue(isinstance({"a": 1, "b": 1}, t))

        url_ = make_type(url, debug=True)
        self.assertTrue(url_.__name__ == "url")
        self.assertFalse(isinstance("google.com", url_))
        self.assertTrue(isinstance("https://google.com", url_))

        country_code = make_type(regex("[A-ZA-Z]", "country_code"), debug=True)
        self.assertTrue(country_code.__name__ == "country_code")
        self.assertFalse(isinstance("BEL", country_code))

        t = make_type({}, debug=True)
        self.assertTrue(t.__name__ == "schema")

        t = make_type({1: set_label("a", "x")}, debug=True)
        object_ = {1: "b"}
        self.assertFalse(isinstance(object_, t))
        t = make_type(
            {1: set_label("a", "x", debug=True)}, debug=True, subs={"x": anything}
        )
        self.assertTrue(isinstance(object_, t))

    def test_generics(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(ValidationError) as mc:
            schema = [str, ...]
            object_ = ("a", "b")
            validate(schema, object_)
        show(mc)

        object_ = ["a", "b"]
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = ["a", 10]
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = ["a", ["b", "c"]]
            validate(schema, object_)
        show(mc)

        schema = [...]
        object_ = ["a", "b", 1, 2]
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", ...]
            object_ = ["a", "b"]
            validate(schema, object_)
        show(mc)

        object_ = []
        validate(schema, object_)

        object_ = ["a", "a"]
        validate(schema, object_)

        object_ = ["a", "a", "a", "a", "a"]
        validate(schema, object_)

        schema = ["a", "b", ...]
        object_ = ["a", "b"]
        validate(schema, object_)

        schema = ["a", "b", "c", ...]
        object_ = ["a", "b"]
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", "b", "c", "d", ...]
            object_ = ["a", "b"]
            validate(schema, object_)
        show(mc)

        schema = [(str, int), ...]
        object_ = [("a", 1), ("b", 2)]
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            schema = [(str, int), ...]
            object_ = [("a", 1), ("b", "c")]
            validate(schema, object_)

        schema = [email, ...]
        object_ = ["user1@example.com", "user2@example.com"]
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            schema = [email, ...]
            object_ = ["user1@example.com", "user00@user00.user00"]
            validate(schema, object_)
        show(mc)

    def test_sequence(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(ValidationError) as mc:
            schema = {"a": 1}
            object_ = []
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = []
            object_ = (1, 2)
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", "b", None, "c"]
            object_ = ["a", "b"]
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", "b"]
            object_ = ["a", "b", None, "c"]
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", int, ...]
            object_ = ["a", "c", 1]
            validate(schema, object_)
        show(mc)

    @unittest.skipUnless(
        vtjson.supports_Generic_ABC,
        "Generic base classes were introduced in Pythin 3.9",
    )
    def test_Sequence(self) -> None:

        T = TypeVar("T")

        class dummy(Sequence[T]):
            L: Sequence[T]

            def __init__(self, L: Sequence[T] = ()) -> None:
                self.L = L

            @overload
            def __getitem__(self, index: int) -> T: ...

            @overload
            def __getitem__(self, index: slice) -> dummy[T]: ...

            def __getitem__(self, index: int | slice) -> T | dummy[T]:
                if isinstance(index, int):
                    return self.L[index]
                return dummy(self.L[index])

            def __len__(self) -> int:
                return len(self.L)

        class dummy_ex(dummy[T]):
            pass

        schema: object
        object_: object

        object_ = dummy((1, 2))
        schema = dummy((1, 2))
        validate(schema, object_)

        schema = dummy([1, 2])
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = [1, 2]
            validate(schema, object_)
        show(mc)

        validate(schema, dummy_ex([1, 2]))

        with self.assertRaises(ValidationError) as mc:
            object_ = dummy(["a", "b"])
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = dummy(["a", "b", None, "c"])
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = dummy(["a", int, ...])
            object_ = dummy(["a", "c", 1])
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = dummy_ex((1, 2))
            object_ = dummy((1, 2))
            validate(schema, object_)
        show(mc)
        self.assertTrue("dummy_ex" in str(mc.exception))

        schema = dummy[str]
        object_ = dummy(("a", "b"))
        validate(schema, object_)

        object_ = dummy_ex(("a", "b"))
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = dummy((1, 2))
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = dummy_ex[str]
            object_ = dummy(("a", "b"))
            validate(schema, object_)
        show(mc)
        self.assertTrue("dummy_ex" in str(mc.exception))

    @unittest.skipUnless(
        vtjson.supports_Generic_ABC,
        "Generic base classes were introduced in Pythin 3.9",
    )
    def test_Mapping(self) -> None:

        S = TypeVar("S")
        T = TypeVar("T")

        class dummy(Mapping[S, T]):
            L: Mapping[S, T]

            def __init__(self, L: Mapping[S, T] = {}) -> None:
                self.L = L

            def __getitem__(self, key: S) -> T:
                return self.L[key]

            def __iter__(self) -> Generator[S]:
                for key in self.L:
                    yield key

            def __len__(self) -> int:
                return len(self.L)

        class dummy_ex(dummy[S, T]):
            pass

        schema: object
        object_: object

        schema = dummy({1: 2})
        object_ = dummy({1: 2})
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = [1, 2]
            validate(schema, object_)
        show(mc)

        validate(schema, dummy_ex({1: 2}))

        with self.assertRaises(ValidationError) as mc:
            object_ = dummy(["a", "b"])  # type: ignore
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = dummy({1: "b"})
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = dummy({"a": int})
            object_ = dummy({"a": "c"})
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = dummy_ex({1: 2})
            object_ = dummy({1: 2})
            validate(schema, object_)
        show(mc)
        self.assertTrue("dummy_ex" in str(mc.exception))

        schema = dummy[str, str]
        object_ = dummy({"a": "b"})
        validate(schema, object_)

        object_ = dummy_ex({"a": "b"})
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = dummy({1: 2})
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = dummy_ex[str, str]
            object_ = dummy({"a": "b"})
            validate(schema, object_)
        show(mc)
        self.assertTrue("dummy_ex" in str(mc.exception))

    def test_validate(self) -> None:
        schema: object
        object_: object

        class lower_case_string:
            @staticmethod
            def __validate__(
                object_: object, name: str, strict: bool, subs: Dict[str, object]
            ) -> str:
                if not isinstance(object_, str):
                    return f"{name} (value:{object_}) is not of type str"
                for c in object_:
                    if not ("a" <= c <= "z"):
                        return (
                            f"{c}, contained in the string {name} "
                            + f"(value: {repr(object_)}) is not a lower case letter"
                        )
                return ""

        with self.assertRaises(ValidationError) as mc:
            schema = lower_case_string
            object_ = 1
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = "aA"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = "aA"
            validate(schema, object_)
        show(mc)

        object_ = "ab"
        validate(schema, object_)

        schema = {"a": lower_case_string}
        object_ = {"a": "ab"}
        validate(schema, object_)

        class lower_case_string_ex(compiled_schema):
            def __validate__(
                self,
                object_: object,
                name: str,
                strict: bool,
                subs: Mapping[str, object],
            ) -> str:
                if not isinstance(object_, str):
                    return f"{name} (value:{object_}) is not of type str"
                for c in object_:
                    if not ("a" <= c <= "z"):
                        return (
                            f"{c}, contained in the string {name} "
                            + f"(value: {repr(object_)}) is not a lower case letter"
                        )
                return ""

        schema = {"a": lower_case_string_ex}
        object_ = {"a": "ab"}
        validate(schema, object_)

    def test_regex(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(SchemaError) as cm_:
            regex({})  # type: ignore
        show(cm_)

        with self.assertRaises(SchemaError) as cm_:
            regex({}, name="test")  # type: ignore
        show(cm_)

        with self.assertRaises(SchemaError) as cm_:
            regex("a", name={})  # type: ignore
        show(cm_)

        with self.assertRaises(SchemaError) as cm_:
            schema = regex
            object_ = "a"
            validate(schema, object_)
        show(cm_)

        ip_address = regex(r"(?:[\d]+\.){3}(?:[\d]+)", name="ip_address")
        with self.assertRaises(ValidationError) as mc:
            object_ = 123
            validate(ip_address, object_)
        show(mc)

        schema = {"ip": ip_address}
        object_ = {"ip": "123.123.123.123"}
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"ip": "123.123.123"}
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"ip": "123.123.123.abc"}
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"ip": "123.123..123"}
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"ip": "123.123.123.123.123"}
            validate(schema, object_)
        show(mc)

        object_ = {"ip": "123.123.123.1000000"}
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"ip": ""}
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = regex(".")
            object_ = "\n"
            validate(schema, object_)
        show(mc)

        schema = regex(".", flags=re.DOTALL)
        object_ = "\n"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            schema = regex(".", flags=re.ASCII | re.MULTILINE)
            object_ = "\n"
            validate(schema, object_)
        show(mc)

    def test_size(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(SchemaError) as mc_:
            schema = size("a", "b")  # type: ignore
            object_ = "a"
            validate(schema, object_)
        show(mc_)

        with self.assertRaises(SchemaError) as mc_:
            schema = size(-1, 0)
            object_ = "a"
            validate(schema, object_)
        show(mc_)

        with self.assertRaises(SchemaError) as mc_:
            schema = size(1, 0)
            object_ = "a"
            validate(schema, object_)
        show(mc_)

        with self.assertRaises(SchemaError) as mc_:
            schema = size(..., 1)  # type: ignore
            object_ = "a"
            validate(schema, object_)
        show(mc_)

        with self.assertRaises(SchemaError) as mc_:
            schema = size(1, "10")  # type: ignore
            object_ = "a"
            validate(schema, object_)
        show(mc_)

        schema = size(1, 2)
        object_ = "a"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = -1
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = []
            validate(schema, object_)
        show(mc)

        object_ = [1]
        validate(schema, object_)

        object_ = [1, 2]
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = [1, 2, 3]
            validate(schema, object_)
        show(mc)

        schema = size(1)
        object_ = "a"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = "aa"
            validate(schema, object_)
        show(mc)

        schema = size(10, ...)
        object_ = 10 * "a"
        validate(schema, object_)

        object_ = 11 * "a"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = 9 * "a"
            validate(schema, object_)
        show(mc)

    def test_gt(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(SchemaError) as mc_:
            schema = gt
            object_ = "a"
            validate(schema, object_)
        show(mc_)

        with self.assertRaises(ValidationError) as mc:
            schema = gt(1)
            object_ = "a"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = gt(1)
            object_ = 1
            validate(schema, object_)
        show(mc)

        schema = gt(1)
        object_ = 2

    def test_ge(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(SchemaError) as mc_:
            schema = ge
            object_ = "a"
            validate(schema, object_)
        show(mc_)

        with self.assertRaises(ValidationError) as mc:
            schema = ge(1)
            object_ = "a"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = ge(1)
            object_ = 0
            validate(schema, object_)
        show(mc)

        schema = ge(1)
        object_ = 1

    def test_lt(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(SchemaError) as mc_:
            schema = lt
            object_ = "a"
            validate(schema, object_)
        show(mc_)

        with self.assertRaises(ValidationError) as mc:
            schema = lt(1)
            object_ = "a"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = lt(1)
            object_ = 1
            validate(schema, object_)
        show(mc)

        schema = lt(1)
        object_ = 0

    def test_le(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(SchemaError) as mc_:
            schema = le
            object_ = "a"
            validate(schema, object_)
        show(mc_)

        with self.assertRaises(ValidationError) as mc:
            schema = le(1)
            object_ = "a"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = le(1)
            object_ = 2
            validate(schema, object_)
        show(mc)

        schema = le(1)
        object_ = 1

    def test_interval(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(SchemaError) as mc_:
            schema = interval
            object_ = "a"
            validate(schema, object_)
        show(mc_)

        with self.assertRaises(ValidationError) as mc:
            schema = interval(1, 10)
            object_ = "a"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = interval(1, 9)
            object_ = "a"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = -1
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = 10
            validate(schema, object_)
        show(mc)

        object_ = 5
        validate(schema, object_)

        schema = interval(1, 9, strict_lb=True, strict_ub=True)
        with self.assertRaises(ValidationError) as mc:
            object_ = 1
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = 9
            validate(schema, object_)
        show(mc)

        object_ = 5
        validate(schema, object_)

        schema = interval(0, ...)
        object_ = 5
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = -1
            validate(schema, object_)
        show(mc)

        schema = interval(..., 0)
        object_ = -5
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = 1
            validate(schema, object_)
        show(mc)

        schema = interval(..., ...)
        object_ = "0"
        validate(schema, object_)

        with self.assertRaises(SchemaError) as cm_:
            interval(0, "z")
        show(cm_)

        with self.assertRaises(SchemaError) as cm_:
            interval(..., {})  # type: ignore
        show(cm_)

        with self.assertRaises(SchemaError) as cm_:
            interval({}, ...)  # type: ignore
        show(cm_)

    def test_email(self) -> None:
        schema: object
        object_: object
        schema = email
        object_ = "user00@user00.com"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = "user00@user00.user00"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = 1
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = "@user00.user00"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = email(check_deliverability=True)
            object_ = "user@example.com"
            validate(schema, object_)
        show(mc)

        object_ = "user@google.com"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = "user@ffdfsdfsdfsasddasdadasad.com"
            validate(schema, object_)
        show(mc)

    def test_ip_address(self) -> None:
        schema: object
        object_: object

        with self.assertRaises(SchemaError) as cm_:
            schema = ip_address(version=5)  # type: ignore
        show(cm_)

        with self.assertRaises(ValidationError) as cm:
            schema = ip_address(version=4)
            object_ = "2001:db8:3333:4444:5555:6666:7777:8888"
            validate(schema, object_)
        show(cm)
        object_ = "123.123.123.123"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as cm:
            schema = ip_address(version=4)
            object_ = {}
            validate(schema, object_)
        show(cm)

        with self.assertRaises(ValidationError) as cm:
            schema = ip_address(version=6)
            object_ = "123.123.123.123"
            validate(schema, object_)
        show(cm)
        object_ = "2001:db8:3333:4444:5555:6666:7777:8888"
        validate(schema, object_)

        schema = {"ip": ip_address}
        object_ = {"ip": "123.123.123.123"}
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"ip": "123.123.123"}
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"ip": "123.123.123.256"}
            validate(schema, object_)
        show(mc)

        object_ = {"ip": "2001:db8:3333:4444:5555:6666:7777:8888"}
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"ip": "2001:db8:3333:4444:5555:6666:7777:"}
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"ip": {}}
            validate(schema, object_)
        show(mc)

    def test_url(self) -> None:
        schema: object
        object_: object
        schema = {"url": url}
        object_ = {"url": "https://google.com"}
        validate(schema, object_)

        object_ = {"url": "https://google.com?search=chatgpt"}
        validate(schema, object_)

        object_ = {"url": "https://user:pass@google.com?search=chatgpt"}
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"url": "google.com"}
            validate(schema, object_)
        show(mc)

    def test_domain_name(self) -> None:
        schema: object
        object_: object
        schema = domain_name
        object_ = "www.example.com"
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = "www.éxample.com"
            validate(schema, object_)
        show(mc)

        schema = domain_name(ascii_only=False)
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = "-www.éxample.com"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object_ = "www.é_xample.com"
            validate(schema, object_)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = domain_name(resolve=True)
            object_ = "www.exaaaaaaaaaaaaaaaaaaaaaaaaample.com"
            validate(schema, object_)
        show(mc)

        object_ = "www.example.com"
        validate(schema, object_)

    def test_number(self) -> None:
        schema: object
        object_: object
        with self.assertWarns(DeprecationWarning):
            schema = {"number": number}
            compile(schema)

        object_ = {"number": 1}
        validate(schema, object_)

        object_ = {"number": 1.0}
        validate(schema, object_)

        with self.assertRaises(ValidationError) as mc:
            object_ = {"number": "a"}
            validate(schema, object_)
        show(mc)

    def test_truncation(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(ValidationError) as mc:
            schema = "a"
            object_ = 1000 * "abc"
            validate(schema, object_)
        show(mc)

        valid = str(mc.exception)

        self.assertTrue(r"...'" in valid)
        self.assertTrue("TRUNCATED" in valid)
        self.assertTrue(r"value:'" in valid)

        with self.assertRaises(ValidationError) as mc:
            object_ = 50 * "a"
            validate(schema, object_)
        show(mc)

        valid = str(mc.exception)

        self.assertTrue(r"value:'" in valid)
        self.assertFalse("TRUNCATED" in valid)

        with self.assertRaises(ValidationError) as mc:
            object_ = 1000 * ["abcdefgh"]
            validate(schema, object_)
        show(mc)

        valid = str(mc.exception)

        self.assertTrue(r"value:[" in valid)
        self.assertTrue(r"...]" in valid)
        self.assertTrue("TRUNCATED" in valid)

        with self.assertRaises(ValidationError) as mc:
            object__: Dict[int, int] = {}
            for i in range(1000):
                object__[i] = 7 * i
            validate(schema, object__)
        show(mc)

        valid = str(mc.exception)

        self.assertTrue(r"value:{" in valid)
        self.assertTrue("...}" in valid)
        self.assertTrue("TRUNCATED" in valid)

    def test_int_float_complex(self) -> None:
        schema: object
        schema = int
        validate(schema, 1)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, 1.0)
        show(mc)
        schema = float
        validate(schema, 1)
        validate(schema, 1.0)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, 1.0 + 1.0j)
        show(mc)
        schema = complex
        validate(schema, 1)
        validate(schema, 1.0)
        validate(schema, 1.0 + 1.0j)

    def test_float_equal(self) -> None:
        schema: object
        object_: object
        with self.assertRaises(ValidationError) as mc:
            schema = 2.94
            object_ = 2.95
            validate(schema, object_)
        show(mc)

        object_ = 2.94 + 1e-10
        validate(schema, object_)

    def test_callable(self) -> None:
        schema: object
        object_: object

        def even(x: int) -> bool:
            return x % 2 == 0

        with self.assertRaises(ValidationError) as mc:
            schema = even
            object_ = 1
            validate(schema, object_)
        show(mc)

        object_ = 2
        validate(schema, object_)

        def fails(x: float) -> bool:
            return 1 / x == 0

        with self.assertRaises(ValidationError) as mc:
            schema = fails
            object_ = 0
            validate(schema, object_)
        show(mc)

    @unittest.skipUnless(
        vtjson.supports_Literal,
        "Literal was introduced in Python 3.8",
    )
    def test_Literal(self) -> None:
        schema = Literal["a", "b"]
        validate(schema, "a")
        with self.assertRaises(ValidationError) as mc:
            validate(schema, "c")
        show(mc)

    @unittest.skipUnless(
        vtjson.supports_Generics,
        "Generics did not work well in Pythin 3.7",
    )
    def test_List(self) -> None:
        schema = List[str]
        validate(schema, ["a", "b"])
        with self.assertRaises(ValidationError) as mc:
            validate(schema, [1])
        show(mc)

    @unittest.skipUnless(
        vtjson.supports_Generics,
        "Generics did not work well in Pythin 3.7",
    )
    def test_Dict(self) -> None:
        schema = Dict[str, str]
        validate(schema, {"a": "b"})
        with self.assertRaises(ValidationError) as mc:
            validate(schema, {"a": 1})
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, {1: "a"})
        show(mc)

    @unittest.skipUnless(
        vtjson.supports_Generics,
        "Generics did not work well in Pythin 3.7",
    )
    def test_Tuple(self) -> None:
        schema: object
        schema = Tuple[str, ...]
        validate(schema, ("a", "b"))
        with self.assertRaises(ValidationError) as mc:
            validate(schema, ["a", "b"])
        show(mc)

        schema = Tuple[str, int]
        validate(schema, ("a", 1))
        with self.assertRaises(ValidationError) as mc:
            validate(schema, ("a", "b"))
        show(mc)

    @unittest.skipUnless(
        sys.version_info >= (3, 9),
        "Parametrized types were introduced in Python 3.9",
    )
    def test_generic_list(self) -> None:
        schema = list[str]
        validate(schema, ["a", "b"])
        with self.assertRaises(ValidationError) as mc:
            validate(schema, [1])
        show(mc)

    @unittest.skipUnless(
        sys.version_info >= (3, 9),
        "Parametrized types were introduced in Python 3.9",
    )
    def test_generic_tuple(self) -> None:
        schema: object
        schema = tuple[str, ...]
        validate(schema, ("a", "b"))
        with self.assertRaises(ValidationError) as mc:
            validate(schema, ["a", "b"])
        show(mc)

        schema = tuple[str, int]
        validate(schema, ("a", 1))
        with self.assertRaises(ValidationError) as mc:
            validate(schema, ("a", "b"))
        show(mc)

    @unittest.skipUnless(
        sys.version_info >= (3, 9),
        "Parametrized types were introduced in Python 3.9",
    )
    def test_generic_dict(self) -> None:
        schema = dict[str, str]
        validate(schema, {"a": "b"})
        with self.assertRaises(ValidationError) as mc:
            validate(schema, {"a": 1})
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, {1: "a"})
        show(mc)

    @unittest.skipUnless(
        vtjson.supports_Annotated,
        "Annotated was introduced in Python 3.9",
    )
    def test_Annotated(self) -> None:
        schema = Annotated[str, "a"]
        validate(schema, "a")
        with self.assertRaises(ValidationError) as mc:
            validate(schema, "c")
        show(mc)

    def test_Apply(self) -> None:
        a = Apply()
        with self.assertRaises(SchemaError) as mc_:
            a(())
        show(mc_)
        b = a((int,))
        self.assertTrue(b == int)
        b = a((int, str))
        self.assertTrue(isinstance(b, intersect))

        a = Apply(skip_first=True)
        with self.assertRaises(SchemaError) as mc_:
            a((int,))
        show(mc_)
        b = a((int, str))
        self.assertTrue(b == str)
        b = a((int, str, int))
        self.assertTrue(isinstance(b, intersect))

        a = Apply(name="dummy")
        b = a((int,))
        self.assertTrue(isinstance(b, set_name))

        a = Apply(labels=["dummy1", "dummy2"])
        b = a((int,))
        self.assertTrue(isinstance(b, set_label))

    @unittest.skipUnless(
        vtjson.supports_Annotated,
        "Annotated was introduced in Python 3.9",
    )
    def test_Annotated_Apply(self) -> None:
        schema: object
        skip_first = Apply(skip_first=True)
        with self.assertRaises(SchemaError) as mc_:
            schema = Annotated[int, skip_first, str]
            compile(schema)
        show(mc_)
        schema = Annotated[int, str, skip_first]
        with self.assertRaises(ValidationError) as mc:
            validate(schema, 1)
        show(mc)
        validate(schema, "a")
        with self.assertRaises(SchemaError) as mc_:
            schema = Annotated[int, str, skip_first, skip_first]
            compile(schema)
        show(mc_)
        schema = Annotated[int, str, skip_first, int, skip_first]
        with self.assertRaises(ValidationError) as mc:
            validate(schema, "a")
        show(mc)
        validate(schema, 1)

    @unittest.skipUnless(
        vtjson.supports_Generics,
        "Generics did not work well in Python 3.7",
    )
    def test_Union(self) -> None:
        schema = Union[int, str]
        validate(schema, "a")
        validate(schema, 1)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, 0.1)
        show(mc)

    @unittest.skipUnless(
        vtjson.supports_UnionType,
        "UnionTypes were introduced in Python 3.10",
    )
    def test_UnionType(self) -> None:
        schema = int | str
        validate(schema, "a")
        validate(schema, 1)
        with self.assertRaises(ValidationError) as mc:
            validate(schema, 0.1)
        show(mc)

    @unittest.skipUnless(
        vtjson.supports_TypedDict,
        "TypedDict was introduced in Python 3.8",
    )
    def test_TypedDict(self) -> None:
        class dummy(TypedDict):
            a: int
            b: str

        schema = dummy
        validate(schema, {"a": 1, "b": "c"})
        with self.assertRaises(ValidationError) as mc:
            validate(schema, {"a": "b", "b": "c"})
        show(mc)
        self.assertTrue("dummy" in str(mc.exception))
        with self.assertRaises(ValidationError) as mc:
            validate(schema, {"a": 1, "b": 1})
        show(mc)
        self.assertTrue("dummy" in str(mc.exception))

        class dummy2(TypedDict, total=False):
            a: int
            b: str

        schema2 = dummy2
        validate(schema2, {})
        validate(schema2, {"a": 1})
        with self.assertRaises(ValidationError) as mc:
            validate(schema2, {"a": "b", "b": "c"})
        show(mc)
        self.assertTrue("dummy2" in str(mc.exception))
        with self.assertRaises(ValidationError) as mc:
            validate(schema2, {"a": 1, "b": 1})
        show(mc)
        self.assertTrue("dummy2" in str(mc.exception))

    @unittest.skipUnless(
        vtjson.supports_NotRequired,
        "NotRequired was introduced in Python 3.11",
    )
    def test_NotRequired(self) -> None:
        class dummy(TypedDict):
            a: int
            b: NotRequired[str]

        schema = dummy
        validate(schema, {"a": 1})
        with self.assertRaises(ValidationError) as mc:
            validate(schema, {"a": "b"})
        show(mc)
        validate(schema, {"a": 1, "b": "c"})
        with self.assertRaises(ValidationError) as mc:
            validate(schema, {"a": 1, "b": 1})
        show(mc)

        class dummy2(TypedDict, total=False):
            a: Required[int]
            b: str

        schema2 = dummy2
        validate(schema2, {"a": 1})
        with self.assertRaises(ValidationError) as mc:
            validate(schema2, {"a": "b"})
        show(mc)
        validate(schema2, {"a": 1, "b": "c"})
        with self.assertRaises(ValidationError) as mc:
            validate(schema2, {"a": 1, "b": 1})
        show(mc)

    def test_Any(self) -> None:
        schema = Any
        validate(schema, "dummy")

    def test_NewType(self) -> None:
        dummy = NewType("dummy", int)
        validate(dummy, 1)
        with self.assertRaises(ValidationError) as mc:
            validate(dummy, "a")
        show(mc)
        self.assertTrue("dummy" in str(mc.exception))

    @unittest.skipUnless(
        vtjson.supports_Generics,
        "Generics did not work well in Python 3.7",
    )
    def test_safe_cast(self) -> None:
        with self.assertRaises(ValidationError) as mc:
            safe_cast(List[int], ["a", "b"])
        show(mc)
        a: object = [1, 2]
        if has_assert_type:
            assert_type(a, object)
        b = safe_cast(List[int], a)
        if has_assert_type:
            assert_type(b, List[int])
        with self.assertRaises(ValidationError) as mc:
            safe_cast(List[str], a)
        show(mc)

    def test_Protocol(self) -> None:
        class dummy(Protocol):
            b: int = 0
            c: str = ""

            def f(self, i: float) -> bool:
                return i == i

        class x:
            b: str = ""
            c: str = ""

        if not vtjson.supports_structural:
            with self.assertRaises(SchemaError) as mc_:
                compile(dummy)
            show(mc_)
            return

        with self.assertRaises(ValidationError) as mc:
            validate(dummy, x())
        show(mc)
        self.assertTrue("dummy" in str(mc.exception))

        class w:
            b: int = 1
            c: str = ""

            def g(self) -> bool:
                return True

        validate(dummy, w())

    def test_NamedTuple(self) -> None:
        class dummy(NamedTuple):
            b: int = 0
            c: str = ""

            def f(self, i: float) -> bool:
                return i == i

        class x(NamedTuple):
            b: str = ""
            c: str = ""

        if not vtjson.supports_structural:
            with self.assertRaises(SchemaError) as mc_:
                compile(dummy)
            show(mc_)
            return

        with self.assertRaises(ValidationError) as mc:
            validate(dummy, x())
        show(mc)
        self.assertTrue("dummy" in str(mc.exception))

        class w(NamedTuple):
            b: int = 1
            c: str = ""

            def g(self) -> bool:
                return True

        validate(dummy, w())

    def test_protocol(self) -> None:
        class dummy:
            b: int = 0
            c: str = ""

            def f(self, i: float) -> bool:
                return i == i

        if not vtjson.supports_structural:
            with self.assertRaises(SchemaError) as mc_:
                schema = protocol(dummy)
            show(mc_)
            return

        with self.assertRaises(SchemaError) as mc_:
            schema = protocol(dummy, dict=None)  # type: ignore
        show(mc_)

        with self.assertRaises(SchemaError) as mc_:
            schema = protocol({})
        show(mc_)

        schema = protocol(dummy)

        class x:
            b: str = ""
            c: str = ""

        with self.assertRaises(ValidationError) as mc:
            validate(schema, x())
        show(mc)
        self.assertTrue("dummy" in str(mc.exception))

        class w:
            b: int = 1
            c: str = ""

            def g(self) -> bool:
                return True

        validate(schema, w())

        schema = protocol(dummy, dict=True)
        validate(schema, {"b": 1, "c": ""})

        with self.assertRaises(ValidationError):
            validate(schema, w())
        show(mc)

        if sys.version_info >= (3, 11):

            class dummy2:
                # oh, horror
                a: {"b": int}  # type: ignore # noqa: F821

            class u:
                def __init__(self, v: object) -> None:
                    self.a = {"b": v}

            validate(protocol(dummy2), u(5))

            with self.assertRaises(ValidationError) as mc:
                validate(protocol(dummy2), u(""))
            show(mc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
