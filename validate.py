import re, unittest

from email_validator import validate_email, EmailNotValidError


class optional_key:
    def __init__(self, key):
        self.key = key


class union:
    def __init__(self, *schemas):
        self.schemas = schemas

    def __validate__(self, object, name, strict=False):
        messages = []
        for schema in self.schemas:
            message = validate(schema, object, name, strict=strict)
            if message == "":
                return ""
            else:
                messages.append(message)
        return " and ".join(messages)

class email:
    def __validate__(object, name, strict=False):
        try:
            validate_email(object, check_deliverability=False)
            return ""
        except EmailNotValidError as e:
            return f"{name} is not a valid email address: {str(e)}"

class regex:
    def __init__(self,regex):
        self.regex = regex
        self.pattern = re.compile(regex)
        

    def __validate__(self, object, name, strict=False):
        if self.pattern.fullmatch(object):
            return ""
        else:
            return f"{name} does not match the pattern {self.regex}"

def _keys(dict):
    ret = set()
    for k in dict:
        if isinstance(k, optional_key):
            ret.add(k.key)
        else:
            ret.add(k)
    return ret


def validate(schema, object, name, strict=False):
    if hasattr(schema, "__validate__"):  # duck typing
        return schema.__validate__(object, name, strict=strict)
    elif isinstance(schema, type):
        if not isinstance(object, schema):
            return f"{name} is not of type {schema.__name__}"
        else:
            return ""
    elif isinstance(schema, list) or isinstance(schema, tuple):
        if type(schema) != type(object):
            return f"{name} is not of type {type(schema).__name}"
        l = len(object)
        if strict and l != len(schema):
            return f"{name} does not have length {len(schema)}"
        for i in range(len(schema)):
            name_ = f"{name}[{i}]"
            if i >= l:
                return f"{name_} does not exist"
            else:
                ret = validate(schema[i], object[i], name_, strict=strict)
                if ret != "":
                    return ret
        return ""
    elif isinstance(schema, dict):
        if type(schema) != type(object):
            return f"{name} is not of type {type(schema).__name}"
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
            name_ = f"{name}['{k_}']"
            if k_ not in object:
                return f"{name_} is missing"
            else:
                ret = validate(schema[k], object[k_], name_, strict=strict)
                if ret != "":
                    return ret
        return ""
    elif object != schema:
        return f"{name} is not equal to {repr(schema)}"
    return ""


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

    def test_validate(self):
        class lower_case:
            @staticmethod
            def __validate__(object, name, strict=False):
                if not isinstance(object, str):
                    return f"{name} is not a string"
                for c in object:
                    if not ("a" <= c <= "z"):
                        return f"{c}, contained in {name}, is not a lower case letter"
                return ""

        schema = lower_case
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
        schema = {"a": lower_case}
        object = {"a": "ab"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")

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

    def test_regex(self):
        ip_address = regex(r"([\d]+\.){3}([\d]+)")
        schema = {"ip": ip_address}
        name="my_object"
        object = {"ip":"123.123.123.123"}
        valid = validate(schema, object, name, strict=True)
        self.assertTrue(valid == "")
        object = {"ip":"123.123.123"}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")
        object = {"ip":"123.123.123.abc"}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")
        object = {"ip":"123.123..123"}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")
        object = {"ip":"123.123.123.123.123"}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")
        object = {"ip":""}
        valid = validate(schema, object, name, strict=True)
        print(valid)
        self.assertFalse(valid == "")
        
        
        
if __name__ == "__main__":
    unittest.main()
