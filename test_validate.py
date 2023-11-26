import re
import sys
import unittest

from vtjson import (
    _keys,
    _validate,
    complement,
    date,
    domain_name,
    email,
    intersect,
    interval,
    ip_address,
    lax,
    make_type,
    number,
    quote,
    regex,
    set_name,
    strict,
    union,
    url,
)


class TestValidation(unittest.TestCase):
    def test_keys(self):
        schema = {"a?": 1, "b": 2, "c?": 3}
        keys = _keys(schema)
        self.assertEqual(keys, {"a", "b", "c"})

    def test_strict(self):
        schema = {"a?": 1, "b": 2}
        object = {"b": 2, "c": 3}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = {"a": 1, "c": 3}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = {"a": 1, "b": 2}
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = {"b": 2}
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

    def test_missing_keys(self):
        schema = {"a?": 1, "b": 2}
        object = {"b": 2, "c": 3}
        valid = _validate(schema, object, strict=False)
        self.assertTrue(valid == "")

        object = {"a": 1, "c": 3}
        valid = _validate(schema, object, strict=False)
        print(valid)
        self.assertFalse(valid == "")

        object = {"a": 1, "b": 2}
        valid = _validate(schema, object, strict=False)
        self.assertTrue(valid == "")

        object = {"b": 2}
        valid = _validate(schema, object, strict=False)
        self.assertTrue(valid == "")

        schema = {"a?": 1, "b": 2}
        object = {"b": 2, "c": 3}
        valid = _validate(schema, object, strict=False)
        self.assertTrue(valid == "")

        object = {"a": 1, "c": 3}
        valid = _validate(schema, object, strict=False)
        print(valid)
        self.assertFalse(valid == "")

        object = {"a": 1, "b": 2}
        valid = _validate(schema, object, strict=False)
        self.assertTrue(valid == "")

        object = {"b": 2}
        valid = _validate(schema, object, strict=False)
        self.assertTrue(valid == "")

        schema = ["a", "b"]
        object = ["a"]
        valid = _validate(schema, object, strict=False)
        print(valid)
        self.assertFalse(valid == "")

        object = ["a", "b"]
        valid = _validate(schema, object, strict=False)
        self.assertTrue(valid == "")

        object = ["a", "b", "c"]
        valid = _validate(schema, object, strict=False)
        self.assertTrue(valid == "")

        object = ["a", "b", "c"]
        valid = _validate(schema, object, strict=True)
        print(valid)
        self.assertFalse(valid == "")

    def test_union(self):
        schema = {"a?": 1, "b": union(2, 3)}
        object = {"b": 2, "c": 3}
        valid = _validate(schema, object, strict=False)
        self.assertTrue(valid == "")

        object = {"b": 4, "c": 3}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_quote(self):
        schema = str
        object = str
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = quote(str)
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = {1, 2}
        object = 1
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = quote({1, 2})
        object = 1
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = {1, 2}
        object = {1, 2}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = quote({1, 2})
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

    @unittest.skipUnless(
        sys.version_info.major == 3 and sys.version_info.minor >= 7,
        "datetime.datetime.fromisoformat was introduced in Python 3.7",
    )
    def test_date2(self):
        schema = date
        object = "2000-30-30"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = "2000-12-300"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = "2000-12-30"
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

    def test_date(self):
        schema = date("%Y^%m^%d")
        object = "2000^12^300"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = "2000^12-30"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = "2000^12^30"
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

    def test_set(self):
        schema = {2, 3}
        object = 5
        valid = _validate(schema, object, strict=False)
        print(valid)
        self.assertFalse(valid == "")

        schema = {int, str}
        object = 1.0
        valid = _validate(schema, object, strict=False)
        print(valid)
        self.assertFalse(valid == "")

    def test_intersect(self):
        schema = intersect(url, regex(r"^https", fullmatch=False))
        object = "ftp://example.com"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = "https://example.com"
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        def ordered_pair(o):
            return o[0] <= o[1]

        schema = intersect((int, int), ordered_pair)
        object = (3, 2)
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = (1, 3, 2)
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = ("a", "b")
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = (1, 2)
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = intersect((int, int), set_name(lambda o: o[0] <= o[1], "ordered_pair"))
        object = (3, 2)
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_complement(self):
        schema = intersect(url, complement(regex(r"^https", fullmatch=False)))
        object = "ftp://example.com"
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = "https://example.com"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_set_name(self):
        schema = set_name("a", "dummy")
        self.assertTrue(schema.__name__ == "dummy")

        object = "b"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = "a"
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

    def test_lax(self):
        schema = lax(["a", "b", "c"])
        object = ["a", "b", "c", "d"]
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

    def test_strict_wrapper(self):
        schema = strict(["a", "b", "c"])
        object = ["a", "b", "c", "d"]
        valid = _validate(schema, object, strict=False)
        print(valid)
        self.assertFalse(valid == "")

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
        schema = [str, ...]
        object = ("a", "b")
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = ["a", "b"]
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = ["a", 10]
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = ["a", ["b", "c"]]
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = [...]
        object = ["a", "b", 1, 2]
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = ["a", ...]
        object = ["a", "b"]
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = []
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = ["a", "a"]
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = ["a", "a", "a", "a", "a"]
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = ["a", "b", ...]
        object = ["a", "b"]
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = ["a", "b", "c", ...]
        object = ["a", "b"]
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = ["a", "b", "c", "d", ...]
        object = ["a", "b"]
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = [(str, int), ...]
        object = [("a", 1), ("b", 2)]
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = [(str, int), ...]
        object = [("a", 1), ("b", "c")]
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = [email, ...]
        object = ["user1@example.com", "user2@example.com"]
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = [email, ...]
        object = ["user1@example.com", "user00@user00.user00"]
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_sequence(self):
        schema = {"a": 1}
        object = []
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = []
        object = (1, 2)
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = ["a", "b", None, "c"]
        object = ["a", "b"]
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = ["a", "b"]
        object = ["a", "b", None, "c"]
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test__validate(self):
        class lower_case_string:
            @staticmethod
            def __validate__(object, name, strict):
                if not isinstance(object, str):
                    return f"{name} (value:{object}) is not of type str"
                for c in object:
                    if not ("a" <= c <= "z"):
                        return (
                            f"{c}, contained in the string {name} "
                            + f"(value: {repr(object)}) is not a lower case letter"
                        )
                return ""

        schema = lower_case_string
        object = 1
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = "aA"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = "aA"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = "ab"
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = {"a": lower_case_string}
        object = {"a": "ab"}
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

    def test_regex(self):
        schema = regex({})
        object = "dummy"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = regex({}, name="test")
        object = "dummy"
        self.assertTrue(schema.__name__ == "test")
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        ip_address = regex(r"(?:[\d]+\.){3}(?:[\d]+)", name="ip_address")
        schema = {"ip": ip_address}
        object = {"ip": "123.123.123.123"}
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = {"ip": "123.123.123"}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.abc"}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123..123"}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.123.123"}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.1000000"}
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = {"ip": ""}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = regex(".")
        object = "\n"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = regex(".", flags=re.DOTALL)
        object = "\n"
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = regex(".", flags=re.ASCII | re.MULTILINE)
        object = "\n"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_interval(self):
        schema = interval(1, 10)
        object = "a"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = interval(1, 9)
        object = "a"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = -1
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = 10
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = 5
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = interval(0, ...)
        object = 5
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = -1
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = interval(..., 0)
        object = -5
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = 1
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = interval(..., ...)
        object = "0"
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        schema = interval(0, "z")
        object = "0"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_email(self):
        schema = email
        object = "user00@user00.com"
        valid = _validate(schema, object)
        print(valid)
        self.assertTrue(valid == "")

        object = "user00@user00.user00"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = "@user00.user00"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = email(check_deliverability=True)
        object = "user@example.com"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = "user@google.com"
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = "user@ffdfsdfsdfsasddasdadasad.com"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_ip_address(self):
        schema = {"ip": ip_address}
        object = {"ip": "123.123.123.123"}
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = {"ip": "123.123.123"}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.256"}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_url(self):
        schema = {"url": url}
        object = {"url": "https://google.com"}
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = {"url": "https://google.com?search=chatgpt"}
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = {"url": "https://user:pass@google.com?search=chatgpt"}
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = {"url": "google.com"}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_domain_name(self):
        schema = domain_name
        object = "www.uhasselt.be"
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = "www.uhassëlt.be"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        schema = domain_name(ascii_only=False)
        valid = _validate(schema, object)
        print(valid)
        self.assertTrue(valid == "")

        object = "-www.uhassëlt.be"
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_number(self):
        schema = {"number": number}
        object = {"number": 1}
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = {"number": 1.0}
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        object = {"number": "a"}
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_truncation(self):
        schema = "a"
        object = 1000 * "abc"
        valid = _validate(schema, object)
        print(valid)
        self.assertTrue(r"...'" in valid)
        self.assertTrue("TRUNCATED" in valid)
        self.assertTrue(r"value:'" in valid)

        object = 50 * "a"
        valid = _validate(schema, object)
        print(valid)
        self.assertTrue(r"value:'" in valid)
        self.assertFalse("TRUNCATED" in valid)

        object = 1000 * ["abcdefgh"]
        valid = _validate(schema, object)
        print(valid)
        self.assertTrue(r"value:[" in valid)
        self.assertTrue(r"...]" in valid)
        self.assertTrue("TRUNCATED" in valid)

        object = {}
        for i in range(1000):
            object[i] = 7 * i
        valid = _validate(schema, object)
        print(valid)
        self.assertTrue(r"value:{" in valid)
        self.assertTrue("...}" in valid)
        self.assertTrue("TRUNCATED" in valid)

    def test_float_equal(self):
        schema = 2.94
        object = 2.95
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = schema + 1e-10
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

    @unittest.skipUnless(
        sys.version_info.major == 3 and sys.version_info.minor >= 9,
        "Parametrized types were introduced in Python 3.9",
    )
    def test_type(self):
        schema = list[str]
        object = ["a", "b"]
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

    def test_callable(self):
        def even(x):
            return x % 2 == 0

        schema = even
        object = 1
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")

        object = 2
        valid = _validate(schema, object)
        self.assertTrue(valid == "")

        def fails(x):
            return 1 / x == 0

        schema = fails
        object = 0
        valid = _validate(schema, object)
        print(valid)
        self.assertFalse(valid == "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
