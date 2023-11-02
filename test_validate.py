import unittest

from validate import (
    _keys,
    email,
    ip_address,
    make_type,
    number,
    optional_key,
    regex,
    url,
    union,
    validate,
)

DEBUG = True


def log(*l, debug=DEBUG):
    if debug:
        print(*l)


class TestValidation(unittest.TestCase):
    def test_keys(self):
        schema = {optional_key("a"): 1, "b": 2, optional_key("c"): 3}
        keys = _keys(schema)
        self.assertEqual(keys, {"a", "b", "c"})

    def test_strict(self):
        schema = {optional_key("a"): 1, "b": 2}
        name = "my_object"
        object = {"b": 2, "c": 3}
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = {"a": 1, "c": 3}
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = {"a": 1, "b": 2}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"b": 2}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

    def test_missing_keys(self):
        schema = {optional_key("a"): 1, "b": 2}
        name = "my_object"
        object = {"b": 2, "c": 3}
        valid = validate(schema, object, name, strict=False)
        self.assertTrue(valid == "")

        object = {"a": 1, "c": 3}
        valid = validate(schema, object, name, strict=False)
        log(valid)
        self.assertFalse(valid == "")

        object = {"a": 1, "b": 2}
        valid = validate(schema, object, name, strict=False)
        self.assertTrue(valid == "")

        object = {"b": 2}
        valid = validate(schema, object, name, strict=False)
        self.assertTrue(valid == "")

        schema = ["a", "b"]
        object = ["a"]
        valid = validate(schema, object, name, strict=False)
        log(valid)
        self.assertFalse(valid == "")

        object = ["a", "b"]
        valid = validate(schema, object, name, strict=False)
        self.assertTrue(valid == "")

        object = ["a", "b", "c"]
        valid = validate(schema, object, name, strict=False)
        self.assertTrue(valid == "")

        object = ["a", "b", "c"]
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

    def test_union(self):
        schema = {optional_key("a"): 1, "b": union(2, 3)}
        name = "my_object"
        object = {"b": 2, "c": 3}
        valid = validate(schema, object, name, strict=False)
        self.assertTrue(valid == "")

        object = {"b": 4, "c": 3}
        valid = validate(schema, object, name, strict=False)
        log(valid)
        self.assertFalse(valid == "")

    def test_make_type(self):
        global url
        schema = {"a": 1}
        t = make_type(schema, "example", strict=True, debug=DEBUG)
        self.assertTrue(t.__name__ == "example")
        self.assertFalse(isinstance({"a": 2}, t))
        self.assertTrue(isinstance({"a": 1}, t))
        self.assertFalse(isinstance({"a": 1, "b": 1}, t))

        t = make_type(schema, "example", strict=False, debug=DEBUG)
        self.assertTrue(t.__name__ == "example")
        self.assertTrue(isinstance({"a": 1, "b": 1}, t))

        url_ = make_type(url, debug=DEBUG)
        self.assertTrue(url_.__name__ == "url")
        self.assertFalse(isinstance("google.com", url_))
        self.assertTrue(isinstance("https://google.com", url_))

        t = make_type({}, debug=DEBUG)
        self.assertTrue(t.__name__ == "schema")

    def test_generics(self):
        schema = [str, ...]
        name = "my_object"
        object = ("a", "b")
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = ["a", "b"]
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = ["a", 10]
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = ["a", ["b", "c"]]
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        schema = [...]
        object = ["a", "b", 1, 2]
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        schema = ["a", ...]
        object = ["a", "b"]
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = []
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = ["a", "a"]
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = ["a", "a", "a", "a", "a"]
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        schema = ["a", "b", ...]
        object = ["a", "b"]
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        schema = ["a", "b", "c", ...]
        object = ["a", "b"]
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        schema = ["a", "b", "c", "d", ...]
        object = ["a", "b"]
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        schema = [(str, int), ...]
        object = [("a", 1), ("b", 2)]
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        schema = [(str, int), ...]
        object = [("a", 1), ("b", "c")]
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        schema = [email, ...]
        object = ["user1@example.com", "user2@example.com"]
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        schema = [email, ...]
        object = ["user1@example.com", "user00@user00.user00"]
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

    def test_sequence(self):
        schema = {"a": 1}
        name = "my_object"
        object = []
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        schema = []
        name = "my_object"
        object = (1, 2)
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

    def test_validate(self):
        class lower_case_string:
            @staticmethod
            def __validate__(object, name, strict=False):
                if not isinstance(object, str):
                    return f"{name} (value:{object}) is not of type str"
                for c in object:
                    if not ("a" <= c <= "z"):
                        return f"{c}, contained in the string {name}, is not a lower case letter"
                return ""

        schema = lower_case_string
        object = 1
        name = "my_object"
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = "aA"
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = "aA"
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = "ab"
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        schema = {"a": lower_case_string}
        object = {"a": "ab"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

    def test_regex(self):
        schema = regex({})
        name = "my_object"
        object = "dummy"
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        ip_address = regex(r"(?:[\d]+\.){3}(?:[\d]+)", name="ip_address")
        schema = {"ip": ip_address}
        object = {"ip": "123.123.123.123"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"ip": "123.123.123"}
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.abc"}
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123..123"}
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.123.123"}
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.1000000"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"ip": ""}
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

    def test_email(self):
        schema = email
        object = "user00@user00.com"
        name = "my_object"
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertTrue(valid == "")

        object = "user00@user00.user00"
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

    def test_ip_address(self):
        schema = {"ip": ip_address}
        name = "my_object"
        object = {"ip": "123.123.123.123"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"ip": "123.123.123"}
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.256"}
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

    def test_url(self):
        schema = {"url": url}
        name = "my_object"
        object = {"url": "https://google.com"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"url": "https://google.com?search=chatgpt"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"url": "https://user:pass@google.com?search=chatgpt"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"url": "google.com"}
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")

    def test_number(self):
        schema = {"number": number}
        name = "my_object"
        object = {"number": 1}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"number": 1.0}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"number": "a"}
        valid = validate(schema, object, name, strict=True)
        log(valid)
        self.assertFalse(valid == "")


if __name__ == "__main__":
    unittest.main()
