import json
import re
import sys
import unittest
from datetime import datetime, timezone
from urllib.parse import urlparse

from vtjson import (
    SchemaError,
    ValidationError,
    anything,
    at_least_one_of,
    at_most_one_of,
    compile,
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
    quote,
    regex,
    set_label,
    set_name,
    size,
    strict,
    time,
    union,
    url,
    validate,
)


def show(mc):
    exception = mc.exception
    print(f"{exception.__class__.__name__}: {str(mc.exception)}")


class TestValidation(unittest.TestCase):
    def test_recursion(self):
        a = {}
        a["a?"] = a
        object = {"a": {}}
        validate(a, object)
        object = {"a": {"a": {}}}
        validate(a, object)
        object = {"a": {"a": {"a": {}}}}
        validate(a, object)
        with self.assertRaises(ValidationError) as mc:
            object = {"a": {"a": {"b": {}}}}
            validate(a, object)
        show(mc)

        person = {}
        person["mother"] = union(person, "unknown")
        person["father"] = union(person, "unknown")
        person["name"] = str
        object = {
            "name": "John",
            "father": {"name": "Carlo", "father": "unknown", "mother": "unknown"},
            "mother": {"name": "Iris", "father": "unknown", "mother": "unknown"},
        }
        validate(person, object)
        with self.assertRaises(ValidationError) as mc:
            object = {
                "name": "John",
                "father": {"name": "Carlo", "father": "unknown", "mother": "unknown"},
                "mother": {"name": "Iris", "father": "unknown", "mother": "Sarah"},
            }
            validate(person, object)
        show(mc)

        a = {}
        a["a?"] = intersect(a)
        object = {"a": {}}
        validate(a, object)
        object = {"a": {"a": {}}}
        validate(a, object)
        object = {"a": {"a": {"a": {}}}}
        validate(a, object)
        with self.assertRaises(ValidationError) as mc:
            object = {"a": {"a": {"b": {}}}}
            validate(a, object)
        show(mc)

        a = {}
        b = {}
        a["a?"] = union(b, a)
        object = {"a": {}}
        validate(a, object)
        object = {"a": {"a": {}}}
        validate(a, object)
        object = {"a": {"a": {"a": {}}}}
        validate(a, object)
        with self.assertRaises(ValidationError) as mc:
            object = {"a": {"a": {"b": {}}}}
            validate(a, object)
        show(mc)

        a = {}
        b = {}
        a["b"] = union(b, None)
        b["a"] = union(a, None)
        object = {"b": {"a": {"b": None}}}
        validate(a, object)
        with self.assertRaises(ValidationError) as mc:
            validate(b, object)
        show(mc)

    def test_immutable(self):
        L = ["a"]
        schema = compile(L)
        object = ["a"]
        validate(schema, object)
        L[0] = "b"
        validate(schema, object)
        L = {"a": 1}
        schema = compile(L)
        object = {"a": 1}
        validate(schema, object)
        L["b"] = 2
        validate(schema, object)

    def test_glob(self):
        schema = glob("*.txt")
        object = "hello.txt"
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            object = "hello.doc"
            validate(schema, object)
        show(mc)
        with self.assertRaises(SchemaError) as mc:
            schema = glob({})
        show(mc)
        with self.assertRaises(SchemaError) as mc:
            schema = glob({}, name="Invalid")
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            schema = glob("*.txt", name="text_file")
            object = "hello.doc"
            validate(schema, object)
        show(mc)

    def test_magic(self):
        with self.assertRaises(SchemaError) as mc:
            schema = magic({})
        show(mc)
        schema = magic("text/plain")
        with self.assertRaises(ValidationError) as mc:
            object = []
            validate(schema, object)
        show(mc)
        object = "hello world"
        validate(schema, object)
        object = "hello world".encode()
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            schema = magic("application/pdf")
            validate(schema, object)
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            schema = magic("application/pdf", name="pdf_data")
            validate(schema, object)
        show(mc)

    def test_dict(self):
        schema = {regex("[a-z]+"): "lc", regex("[A-Z]+"): "UC"}
        with self.assertRaises(ValidationError) as mc:
            object = []
            validate(schema, object)
        show(mc)
        object = {"aa": "lc"}
        validate(schema, object)
        object = {"aa": "lc", "bbb": "lc", "AA": "UC"}
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            object = {"aa": "LC"}
            validate(schema, object)
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            object = {11: "lc"}
            validate(schema, object)
        show(mc)
        schema = {11: 11, regex("[a-z]+"): "lc", regex("[A-Z]+"): "uc"}
        object = {11: 11}
        validate(schema, object)
        object = {11: 11, 12: 12}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object)
        show(mc)
        validate(schema, object, strict=False)
        schema = lax(schema)
        validate(schema, object)
        schema = {"+": 11, regex("[a-z]+"): "lc", regex("[A-Z]+"): "uc"}
        object = {}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object)
        show(mc)
        schema = {"+?": 11, regex("[a-z]+"): "lc", regex("[A-Z]+"): "uc"}
        validate(schema, object)
        schema = {optional_key(11): 11, regex("[a-z]+"): "lc", regex("[A-Z]+"): "uc"}
        validate(schema, object)
        schema = {regex("[a-c]"): 4, regex("[b-d]"): 5}
        object = {"b": 4}
        validate(schema, object)
        object = {"b": 5}
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            object = {"b": 6}
            validate(schema, object)
        show(mc)
        schema = {"a": 1, regex("a"): 2}
        object = {"a": 1}
        validate(schema, object)
        object = {"a": 2}
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            object = {"a": 3}
            validate(schema, object)
        show(mc)

    def test_div(self):
        schema = div(2)
        object = 2
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            object = 3
            validate(schema, object)
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            object = "3"
            validate(schema, object)
        show(mc)
        with self.assertRaises(SchemaError) as mc:
            schema = div({})
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            schema = div(2, name="even")
            object = 3
            validate(schema, object)
        show(mc)
        schema = div(2, 1)
        object = 3
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            object = 2
            validate(schema, object)
        show(mc)
        with self.assertRaises(SchemaError) as mc:
            schema = div(1, {})
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            schema = div(2, 1, name="odd")
            object = 2
            validate(schema, object)
        show(mc)

    def test_at_most_one_of(self):
        schema = at_most_one_of("cat", "dog")
        object = {}
        validate(schema, object)
        object = {"cat": None}
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            object = {"cat": None, "dog": None}
            validate(schema, object)
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            object = 1
            validate(schema, object)
        show(mc)

    def test_at_least_one_of(self):
        schema = at_least_one_of("cat", "dog")
        with self.assertRaises(ValidationError) as mc:
            object = {}
            validate(schema, object)
        show(mc)
        object = {"cat": None}
        validate(schema, object)
        object = {"cat": None, "dog": None}
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            object = 1
            validate(schema, object)
        show(mc)

    def test_one_of(self):
        schema = one_of("cat", "dog")
        with self.assertRaises(ValidationError) as mc:
            object = {}
            validate(schema, object)
        show(mc)
        object = {"cat": None}
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            object = {"cat": None, "dog": None}
            validate(schema, object)
        show(mc)
        with self.assertRaises(ValidationError) as mc:
            object = 1
            validate(schema, object)
        show(mc)

    def test_keys(self):
        schema = keys("a", "b")
        object = {"a": 1, "b": 2}
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            object = {"a": 1}
            validate(schema, object)
        show(mc)

    def test_ifthen(self):
        schema = ifthen(keys("a"), keys("b"))
        object = {"a": 1, "b": 1}
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            object = {"a": 1}
            validate(schema, object)
        show(mc)
        object = {"c": 1}
        validate(schema, object)
        with self.assertRaises(ValidationError) as mc:
            schema = ifthen(keys("a"), keys("b"), keys("d"))
            validate(schema, object)
        show(mc)
        object = {"d": 1}
        validate(schema, object)

    def test_filter(self):
        with self.assertRaises(SchemaError) as mc:
            schema = filter(1, 2)
        show(mc)
        with self.assertRaises(SchemaError) as mc:
            schema = filter(1, 2, filter_name={})
        show(mc)
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
        object = "http://example.org"
        validate(schema, object, "url")
        with self.assertRaises(ValidationError) as mc:
            object = "https://example.org"
            validate(schema, object, "url")
        show(mc)

    def test_cond(self):
        with self.assertRaises(SchemaError) as mc:
            schema = cond("a", "b", "c")
        show(mc)

        schema = cond((0, 0), (1, 1))
        object = 1
        validate(schema, object)

        schema = cond((0, 0), (1, 1))
        object = 0
        validate(schema, object)

        schema = cond((0, 0), (1, 1))
        object = 2
        validate(schema, object)

        schema = cond((0, 0), (1, 1), (object, 1))
        object = 2
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object)
        show(mc)

    def test_fields(self):
        with self.assertRaises(SchemaError) as mc:
            fields("dummy")
        show(mc)
        with self.assertRaises(SchemaError) as mc:
            fields({1: "a"})
        show(mc)
        datetime_utc = intersect(datetime, fields({"tzinfo": timezone.utc}))
        object = datetime(2024, 4, 17)
        with self.assertRaises(ValidationError) as mc:
            validate(datetime_utc, object)
        show(mc)
        object = datetime(2024, 4, 17, tzinfo=timezone.utc)
        validate(datetime_utc, object)

    def test_strict(self):
        with self.assertRaises(ValidationError) as mc:
            schema = {"a?": 1, "b": 2}
            object = {"b": 2, "c": 3}
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = {"a": 1, "c": 3}
            validate(schema, object)
        show(mc)

        object = {"a": 1, "b": 2}
        validate(schema, object)

        object = {"b": 2}
        validate(schema, object)

    def test_missing_keys(self):
        schema = {"a?": 1, "b": 2}
        object = {"b": 2, "c": 3}
        validate(schema, object, strict=False)

        with self.assertRaises(ValidationError) as mc:
            object = {"a": 1, "c": 3}
            validate(schema, object, strict=False)
        show(mc)

        object = {"a": 1, "b": 2}
        validate(schema, object, strict=False)

        object = {"b": 2}
        validate(schema, object, strict=False)

        schema = {"a?": 1, "b": 2}
        object = {"b": 2, "c": 3}
        validate(schema, object, strict=False)

        with self.assertRaises(ValidationError) as mc:
            object = {"a": 1, "c": 3}
            validate(schema, object, strict=False)
        show(mc)

        object = {"a": 1, "b": 2}
        validate(schema, object, strict=False)

        object = {"b": 2}
        validate(schema, object, strict=False)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", "b"]
            object = ["a"]
            validate(schema, object, strict=False)

        object = ["a", "b"]
        validate(schema, object, strict=False)

        object = ["a", "b", "c"]
        validate(schema, object, strict=False)

        with self.assertRaises(ValidationError) as mc:
            object = ["a", "b", "c"]
            validate(schema, object, strict=True)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = {
                "s?": 1,
            }
            object = {
                "s": 2,
            }
            validate(schema, object, strict=True)
        show(mc)

    def test_compile(self):
        schema = {"a?": 1}
        object = {"a": 1}
        validate(schema, object)

        schema = compile(schema)
        validate(schema, object)

    def test_union(self):
        schema = {"a?": 1, "b": union(2, 3)}
        object = {"b": 2, "c": 3}
        validate(schema, object, strict=False)

        with self.assertRaises(ValidationError) as mc:
            object = {"b": 4, "c": 3}
            validate(schema, object)
        show(mc)

    def test_set_label(self):
        schema = {1: "a"}
        object = {1: "b"}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object)
        show(mc)
        schema = {1: set_label("a", "x")}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object)
        show(mc)
        validate(schema, object, subs={"x": anything})
        with self.assertRaises(SchemaError) as mc:
            schema = {1: set_label("a", {})}
        show(mc)
        with self.assertRaises(SchemaError) as mc:
            schema = {1: set_label("a", "x", debug={})}
        show(mc)
        schema = {1: set_label("a", "x", debug=True)}
        validate(schema, object, subs={"x": anything})
        schema = {1: set_label("a", "x", debug=True)}
        validate(schema, object, subs={"x": anything})
        schema = {1: set_label("a", "x", "y", debug=True)}
        validate(schema, object, subs={"x": anything})
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object, subs={"x": anything, "y": anything})
        show(mc)
        validate(schema, object, subs={"x": "b"})

    def test_quote(self):
        with self.assertRaises(ValidationError) as mc:
            schema = str
            object = str
            validate(schema, object)
        show(mc)

        schema = quote(str)
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            schema = quote({1, 2})
            object = 1
            validate(schema, object)
        show(mc)

        schema = quote({1, 2})
        object = {1, 2}
        validate(schema, object)

    @unittest.skipUnless(
        sys.version_info.major == 3 and sys.version_info.minor >= 7,
        "datetime.datetime.fromisoformat was introduced in Python 3.7",
    )
    def test_date_time(self):
        with self.assertRaises(ValidationError) as mc:
            schema = date_time
            object = "2000-30-30"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = "2000-12-300"
            validate(schema, object)
        show(mc)

        object = "2000-12-30"
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            schema = date_time("%Y^%m^%d")
            object = "2000^12^300"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = "2000^12-30"
            validate(schema, object)
        show(mc)

        object = "2000^12^30"
        validate(schema, object)

    @unittest.skipUnless(
        sys.version_info.major == 3 and sys.version_info.minor >= 7,
        "datetime.date.fromisoformat was introduced in Python 3.7",
    )
    def test_date(self):
        schema = date
        object = "2023-10-10"
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = "2023-10-10T01:01:01"
            validate(schema, object)
        show(mc)

    @unittest.skipUnless(
        sys.version_info.major == 3 and sys.version_info.minor >= 7,
        "datetime.time.fromisoformat was introduced in Python 3.7",
    )
    def test_time(self):
        schema = time
        object = "01:01:01"
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = "2023-10-10T01:01:01"
            validate(schema, object)
        show(mc)

    def test_nothing(self):
        schema = nothing
        object = "dummy"
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object)
        show(mc)

    def test_anything(self):
        schema = anything
        object = "dummy"
        validate(schema, object)

    def test_set(self):
        schema = set()
        object = set()
        validate(schema, object)
        object = {"a"}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object)
        show(mc)
        schema = {str}
        object = set()
        validate(schema, object)
        object = {"a"}
        validate(schema, object)
        object = {"a", "b"}
        validate(schema, object)
        object = {1}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object)
        show(mc)
        object = {"a", 1}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object)
        show(mc)
        schema = {int, str}
        object = {1.0}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object)
        show(mc)
        object = {1}
        validate(schema, object)
        object = {1, 2.0}
        with self.assertRaises(ValidationError) as mc:
            validate(schema, object)
        show(mc)

    def test_intersect(self):
        with self.assertRaises(ValidationError) as mc:
            schema = intersect(url, regex(r"^https", fullmatch=False))
            object = "ftp://example.com"
            validate(schema, object)
        show(mc)

        object = "https://example.com"
        validate(schema, object)

        def ordered_pair(o):
            return o[0] <= o[1]

        with self.assertRaises(ValidationError) as mc:
            schema = intersect((int, int), ordered_pair)
            object = (3, 2)
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = (1, 3, 2)
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = ("a", "b")
            validate(schema, object)
        show(mc)

        object = (1, 2)
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            schema = intersect(
                (int, int), set_name(lambda o: o[0] <= o[1], "ordered_pair")
            )
            object = (3, 2)
            validate(schema, object)
        show(mc)

    def test_complement(self):
        schema = intersect(url, complement(regex(r"^https", fullmatch=False)))
        object = "ftp://example.com"
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = "https://example.com"
            validate(schema, object)
        show(mc)

    def test_set_name(self):
        schema = set_name("a", "dummy")
        self.assertTrue(compile(schema).__name__ == "dummy")

        with self.assertRaises(ValidationError) as mc:
            object = "b"
            validate(schema, object)
        show(mc)

        object = "a"
        validate(schema, object)

        with self.assertRaises(SchemaError) as mc:
            schema = set_name("a", {})
        show(mc)

    def test_lax(self):
        schema = lax(["a", "b", "c"])
        object = ["a", "b", "c", "d"]
        validate(schema, object)

    def test_strict_wrapper(self):
        with self.assertRaises(ValidationError) as mc:
            schema = strict(["a", "b", "c"])
            object = ["a", "b", "c", "d"]
            validate(schema, object, strict=False)
        show(mc)

    def test_make_type(self):
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

    def test_generics(self):
        with self.assertRaises(ValidationError) as mc:
            schema = [str, ...]
            object = ("a", "b")
            validate(schema, object)
        show(mc)

        object = ["a", "b"]
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = ["a", 10]
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = ["a", ["b", "c"]]
            validate(schema, object)
        show(mc)

        schema = [...]
        object = ["a", "b", 1, 2]
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", ...]
            object = ["a", "b"]
            validate(schema, object)
        show(mc)

        object = []
        validate(schema, object)

        object = ["a", "a"]
        validate(schema, object)

        object = ["a", "a", "a", "a", "a"]
        validate(schema, object)

        schema = ["a", "b", ...]
        object = ["a", "b"]
        validate(schema, object)

        schema = ["a", "b", "c", ...]
        object = ["a", "b"]
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", "b", "c", "d", ...]
            object = ["a", "b"]
            validate(schema, object)
        show(mc)

        schema = [(str, int), ...]
        object = [("a", 1), ("b", 2)]
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            schema = [(str, int), ...]
            object = [("a", 1), ("b", "c")]
            validate(schema, object)

        schema = [email, ...]
        object = ["user1@example.com", "user2@example.com"]
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            schema = [email, ...]
            object = ["user1@example.com", "user00@user00.user00"]
            validate(schema, object)
        show(mc)

    def test_sequence(self):
        with self.assertRaises(ValidationError) as mc:
            schema = {"a": 1}
            object = []
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = []
            object = (1, 2)
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", "b", None, "c"]
            object = ["a", "b"]
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", "b"]
            object = ["a", "b", None, "c"]
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = ["a", int, ...]
            object = ["a", "c", 1]
            validate(schema, object)
        show(mc)

    def test_validate(self):
        class lower_case_string:
            @staticmethod
            def __validate__(object, name, strict, subs):
                if not isinstance(object, str):
                    return f"{name} (value:{object}) is not of type str"
                for c in object:
                    if not ("a" <= c <= "z"):
                        return (
                            f"{c}, contained in the string {name} "
                            + f"(value: {repr(object)}) is not a lower case letter"
                        )
                return ""

        with self.assertRaises(ValidationError) as mc:
            schema = lower_case_string
            object = 1
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = "aA"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = "aA"
            validate(schema, object)
        show(mc)

        object = "ab"
        validate(schema, object)

        schema = {"a": lower_case_string}
        object = {"a": "ab"}
        validate(schema, object)

        class lower_case_string:
            def __validate__(self, object, name, strict, subs):
                if not isinstance(object, str):
                    return f"{name} (value:{object}) is not of type str"
                for c in object:
                    if not ("a" <= c <= "z"):
                        return (
                            f"{c}, contained in the string {name} "
                            + f"(value: {repr(object)}) is not a lower case letter"
                        )
                return ""

        schema = {"a": lower_case_string}
        object = {"a": "ab"}
        validate(schema, object)

    def test_regex(self):
        with self.assertRaises(SchemaError) as cm:
            regex({})
        show(cm)

        with self.assertRaises(SchemaError) as cm:
            regex({}, name="test")
        show(cm)

        with self.assertRaises(SchemaError) as cm:
            regex("a", name={})
        show(cm)

        with self.assertRaises(SchemaError) as cm:
            schema = regex
            object = "a"
            validate(schema, object)
        show(cm)

        ip_address = regex(r"(?:[\d]+\.){3}(?:[\d]+)", name="ip_address")
        schema = {"ip": ip_address}
        object = {"ip": "123.123.123.123"}
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = {"ip": "123.123.123"}
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = {"ip": "123.123.123.abc"}
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = {"ip": "123.123..123"}
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = {"ip": "123.123.123.123.123"}
            validate(schema, object)
        show(mc)

        object = {"ip": "123.123.123.1000000"}
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = {"ip": ""}
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = regex(".")
            object = "\n"
            validate(schema, object)
        show(mc)

        schema = regex(".", flags=re.DOTALL)
        object = "\n"
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            schema = regex(".", flags=re.ASCII | re.MULTILINE)
            object = "\n"
            validate(schema, object)
        show(mc)

    def test_size(self):
        with self.assertRaises(SchemaError) as mc:
            schema = size("a", "b")
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(SchemaError) as mc:
            schema = size(-1, 0)
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(SchemaError) as mc:
            schema = size(1, 0)
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(SchemaError) as mc:
            schema = size(..., 1)
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(SchemaError) as mc:
            schema = size(1, "10")
            object = "a"
            validate(schema, object)
        show(mc)

        schema = size(1, 2)
        object = "a"
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = -1
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = []
            validate(schema, object)
        show(mc)

        object = [1]
        validate(schema, object)

        object = [1, 2]
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = [1, 2, 3]
            validate(schema, object)
        show(mc)

        schema = size(1)
        object = "a"
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = "aa"
            validate(schema, object)
        show(mc)

    def test_gt(self):
        with self.assertRaises(SchemaError) as mc:
            schema = gt
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = gt(1)
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = gt(1)
            object = 1
            validate(schema, object)
        show(mc)

        schema = gt(1)
        object = 2

    def test_ge(self):
        with self.assertRaises(SchemaError) as mc:
            schema = ge
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = ge(1)
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = ge(1)
            object = 0
            validate(schema, object)
        show(mc)

        schema = ge(1)
        object = 1

    def test_lt(self):
        with self.assertRaises(SchemaError) as mc:
            schema = lt
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = lt(1)
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = lt(1)
            object = 1
            validate(schema, object)
        show(mc)

        schema = lt(1)
        object = 0

    def test_le(self):
        with self.assertRaises(SchemaError) as mc:
            schema = le
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = le(1)
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = le(1)
            object = 2
            validate(schema, object)
        show(mc)

        schema = le(1)
        object = 1

    def test_interval(self):
        with self.assertRaises(SchemaError) as mc:
            schema = interval
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = interval(1, 10)
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = interval(1, 9)
            object = "a"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = -1
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = 10
            validate(schema, object)
        show(mc)

        object = 5
        validate(schema, object)

        schema = interval(1, 9, strict_lb=True, strict_ub=True)
        with self.assertRaises(ValidationError) as mc:
            object = 1
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = 9
            validate(schema, object)
        show(mc)

        object = 5
        validate(schema, object)

        schema = interval(0, ...)
        object = 5
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = -1
            validate(schema, object)
        show(mc)

        schema = interval(..., 0)
        object = -5
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = 1
            validate(schema, object)
        show(mc)

        schema = interval(..., ...)
        object = "0"
        validate(schema, object)

        with self.assertRaises(SchemaError) as cm:
            interval(0, "z")
        show(cm)

        with self.assertRaises(SchemaError) as cm:
            interval(..., {})
        show(cm)

        with self.assertRaises(SchemaError) as cm:
            interval({}, ...)
        show(cm)

    def test_email(self):
        schema = email
        object = "user00@user00.com"
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = "user00@user00.user00"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = 1
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = "@user00.user00"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = email(check_deliverability=True)
            object = "user@example.com"
            validate(schema, object)
        show(mc)

        object = "user@google.com"
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = "user@ffdfsdfsdfsasddasdadasad.com"
            validate(schema, object)
        show(mc)

    def test_ip_address(self):
        schema = {"ip": ip_address}
        object = {"ip": "123.123.123.123"}
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = {"ip": "123.123.123"}
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = {"ip": "123.123.123.256"}
            validate(schema, object)
        show(mc)

        object = {"ip": "2001:db8:3333:4444:5555:6666:7777:8888"}
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = {"ip": "2001:db8:3333:4444:5555:6666:7777:"}
            validate(schema, object)
        show(mc)

    def test_url(self):
        schema = {"url": url}
        object = {"url": "https://google.com"}
        validate(schema, object)

        object = {"url": "https://google.com?search=chatgpt"}
        validate(schema, object)

        object = {"url": "https://user:pass@google.com?search=chatgpt"}
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = {"url": "google.com"}
            validate(schema, object)
        show(mc)

    def test_domain_name(self):
        schema = domain_name
        object = "www.example.com"
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = "www.éxample.com"
            validate(schema, object)
        show(mc)

        schema = domain_name(ascii_only=False)
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = "-www.éxample.com"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            object = "www.é_xample.com"
            validate(schema, object)
        show(mc)

        with self.assertRaises(ValidationError) as mc:
            schema = domain_name(resolve=True)
            object = "www.exaaaaaaaaaaaaaaaaaaaaaaaaample.com"
            validate(schema, object)
        show(mc)

        object = "www.example.com"
        validate(schema, object)

    def test_number(self):
        schema = {"number": number}
        object = {"number": 1}
        validate(schema, object)

        object = {"number": 1.0}
        validate(schema, object)

        with self.assertRaises(ValidationError) as mc:
            object = {"number": "a"}
            validate(schema, object)
        show(mc)

    def test_truncation(self):
        with self.assertRaises(ValidationError) as mc:
            schema = "a"
            object = 1000 * "abc"
            validate(schema, object)
        show(mc)

        valid = str(mc.exception)

        self.assertTrue(r"...'" in valid)
        self.assertTrue("TRUNCATED" in valid)
        self.assertTrue(r"value:'" in valid)

        with self.assertRaises(ValidationError) as mc:
            object = 50 * "a"
            validate(schema, object)
        show(mc)

        valid = str(mc.exception)

        self.assertTrue(r"value:'" in valid)
        self.assertFalse("TRUNCATED" in valid)

        with self.assertRaises(ValidationError) as mc:
            object = 1000 * ["abcdefgh"]
            validate(schema, object)
        show(mc)

        valid = str(mc.exception)

        self.assertTrue(r"value:[" in valid)
        self.assertTrue(r"...]" in valid)
        self.assertTrue("TRUNCATED" in valid)

        with self.assertRaises(ValidationError) as mc:
            object = {}
            for i in range(1000):
                object[i] = 7 * i
            validate(schema, object)
        show(mc)

        valid = str(mc.exception)

        self.assertTrue(r"value:{" in valid)
        self.assertTrue("...}" in valid)
        self.assertTrue("TRUNCATED" in valid)

    def test_float_equal(self):
        with self.assertRaises(ValidationError) as mc:
            schema = 2.94
            object = 2.95
            validate(schema, object)
        show(mc)

        object = schema + 1e-10
        validate(schema, object)

    @unittest.skipUnless(
        sys.version_info.major == 3 and sys.version_info.minor >= 9,
        "Parametrized types were introduced in Python 3.9",
    )
    def test_type(self):
        with self.assertRaises(SchemaError) as cm:
            schema = list[str]
            object = ["a", "b"]
            validate(schema, object)
        show(cm)

    def test_callable(self):
        def even(x):
            return x % 2 == 0

        with self.assertRaises(ValidationError) as mc:
            schema = even
            object = 1
            validate(schema, object)
        show(mc)

        object = 2
        validate(schema, object)

        def fails(x):
            return 1 / x == 0

        with self.assertRaises(ValidationError) as mc:
            schema = fails
            object = 0
            validate(schema, object)
        show(mc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
