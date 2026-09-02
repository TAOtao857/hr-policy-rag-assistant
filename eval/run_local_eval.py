#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地评测脚本（无需 Coze 账号即可运行）：
  - tool 类：直接调用 plugins 下的函数，比对标准答案
  - retrieval 类：在 kb_output/knowledge_base.jsonl 中检索，验证答案确实在知识库里（bot 应能检索到）
  - refusal 类：验证知识库中不含该话题（bot 应拒答，不编造）

用法：
    python eval/run_local_eval.py
输出：每类命中率 + 总体报告
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_FILE = os.path.join(ROOT, "kb_output", "knowledge_base.jsonl")
DATASET = os.path.join(ROOT, "eval", "qa_dataset.jsonl")
PLUGINS = os.path.join(ROOT, "plugins")
sys.path.insert(0, PLUGINS)

from leave_calculator import calc_annual_leave
from overtime_calculator import calc_overtime_pay, monthly_to_hourly
from policy_validity import check_validity, check_by_name


def load_kb():
    chunks = []
    if not os.path.exists(KB_FILE):
        print(f"[warn] 未找到 {KB_FILE}，请先运行 scripts/build_knowledge_base.py")
        return chunks
    with open(KB_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


_KB_CACHE = None


def kb_contains(substrings):
    global _KB_CACHE
    if _KB_CACHE is None:
        _KB_CACHE = load_kb()
    for ch in _KB_CACHE:
        text = ch["content"]
        if all(s in text for s in substrings):
            return True
    return False


def run_tool(entry):
    name = entry["tool"]
    inp = entry["inputs"]
    exp = entry["expected"]
    if name == "leave_calculator.calc_annual_leave":
        got = calc_annual_leave(inp["entry_date"], inp.get("as_of"))
    elif name == "overtime_calculator.calc_overtime_pay":
        got = calc_overtime_pay(inp["hourly_base"], inp["hours"], inp["ot_type"])
    elif name == "overtime_calculator.monthly_to_hourly":
        got = monthly_to_hourly(inp["monthly_salary"])
    elif name == "policy_validity.check_validity":
        got = check_validity(inp["effective_date"], inp.get("revoked_date"),
                             inp.get("as_of"))
    else:
        return False, f"未知工具 {name}"
    # 标量型工具（加班费/时薪）：got 是数值，expected 也是数值，直接比较
    if isinstance(got, (int, float)):
        ok = isinstance(exp, (int, float)) and abs(got - exp) < 0.01
        return ok, got
    # 字典型工具（年假/时效）：逐字段比对
    ok = all(
        (got.get(k) == v) or (isinstance(v, float) and abs(got.get(k, 0) - v) < 0.01)
        for k, v in exp.items()
    )
    return ok, got


def main():
    total = {"tool": [0, 0], "retrieval": [0, 0], "refusal": [0, 0]}
    details = []
    with open(DATASET, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            cat = e["category"]
            if cat == "tool":
                ok, got = run_tool(e)
                got = str(got)
            elif cat == "retrieval":
                ok = kb_contains(e["expect_contains"])
                got = "in_kb" if ok else "not_in_kb"
            elif cat == "refusal":
                ok = not kb_contains([e["topic"]])
                got = "should_refuse" if ok else "topic_in_kb!"
            else:
                continue
            total[cat][1] += 1
            if ok:
                total[cat][0] += 1
            else:
                details.append(f"  [FAIL] {e['id']} {e['question']} -> {got}")

    print("=" * 48)
    print("本地评测报告（升级版 RAG 问答 - HR 助手）")
    print("=" * 48)
    for cat, (hit, alln) in total.items():
        rate = hit / alln * 100 if alln else 0
        print(f"  {cat:10s}: {hit}/{alln}  = {rate:.1f}%")
    overall_hit = sum(v[0] for v in total.values())
    overall_all = sum(v[1] for v in total.values())
    print(f"  {'总体':10s}: {overall_hit}/{overall_all}  = "
          f"{overall_hit / overall_all * 100:.1f}%")
    if details:
        print("-" * 48)
        print("失败项：")
        print("\n".join(details))
    print("=" * 48)


if __name__ == "__main__":
    main()
