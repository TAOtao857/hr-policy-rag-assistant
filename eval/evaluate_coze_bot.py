#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coze Bot 线上评测（需账号）。

读取 eval/qa_dataset.jsonl，逐条调用 Coze Bot 的 /v3/chat 接口，
对答案按类别检查，输出指标报告。

依赖：仅 Python 3 标准库（urllib / json / time），无需 pip install。
配置：通过 .env 文件或环境变量提供 COZE_PAT 与 COZE_BOT_ID。

用法：
    python eval/evaluate_coze_bot.py            # 跑全部 50 条
    python eval/evaluate_coze_bot.py --limit 5  # 只跑前 5 条（冒烟测试）
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(ROOT, "eval", "qa_dataset.jsonl")
API_BASE = "https://api.coze.cn"  # 国内版；海外版改为 https://api.coze.com


# ---------------------------------------------------------------------------
# 极简 .env 加载（避免引入 python-dotenv 依赖）
# ---------------------------------------------------------------------------
def load_dotenv(path=os.path.join(ROOT, ".env")):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _request(method, url, headers, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(question, headers, bot_id, retries=3):
    """发起流式对话，从 SSE 流中拼接 assistant 的最终回答文本。

    坑点记录（Coze 国内版 PAT）：
    - GET /v3/chat/retrieve 与 /v3/chat/message 在 PAT 下会返回
      4100 authentication is invalid，因此改用 stream=true，答案直接
      嵌在 POST 响应里，无需再轮询。
    - 带 reasoning 的模型（如 DeepSeek）正文落在 reasoning_content
      字段，content 可能为空，故两者都拼接。
    - 服务端偶发 [WinError 10054] 重置连接，故失败时指数退避重试。
    """
    body = {
        "bot_id": bot_id,
        "user_id": "eval",          # 固定 user_id => 每条独立会话
        "stream": True,
        "auto_save_history": True,
        "additional_messages": [
            {"role": "user", "content": question, "content_type": "text"}
        ],
    }
    data = json.dumps(body).encode("utf-8")
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                f"{API_BASE}/v3/chat", data=data, headers=headers, method="POST"
            )
            parts = []
            with urllib.request.urlopen(req, timeout=90) as resp:
                buf = b""
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line = line.strip()
                        if not line.startswith(b"data:"):
                            continue
                        payload = line[5:].strip()
                        if not payload or payload == b"[DONE]":
                            continue
                        try:
                            ev = json.loads(payload)
                        except Exception:
                            continue
                        if not isinstance(ev, dict):
                            try:
                                ev = json.loads(ev)
                            except Exception:
                                continue
                        if ev.get("role") == "assistant" and ev.get("type") == "answer":
                            c = ev.get("content") or ""
                            r = ev.get("reasoning_content") or ""
                            if isinstance(c, str):
                                parts.append(c)
                            if isinstance(r, str):
                                parts.append(r)
            return "".join(parts)
        except Exception as ex:
            last_err = ex
            time.sleep(2 * (attempt + 1))  # 2s, 4s, 6s 退避
    raise last_err


# ---------------------------------------------------------------------------
# 各类别判定
# ---------------------------------------------------------------------------
def _norm(s):
    # 去掉所有空白，缓解「10天」与「10 天」等表述差异
    return "".join(str(s).split())


def check_contains(ans, fragments):
    """回答需包含所有关键片段（去空白后做子串匹配）。tool / retrieval 通用。"""
    a = _norm(ans)
    miss = [f for f in fragments if _norm(f) not in a]
    return (len(miss) == 0), ("缺失片段: " + str(miss) if miss else "")


REFUSAL_MARKERS = [
    "无法确认", "无法", "不知道", "咨询 HR", "建议咨询", "暂不",
    "没有相关信息", "抱歉", "不便", "不便于", "不在", "不属于",
    "无法回答", "不涉及", "不在我", "不是", "没有权限",
]


def check_refusal(ans):
    hit = any(m in ans for m in REFUSAL_MARKERS)
    return hit, ("" if hit else "未检测到拒答表述")


def evaluate(ans, e):
    cat = e["category"]
    if cat in ("tool", "retrieval"):
        return check_contains(ans, e.get("expect_contains", []))
    if cat == "refusal":
        return check_refusal(ans)
    return False, f"未知类别 {cat}"


def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（0=全部）")
    args = ap.parse_args()

    pat = os.environ.get("COZE_PAT")
    bot_id = os.environ.get("COZE_BOT_ID")
    if not pat or not bot_id:
        print("请先在 .env 或环境变量中设置 COZE_PAT 与 COZE_BOT_ID")
        sys.exit(1)
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
    }

    rows = [json.loads(l) for l in open(DATASET, "r", encoding="utf-8") if l.strip()]
    if args.limit:
        rows = rows[: args.limit]

    stats = {"tool": [0, 0], "retrieval": [0, 0], "refusal": [0, 0]}
    print(f"{'ID':<6}{'类别':<10}{'结果':<6}说明")
    print("-" * 70)
    for e in rows:
        cat = e["category"]
        try:
            ans = chat(e["question"], headers, bot_id)
        except Exception as ex:  # 单条失败不中断整体
            stats[cat][1] += 1
            print(f"{e['id']:<6}{cat:<10}{'ERROR':<6}{ex}")
            continue
        ok, note = evaluate(ans, e)
        stats[cat][0] += 1 if ok else 0
        stats[cat][1] += 1
        print(f"{e['id']:<6}{cat:<10}{'PASS' if ok else 'FAIL':<6}{note}")
        time.sleep(1)  # 降低请求频率，避免触发限流

    total_ok = sum(v[0] for v in stats.values())
    total_all = sum(v[1] for v in stats.values())
    print("-" * 70)
    print("分类结果：")
    for cat, (ok, allc) in stats.items():
        rate = (ok / allc * 100) if allc else 0
        print(f"  {cat:<10} {ok}/{allc} = {rate:.0f}%")
    overall = (total_ok / total_all * 100) if total_all else 0
    print(f"  总体     {total_ok}/{total_all} = {overall:.0f}%")


if __name__ == "__main__":
    main()
