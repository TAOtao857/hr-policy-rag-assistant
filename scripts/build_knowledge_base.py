#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库构建脚本：读取 data/ 下的 Markdown 文档，按标题层级切分为 300~500 字的 chunk，
提取「生效日期 / 废止日期」等 metadata，输出 kb_output/knowledge_base.jsonl 供上传到 Coze 知识库。

用法：
    python scripts/build_knowledge_base.py
依赖：仅标准库
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "kb_output")
OUT_FILE = os.path.join(OUT_DIR, "knowledge_base.jsonl")

CHUNK_TARGET = 420          # 目标 chunk 长度
CHUNK_MAX = 520             # 单 chunk 上限
EFFECTIVE_RE = re.compile(r"生效日期\s*[:：]\s*(\d{4}-\d{2}-\d{2})")
REVOKED_RE = re.compile(r"废止日期\s*[:：]\s*(\d{4}-\d{2}-\d{2})")


def iter_md_files():
    for root, _, files in os.walk(DATA_DIR):
        for f in sorted(files):
            if f.lower().endswith(".md"):
                yield os.path.join(root, f)


def split_long(text, target=CHUNK_TARGET, maxlen=CHUNK_MAX):
    """按句子切分超长文本。"""
    if len(text) <= maxlen:
        return [text] if text.strip() else []
    parts = re.split(r"(?<=[。！？；\.\n])", text)
    chunks, cur = [], ""
    for p in parts:
        if len(cur) + len(p) <= target:
            cur += p
        else:
            if cur.strip():
                chunks.append(cur.strip())
            cur = p if len(p) <= maxlen else p[:maxlen]
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def _flush(buf, source, section, level, effective, revoked, out, counter):
    n = 0
    for c in split_long(buf):
        counter[0] += 1
        out.write(json.dumps({
            "id": f"kb{counter[0]:04d}",
            "content": c,
            "metadata": {
                "source": source,
                "section": section,
                "level": level,
                "effective_date": effective,
                "revoked_date": revoked,
            },
        }, ensure_ascii=False) + "\n")
        n += 1
    return n


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    counter = [0]
    total = 0
    with open(OUT_FILE, "w", encoding="utf-8") as out:
        for path in iter_md_files():
            source = os.path.relpath(path, DATA_DIR)
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            effective = (EFFECTIVE_RE.search(raw).group(1)
                         if EFFECTIVE_RE.search(raw) else None)
            revoked = (REVOKED_RE.search(raw).group(1)
                       if REVOKED_RE.search(raw) else None)

            section, level, buf = "正文", 0, ""
            for line in raw.splitlines():
                h = re.match(r"^(#{1,6})\s+(.*)$", line)
                if h:
                    if buf.strip():
                        total += _flush(buf, source, section, level,
                                        effective, revoked, out, counter)
                    level = len(h.group(1))
                    section = h.group(2).strip()
                    buf = ""
                else:
                    buf += line + "\n"
            if buf.strip():
                total += _flush(buf, source, section, level,
                                effective, revoked, out, counter)
    print(f"已生成 {total} 个 chunk -> {OUT_FILE}")


if __name__ == "__main__":
    build()
