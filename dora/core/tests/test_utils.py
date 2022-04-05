import unittest

from dora.core import utils


class UtilsTestCase(unittest.TestCase):
    def test_normalize_description(self):
        cases = [
            (
                "Lorem ipsum dolor sit amet",
                10,
                ("Lorem ips…", "Lorem ipsum dolor sit amet"),
            ),
            (
                "Lorem ipsum dolor sit amet",
                100,
                ("Lorem ipsum dolor sit amet", ""),
            ),
        ]

        for input, limit, expected in cases:
            self.assertEqual(utils.normalize_description(input, limit), expected)

    def test_normalize_phone_number(self):
        cases = [
            ("01-02-03 04.05", "0102030405"),
            ("0102030405 - 0203040506", "0102030405"),
            ("3509", "3509"),
        ]

        for input, expected in cases:
            self.assertEqual(utils.normalize_phone_number(input), expected)
