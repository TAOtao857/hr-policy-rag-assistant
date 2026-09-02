import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from leave_calculator import calc_annual_leave


class TestLeave(unittest.TestCase):
    def test_six_years(self):
        r = calc_annual_leave("2020-03-01", "2026-09-01")
        self.assertTrue(r["eligible"])
        self.assertEqual(r["days"], 5)
        self.assertEqual(r["service_years"], 6)

    def test_ten_year_boundary(self):
        r = calc_annual_leave("2016-08-01", "2026-09-01")
        self.assertEqual(r["days"], 10)

    def test_twenty_year(self):
        r = calc_annual_leave("2005-01-01", "2026-09-01")
        self.assertEqual(r["days"], 15)

    def test_less_than_one_year(self):
        # 2025-10-01 入职，至 2026-03-01 跨年但本单位工龄不足 1 年 -> 不享受
        r = calc_annual_leave("2025-10-01", "2026-03-01")
        self.assertFalse(r["eligible"])
        self.assertEqual(r["days"], 0)

    def test_first_year_proration(self):
        # 2026-03-01 入职，当年剩余 306 天 -> int(306/365*5)=4
        r = calc_annual_leave("2026-03-01", "2026-09-01")
        self.assertTrue(r["eligible"])
        self.assertEqual(r["days"], 4)
        self.assertIn("折算", r["note"])


if __name__ == "__main__":
    unittest.main()
