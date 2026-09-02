#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政策时效校验插件（升级版 RAG 问答的 Tool Use 示例）
判断某条款是否现行有效：
  - 已设置废止日期且当前晚于废止日期 -> 已废止
  - 当前早于生效日期 -> 未生效
  - 否则 -> 现行有效
支持两种用法：
  1) 直接传 effective_date / revoked_date
  2) 传 name，从 regulations.json 注册表查
"""
import json
import os
from datetime import date

REG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regulations.json")


def _parse(d):
    return date.fromisoformat(d)


def check_validity(effective_date: str, revoked_date: str | None = None,
                   as_of: str | None = None) -> dict:
    e = _parse(effective_date)
    a = _parse(as_of) if as_of else date.today()
    r = _parse(revoked_date) if revoked_date else None
    if r and a > r:
        status, valid = "已废止", False
    elif a < e:
        status, valid = "未生效", False
    else:
        status, valid = "现行有效", True
    return {"status": status, "valid": valid,
            "effective_date": effective_date, "revoked_date": revoked_date}


def load_registry():
    with open(REG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def check_by_name(name: str, as_of: str | None = None) -> dict:
    for item in load_registry():
        if item["name"] == name:
            res = check_validity(item["effective_date"],
                                 item.get("revoked_date"), as_of)
            res["name"] = name
            res["summary"] = item.get("summary", "")
            return res
    raise KeyError(f"注册表中未找到: {name}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        if len(sys.argv) == 2:
            print(check_by_name(sys.argv[1]))
        else:
            print(check_validity(sys.argv[1],
                                  sys.argv[2] if len(sys.argv) > 2 else None))
