import unittest

from validate import _keys, email, ip_address, number, optional_key, regex, url, union, validate


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
        print(valid)
        self.assertFalse(valid == "")

        object = {"a": 1, "c": 3}
        valid = validate(schema, object, name, strict=True)
        print(valid)
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
        print(valid)
        self.assertFalse(valid == "")

        object = {"a": 1, "b": 2}
        valid = validate(schema, object, name, strict=False)
        self.assertTrue(valid == "")

        object = {"b": 2}
        valid = validate(schema, object, name, strict=False)
        self.assertTrue(valid == "")

    def test_union(self):
        schema = {optional_key("a"): 1, "b": union(2, 3)}
        name = "my_object"
        object = {"b": 2, "c": 3}
        valid = validate(schema, object, name, strict=False)
        self.assertTrue(valid == "")

        object = {"b": 4, "c": 3}
        valid = validate(schema, object, name, strict=False)
        print(valid)
        self.assertFalse(valid == "")

    def test_generics(self):
        schema = dict[str]
        name = "my_object"
        object = {}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        schema = list[tuple()]
        object = ["a", "b"]
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        schema = list[str]
        object = ("a", "b")
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        object = ["a", "b"]
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = ["a", 10]
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        object = ["a", ["b", "c"]]
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        schema = list[(str, int)]
        object = [("a", 1), ("b", 2)]
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        schema = list[(str, int)]
        object = [("a", 1), ("b", "c")]
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        schema = list[email]
        object = ["user1@example.com", "user2@example.com"]
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        schema = list[email]
        object = ["user1@example.com", "user00@user00.user00"]
        valid = validate(schema, object, name, strict=True)
        print(valid)
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
        print(valid)
        self.assertFalse(valid == "")

        object = "aA"
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        object = "aA"
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        object = "ab"
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        schema = {"a": lower_case_string}
        object = {"a": "ab"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

    def test_regex(self):
        ip_address = regex(r"(?:[\d]+\.){3}(?:[\d]+)", name="ip_address")
        schema = {"ip": ip_address}
        name = "my_object"
        object = {"ip": "123.123.123.123"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"ip": "123.123.123"}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.abc"}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123..123"}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.123.123"}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.1000000"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"ip": ""}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

    def test_email(self):
        schema = email
        object = "user00@user00.com"
        name = "my_object"
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertTrue(valid == "")

        object = "user00@user00.user00"
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

    def test_ip_address(self):
        schema = {"ip": ip_address}
        name = "my_object"
        object = {"ip": "123.123.123.123"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

        object = {"ip": "123.123.123"}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")

        object = {"ip": "123.123.123.256"}
        valid = validate(schema, object, name, strict=True)
        print(valid)
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
        print(valid)
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
        print(valid)
        self.assertFalse(valid == "")
        


if __name__ == "__main__":
    unittest.main()
