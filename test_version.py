import unittest

import toml

import vtjson


class TestValidation(unittest.TestCase):
    def test_version(self):
        with open("pyproject.toml", "r") as f:
            data = toml.load(f)
        self.assertTrue(data["project"]["version"] == vtjson.__version__)


if __name__ == "__main__":
    unittest.main()
