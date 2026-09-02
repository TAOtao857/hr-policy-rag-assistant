#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年假计算插件（升级版 RAG 问答的 Tool Use 示例）
规则依据：《职工带薪年休假条例》
  - 累计工作已满1年不满10年：5天
  - 已满10年不满20年：10天
  - 已满20年：15天
  - 入职当年按剩余日历天数折算（不足1天部分不享受）
注意（简化假设）：本函数把 entry_date 视为「已具备年休假资格的工龄起点」，
即默认员工在 entry_date 之前已连续工作满 1 年。因此同年入职时按剩余天数折算；
跨年但本单位工龄不足 1 年时返回不享受。如需严格区分「累计工龄」，可扩展传入 prior_service_years。
纯标准库实现，作为 Coze 代码插件内部逻辑直接复用。
"""
from datetime import date


def _parse(d):
    return date.fromisoformat(d)


def calc_annual_leave(entry_date: str, as_of: str | None = None) -> dict:
    """计算某员工截至 as_of 的带薪年休假天数。

    Args:
        entry_date: 入职日期 YYYY-MM-DD
        as_of: 计算基准日 YYYY-MM-DD，默认今天
    Returns:
        {"eligible", "base_days", "days", "service_years", "note"}
    """
    e = _parse(entry_date)
    a = _parse(as_of) if as_of else date.today()

    # 入职当年：按剩余日历天数折算（条例：新进职工当年休假按剩余天数折算）
    if e.year == a.year:
        end_of_year = date(a.year, 12, 31)
        remaining = (end_of_year - e).days + 1
        days = int(remaining / 365 * 5)  # 不足1天不享受 -> int 截断
        return {
            "eligible": True,
            "base_days": 5,
            "days": days,
            "service_years": 0,
            "note": f"入职当年按剩余日历天数折算（剩余{remaining}天）",
        }

    service = a.year - e.year - ((a.month, a.day) < (e.month, e.day))
    if service < 1:
        return {"eligible": False, "base_days": 0, "days": 0,
                "service_years": service, "note": "连续工作未满1年，不享受年休假"}
    if service < 10:
        base = 5
    elif service < 20:
        base = 10
    else:
        base = 15
    return {"eligible": True, "base_days": base, "days": base,
            "service_years": service, "note": ""}


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        print(calc_annual_leave(sys.argv[1],
                                sys.argv[2] if len(sys.argv) > 2 else None))
