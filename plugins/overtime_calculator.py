#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加班费计算插件（升级版 RAG 问答的 Tool Use 示例）
规则依据：《劳动法》第四十四条
  - 工作日加班：不低于工资 150%
  - 休息日加班且不能补休：不低于工资 200%
  - 法定节假日加班：不低于工资 300%
  - 时薪 = 月薪 / 21.75 / 8
纯标准库实现，可作为 Coze 自定义代码插件的函数直接粘贴。
"""


def monthly_to_hourly(monthly_salary: float) -> float:
    """月薪转时薪（计薪基数 21.75 天 / 8 小时）。"""
    return round(monthly_salary / 21.75 / 8, 2)


def calc_overtime_pay(hourly_base: float, hours: float, ot_type: str) -> float:
    """计算加班费金额。

    Args:
        hourly_base: 时薪
        hours: 加班小时数
        ot_type: 加班类型，枚举 [工作日, 休息日, 法定节假日]
    Returns:
        加班费金额（四舍五入两位小数）
    """
    factor = {"工作日": 1.5, "休息日": 2.0, "法定节假日": 3.0}
    if ot_type not in factor:
        raise ValueError(f"未知加班类型: {ot_type}，应为 工作日/休息日/法定节假日")
    return round(hourly_base * hours * factor[ot_type], 2)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 4:
        hb = float(sys.argv[1])
        print(calc_overtime_pay(hb, float(sys.argv[2]), sys.argv[3]))
