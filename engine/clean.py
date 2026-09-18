# -*- coding: utf-8 -*-
"""输出清洗。

移植并改造自 RebelsPromptEnhancer/__init__.py 的 _clean_output 系列
（原作者 RealRebelAI，同一套思路）。保留其经过实战验证的正则，
另外加了两件事：

  1. 记录"每一步实际剥掉了什么"。旧版只报字符数差，
     诊断面板需要看到被剥掉的具体内容才能判断是模型跑偏还是清洗误伤。

  2. 彻底删掉了旧版的"剥除开头复读"规则。
     旧工具要的是改写，模型抄一遍原话再改写属于冗余，剥掉合理。
     本工具的 SURVIVAL RULE 恰恰要求保留原话——输出以用户输入开头是
     期望行为，剥掉是自相矛盾。实测这条规则会把正确的输出削成
     一个孤零零的逗号，详见 clean_output 里的说明。

  3. 剥离残留标点时连全角一起处理。只写 ASCII 的话，中文标点会活下来，
     表现为结果开头出现 "，" 或 "；"。
"""

import re

# 推理痕迹标记词。命中 >=2 个才认为模型在写思考过程而不是在写提示词。
REASONING_MARKERS = (
    "let me", "i'll ", "i will ", "i need", "i must", "i should",
    "the prompt is", "the user", "key elements", "brainstorm",
    "as per the rules", "according to the rules", "the rules say",
    "let's", "okay so", "first,", "second,", "third,",
    "i can say", "i might", "since this", "so i",
    "thinking process", "analyze the request", "deconstruct",
    "step-by-step", "step by step", "drafting",
)

# 开场白。模型喜欢先说 "Here's the enhanced prompt:" 再给正文。
PREAMBLES = (
    "here's", "here is", "sure,", "sure!", "certainly,", "of course,",
    "okay,", "okay.", "alright,",
    "enhanced prompt:", "expanded prompt:", "prompt:",
    "output:", "answer:", "final prompt:", "final:", "example:",
    "the image shows", "the image depicts", "this image shows",
    "in the image", "i can see", "i see",
)

# 停止序列。只留回合边界标记——模型开始自问自答时截断它。
#
# 旧工具这里还列了 "Thinking Process:" / "Analysis:" / "</think>" 等，
# 意图是"模型开始推理就截断"。实测发现这个意图是错的：
#
#   本机的 Qwen3.5-9B 系列不用  thinking 标签，而是把推理直接写成正文，
#   且永远以 "Thinking Process:" 开头。命中该 stop 会在第 3 个 token 截断，
#   返回空字符串——旧工具在这台机器的模型上输出恒为空。
#
# 而且 /no_think 对它无效（模型会在推理里讨论"/no_think 意味着不要显示
# 内心独白"，然后继续推理）。chat_template_kwargs 这个 llama-cpp-python
# 版本也不支持。
#
# 所以正确做法是：不拦推理，让它写完，由下面的 extract_drafted_content /
# extract_final_paragraph 从推理里把最终答案捞出来。清洗层的存在本来就
# 是为了这个，不需要 stop 帮忙，帮忙反而帮倒忙。
VERBOSE_STOPS = [
    "\n\nUser:", "\n\nAssistant:", "Human:", "\n\nHuman:",
]


def strip_thinking_tags(text):
    """删掉成对的思考标签块。"""
    for pat in (
        r"<think(?:ing)?>.*?</think(?:ing)?>",
        r"<\|thinking\|>.*?<\|/thinking\|>",
        r"\[THINK(?:ING)?\].*?\[/THINK(?:ING)?\]",
    ):
        text = re.sub(pat, "", text, flags=re.DOTALL | re.IGNORECASE)
    return text


def extract_drafted_content(text):
    """模型先推理再起草时，取最后一个起草标记之后的内容。

    返回 (结果, 是否命中)。
    """
    marker_patterns = [
        r"(?:^|\n)\s*\d+\.\s*\*{0,2}\s*Draft(?:ing)?[^\n]*",
        r"(?:^|\n)#{0,3}\s*\*{0,2}\s*Draft(?:ing)?[^\n]*",
        r"(?:^|\n)#{0,3}\s*\*{0,2}\s*(?:Final\s+(?:Prompt|Output|Answer)|Final|Prompt|Output|Result)\s*:?\s*\*{0,2}",
    ]
    last_match_end = -1
    for pat in marker_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            if m.end() > last_match_end:
                last_match_end = m.end()

    if last_match_end > 0:
        candidate = text[last_match_end:].strip()
        candidate = candidate.lstrip(":*-• \t\n")
        candidate = re.sub(
            r"\*{1,2}\s*(?:Subject|Setting|Lighting|Composition|Mood|Style|Environment|Atmosphere|Scene|Background|Foreground|Pose|Camera)\s*:?\s*\*{0,2}\s*",
            "", candidate, flags=re.IGNORECASE,
        )
        candidate = re.sub(r"(?:^|\n)\s*[-*•]\s+", " ", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if len(candidate) > 40:
            return candidate, True
    return text, False


def extract_final_paragraph(text):
    """输出里推理痕迹很重时，从后往前找第一个"不像推理"的段落。"""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) < 2:
        return text, False

    full_lower = text.lower()
    if sum(1 for m in REASONING_MARKERS if m in full_lower) < 2:
        return text, False

    for p in reversed(paragraphs):
        lower = p.lower().lstrip()
        if any(lower.startswith(m) for m in REASONING_MARKERS):
            continue
        lines = p.split("\n")
        bullets = sum(
            1 for l in lines
            if l.strip().startswith(("-", "*", "•", "1.", "2.", "3."))
        )
        if bullets > 0 and bullets >= len(lines) / 2:
            continue
        if len(p) < 60:
            continue
        if sum(1 for m in REASONING_MARKERS if m in lower) >= 2:
            continue
        return p, True
    return text, False


# 剥离残留标点时要连全角一起处理。
# 只写 ASCII 的话中文标点会活下来，表现为结果开头孤零零一个 "，"。
TRIM_CHARS = " \t\r\n,.:;-\"'-—、。，；：！？…·（）【】《》"


def strip_preambles(text):
    """剥掉开场白，最多 3 层。"""
    removed = []
    for _ in range(3):
        lowered = text.lower().lstrip()
        stripped = False
        for p in PREAMBLES:
            if lowered.startswith(p):
                colon = text.find(":")
                newline = text.find("\n")
                if 0 < colon < 60:
                    removed.append(text[:colon + 1])
                    text = text[colon + 1:].strip(TRIM_CHARS)
                elif 0 < newline < 80:
                    removed.append(text[:newline + 1])
                    text = text[newline + 1:].strip(TRIM_CHARS)
                else:
                    removed.append(text[:len(p)])
                    text = text[len(p):].strip(TRIM_CHARS)
                stripped = True
                break
        if not stripped:
            break
    return text, removed


def clean_output(text, original_input=""):
    """完整清洗流水线。

    返回 (干净结果, 诊断信息 dict)。诊断信息给界面的"处理详情"面板用，
    让用户能看到模型原始输出是什么、被动了哪些手脚。
    """
    raw = (text or "").strip()
    diag = {
        "raw": raw,
        "steps": [],
    }

    text = strip_thinking_tags(raw)
    if text != raw:
        diag["steps"].append(("剥除思考标签", len(raw) - len(text)))

    before = text
    text, hit = extract_drafted_content(text)
    if hit:
        diag["steps"].append(("截取起草段", len(before) - len(text)))

    before = text
    text, hit = extract_final_paragraph(text)
    if hit:
        diag["steps"].append(("选取最终段落", len(before) - len(text)))

    before = text
    text, removed = strip_preambles(text)
    if removed:
        diag["steps"].append((f"剥除开场白 {removed[0][:24]!r}", len(before) - len(text)))

    # 这里原本有一条"剥除开头复读"的规则（移植自旧节点包）：
    #   if text.startswith(original_input): text = text[len(inp):]
    #
    # 已经删掉，因为在这个工具里它是反的。
    #
    # 旧工具要的是"改写"，模型把原话抄一遍再改写属于冗余，剥掉合理。
    # 本工具的 SURVIVAL RULE 恰恰强制要求保留原话——模型把用户的输入放在
    # 开头是**期望行为**，剥掉它等于自己打自己。
    #
    # 实测后果（logs/enhance.jsonl 第 20/21/22/29 条）：
    #   原始输出 "一对男女在床上做爱，采用油画风格..."
    #   最终结果 "，采用油画风格..."          ← 原话被删，只剩一个逗号
    # 而且清理后保留率变成 0%，触发了兜底重试，重试又被同样删掉，
    # 于是报"丢失原话且重试未改善"——整条链路被这一个 bug 带偏。

    text = text.strip().strip('"\'').strip()
    diag["final"] = text
    diag["raw_chars"] = len(raw)
    diag["final_chars"] = len(text)
    return text, diag


def clean_chat_output(text):
    """通用对话的轻量清洗，保留对话结构。"""
    text = (text or "").strip()
    text = strip_thinking_tags(text)
    return text.strip()
