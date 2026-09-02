import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from overtime_calculator import calc_overtime_pay, monthly_to_hourly


class TestOvertime(unittest.TestCase):
    def test_weekday(self):
        self.assertEqual(calc_overtime_pay(100, 2, "工作日"), 300.0)

    def test_restday(self):
        self.assertEqual(calc_overtime_pay(100, 3, "休息日"), 600.0)

    def test_holiday(self):
        self.assertEqual(calc_overtime_pay(100, 1, "法定节假日"), 300.0)

    def test_monthly_to_hourly(self):
        self.assertAlmostEqual(monthly_to_hourly(8000), 8000 / 21.75 / 8, places=2)

    def test_bad_type(self):
        with self.assertRaises(ValueError):
            calc_overtime_pay(100, 1, "周末")


if __name__ == "__main__":
    unittest.main()
