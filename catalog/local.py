# -*- coding: utf-8 -*-
"""外挂风格库的读取。

数据由 tools/import_local_styles.py 从本机 ComfyUI 生态导入，
文件不存在时静默返回空——工具本身不依赖它，只是有它会更丰富。
"""

import os
import json

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "local_styles.json")

_cache = None


def load():
    global _cache
    if _cache is not None:
        return _cache
    if not os.path.isfile(PATH):
        _cache = {"groups": [], "total": 0, "notes": []}
        return _cache
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    except Exception:
        _cache = {"groups": [], "total": 0, "notes": []}
    return _cache


def catalog():
    """给前端的精简目录：只带 id/名称/词数，不带正文（正文按需取）。"""
    data = load()
    return [
        {
            "key": g["key"],
            "label": g["label"],
            "count": len(g["items"]),
            "items": [
                {"i": i, "zh": it["zh"], "words": it["words"]}
                for i, it in enumerate(g["items"])
            ],
        }
        for g in data.get("groups", [])
    ]


def get_text(group_key, index):
    """按组和序号取一条的风格文本。"""
    for g in load().get("groups", []):
        if g["key"] == group_key:
            items = g["items"]
            if 0 <= index < len(items):
                return items[index]["text"]
    return None


def stats():
    d = load()
    return {
        "groups": len(d.get("groups", [])),
        "total": d.get("total", 0),
        "notes": d.get("notes", []),
    }
