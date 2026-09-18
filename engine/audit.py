# -*- coding: utf-8 -*-
"""词溯源审计。

解决的问题：用户抱怨"模型自己丰富提示词，原话被稀释了"——
但光看一段几十词的输出，人眼分不出哪个词是自己写的、哪个是模型加的。

这里把输出切成词，逐个判定来源，分成四类：

    input   来自用户输入
    style   来自用户选中的风格指令
    added   模型自己加的  ← 用户真正想看的
    glue    语法连接词（the/a/of/in...），本身无信息量

判定用的是词表比对，不需要第二次模型调用。

另外算一个关键指标：**原话保留率**——用户输入里的实词有几个进了最终输出。
这个数字直接量化"被稀释"的程度。旧工具没有这个概念，用户只能靠感觉。
"""

import re

# 语法连接词。这些词本身不携带内容，标成 added 只会制造噪声，
# 所以单独归类，渲染时用中性色。
GLUE = {
    "a", "an", "the", "of", "in", "on", "at", "by", "with", "and", "or",
    "to", "from", "as", "is", "are", "was", "were", "be", "being", "been",
    "into", "over", "under", "for", "that", "this", "these", "those",
    "it", "its", "his", "her", "their", "there", "here", "while", "when",
    "standing", "sitting", "looking",  # 高频无信息动作词
}

# 提取词元：英文单词 / 中文单字 / 数字。
# 保持位置信息，因为要按原样重建文本给前端渲染。
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*|[一-鿿]|\d+")

_SUFFIXES = ("ingly", "edly", "ing", "ies", "ied", "es", "ed", "s")


def _stem(word):
    """极简词干化。

    只为了让 "girls"/"girl"、"running"/"run" 能对上，
    不需要语言学意义上的正确性——误判的代价只是着色不准。
    """
    w = word.lower()
    if len(w) <= 3:
        return w
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            base = w[: -len(suf)]
            # "running" -> "runn" -> "run"
            if len(base) >= 2 and base[-1] == base[-2]:
                base = base[:-1]
            return base
    return w


def _tokens(text):
    """返回 [(起始位置, 结束位置, 原词, 词干)]。"""
    out = []
    for m in _TOKEN_RE.finditer(text or ""):
        w = m.group(0)
        out.append((m.start(), m.end(), w, _stem(w)))
    return out


def _vocab(texts):
    """把一组文本转成词干集合。"""
    v = set()
    for t in texts or []:
        for _, _, _, stem in _tokens(t):
            v.add(stem)
    return v


def _is_cjk(tok):
    return bool(re.match(r"[一-鿿]", tok))


def audit(output, user_input, style_texts, budget=None):
    """对输出做词溯源。

    返回 (spans, stats)。spans 是按类别合并后的片段列表，
    每个片段带原文，前端可以直接照着渲染。
    """
    output = output or ""
    user_input = user_input or ""
    style_texts = list(style_texts or [])

    in_vocab = _vocab([user_input])
    st_vocab = _vocab(style_texts)

    toks = _tokens(output)
    if not toks:
        return [], {
            "output_words": 0, "budget": budget, "over_budget": False,
            "input_words": 0, "input_kept": 0, "retention": 1.0,
            "added_words": 0, "style_words": 0, "glue_words": 0,
        }, []

    # --- 逐个词判定来源 ---
    #
    # 顺序要紧：输入词表必须先于风格词表。
    # 用户输入 "cyberpunk girl" 又选了「赛博朋克」风格时，cyberpunk
    # 会同时命中两张表——这时归给 input 才是实话，因为那个词是用户
    # 自己打的。先查风格会把用户的原话算成"模型注入的风格"，正好
    # 把这块面板要回答的问题答反。
    labels = []
    for _, _, w, stem in toks:
        low = w.lower()
        # 中文单字在 GLUE 里没意义（中文没有英文冠词），所以只对英文查
        if not _is_cjk(w) and low in GLUE:
            labels.append("glue")
        elif stem in in_vocab:
            labels.append("input")
        elif stem in st_vocab:
            labels.append("style")
        else:
            labels.append("added")

    # --- 连接词继承邻居的类别，避免满屏中性色 ---
    # 但独立成串的连接词保持 glue。
    for i, lab in enumerate(labels):
        if lab != "glue":
            continue
        prev = next((labels[j] for j in range(i - 1, -1, -1) if labels[j] != "glue"), None)
        nxt = next((labels[j] for j in range(i + 1, len(labels)) if labels[j] != "glue"), None)
        if prev and prev == nxt:
            labels[i] = prev

    # --- 合并连续同类，保留原始文本（含标点空格） ---
    #
    # 片段覆盖的范围是「从本词的起点，到下一个词的起点」——不是「本词的起点到终点」。
    #
    # 这个区别是要紧的：前端把每个片段渲染成独立的 <span>，片段之间不属于任何
    # 片段的字符会被直接丢掉。按 [start, end) 切的话，词与词之间的空格和逗号
    # 正好落在空隙里，界面上 "forest, featuring" 会显示成 "forestfeaturing"，
    # "A still" 显示成 "Astill"。把它一路铺到下一个词的起点，空隙就有了归属
    # （归给前一个词），显示才和原始字符串一致。
    spans = []
    n = len(toks)
    for idx, (start, end, w, _) in enumerate(toks):
        lab = labels[idx]
        seg_start = 0 if idx == 0 else start
        seg_end = toks[idx + 1][0] if idx + 1 < n else len(output)
        if spans and spans[-1]["source"] == lab:
            spans[-1]["_end"] = seg_end
        else:
            spans.append({"source": lab, "_start": seg_start, "_end": seg_end})

    for s in spans:
        s["text"] = output[s["_start"]:s["_end"]]
        s.pop("_start", None)
        s.pop("_end", None)

    # 自检：拼回来的文本必须和原文完全一致。
    # 这条不变量一旦破坏，界面上就会出现词被粘在一起的问题，
    # 所以在这里直接兜住，而不是等用户看出来。
    span_rebuild_failed = False
    if "".join(s["text"] for s in spans) != output:
        span_rebuild_failed = True
        spans = [{"text": output, "source": "glue"}]

    # --- 统计 ---
    content_labels = [l for l in labels if l != "glue"]
    added_words = sum(1 for l in content_labels if l == "added")
    style_words = sum(1 for l in content_labels if l == "style")
    input_words_out = sum(1 for l in content_labels if l == "input")

    # 原话保留率：输入里的实词有多少进了输出
    in_tokens = _tokens(user_input)
    in_content = {stem for _, _, w, stem in in_tokens
                  if not (_is_cjk(w) is False and w.lower() in GLUE)}
    out_vocab_all = {stem for _, _, _, stem in toks}
    kept = in_content & out_vocab_all
    retention = (len(kept) / len(in_content)) if in_content else 1.0

    missing = sorted(in_content - kept)

    out_words = sum(1 for l in labels if l != "glue")

    stats = {
        "output_words": out_words,
        "budget": budget,
        "over_budget": bool(budget and out_words > budget),
        "input_words": len(in_content),
        "input_kept": len(kept),
        "retention": round(retention, 3),
        "added_words": added_words,
        "style_words": style_words,
        "glue_words": len(labels) - len(content_labels),
        "span_rebuild_failed": span_rebuild_failed,
    }
    return spans, stats, missing


def summarize(spans, stats):
    """给界面用的一句话结论。"""
    bits = []
    r = stats.get("retention")
    if r is not None:
        pct = int(round(r * 100))
        if pct >= 90:
            bits.append(f"原话保留 {pct}%，几乎没有丢失")
        elif pct >= 60:
            bits.append(f"原话保留 {pct}%，有部分改写")
        else:
            bits.append(f"原话仅保留 {pct}%，偏离较多")
    a = stats.get("added_words", 0)
    if a == 0:
        bits.append("模型没有自行添加任何内容")
    else:
        bits.append(f"模型自行添加了 {a} 个词")
    if stats.get("over_budget"):
        bits.append(f"超出预算（{stats['output_words']}/{stats['budget']} 词）")
    return "；".join(bits)


if __name__ == "__main__":
    import sys, os, io
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    user_in = "cyberpunk girl by the window"
    styles = ["neon lighting, colored tube glow, wet reflections"]

    cases = [
        ("好的情况（模型守规矩）",
         "cyberpunk girl by the window, neon lighting, wet reflections"),
        ("旧工具那种膨胀",
         "a young woman with intricate cybernetic implants stands by a "
         "rain-streaked window in a neon-drenched megacity apartment, "
         "holographic advertisements flickering across her face, "
         "volumetric fog, cinematic composition, dramatic rim lighting"),
        ("丢掉了原话",
         "a beautiful portrait of a futuristic woman, neon lighting"),
    ]

    for title, out in cases:
        spans, stats, missing = audit(out, user_in, styles, budget=25)
        print("=" * 72)
        print(title)
        print("-" * 72)
        print(out)
        print()
        print("  " + summarize(spans, stats))
        if missing:
            print(f"  输入中未出现: {', '.join(missing)}")
        print(f"  统计: {stats}")
        print()
