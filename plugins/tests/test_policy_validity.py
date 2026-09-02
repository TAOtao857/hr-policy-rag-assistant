import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from policy_validity import check_validity, check_by_name


class TestValidity(unittest.TestCase):
    def test_current(self):
        r = check_validity("2008-01-01", None, "2026-09-01")
        self.assertEqual(r["status"], "现行有效")
        self.assertTrue(r["valid"])

    def test_revoked(self):
        r = check_validity("1995-01-01", "2020-01-01", "2026-09-01")
        self.assertEqual(r["status"], "已废止")
        self.assertFalse(r["valid"])

    def test_future(self):
        r = check_validity("2030-01-01", None, "2026-09-01")
        self.assertEqual(r["status"], "未生效")
        self.assertFalse(r["valid"])

    def test_by_name(self):
        r = check_by_name("职工带薪年休假条例", "2026-09-01")
        self.assertTrue(r["valid"])


if __name__ == "__main__":
    unittest.main()
