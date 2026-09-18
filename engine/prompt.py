# -*- coding: utf-8 -*-
"""提示词组装引擎。

针对旧工具那三个抱怨的设计：

抱怨 1「每次数百词、偏离原意、我的原话被稀释」

    旧工具的 system prompt 写的是 "Rewrite the user's input as a detailed prompt.
    Cover subject, environment, lighting, composition, and mood." —— 这等于命令
    模型把五个维度全部补上，膨胀是必然的，用户的原话在里面根本不是骨架，
    只是被 rewrite 的素材。

    这里的改法是三条同时上：

    (a) 来源规则：用户输入是唯一的内容来源，明确禁止引入任何用户没写的东西。
        不是"尽量贴近原意"这种软话，是"不得引入"这种硬话。

    (b) 白名单：模型唯一被允许新增的东西，是用户自己选中的风格指令。
        这条把"预设风格省打字"和"不许偏离原意"这对矛盾解开了——
        因为风格词是用户主动提供的，不是模型自己发挥的。

    (c) 长度预算：按输入词数算出一个硬上限写进提示词。
        旧版根本没有长度概念，max_tokens=600 是天花板不是目标。

抱怨 3「风格和预制场景不够多」

    风格词作为白名单注入，不是作为"氛围描述"注入。数量由 styles.py 的
    198 条维度词 + local_styles.json 的 3755 条外挂库供给。
    每条注入文本都控制在短句，避免旧版 AESTHETIC_DESCRIPTORS 那种
    一条风格塞 7 个元素的写法。
"""

import os
import re
import sys
import json

# ComfyUI 的 python_embeded 是 isolated 模式（存在 python312._pth），
# 脚本所在目录不会进 sys.path，所以项目内导入之前必须先自己补上。
# 放在模块顶部而不是 __main__ 里——导入发生在模块加载时，晚了就来不及。
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from catalog import formats as fmt_mod

# --------------------------------------------------------------------------
# 强度档位
#
# 决定"允许模型加多少东西"。倍率是输入词数的乘数。
# --------------------------------------------------------------------------
STRENGTHS = {
    "light": {
        "label": "轻",
        "ratio": 1.3,
        "note": "只加连接词和标点，几乎不改写。原话保留度最高。",
        "allowance": (
            "Keep the user's own wording wherever possible. "
            "You may add only small connectives, articles, and punctuation "
            "needed to make it read as a sentence."
        ),
    },
    "standard": {
        "label": "标准",
        "ratio": 1.8,
        "note": "补足必要的语法和风格词，不展开描述。",
        "allowance": (
            "You may smooth the phrasing into natural sentences and weave in the "
            "style directives below. Do not expand the content."
        ),
    },
    "free": {
        "label": "自由",
        "ratio": 3.0,
        "note": "允许较大改写空间，但仍不得引入输入中没有的元素。",
        "allowance": (
            "You may rephrase freely and improve the flow, but the content "
            "constraint above still applies absolutely."
        ),
    },
}

DEFAULT_STRENGTH = "standard"

# 长度预算的上下限（词）。下限保证极短输入也能成型，
# 上限防止长输入被放大成小作文。
MIN_BUDGET = 10
MAX_BUDGET = 150

LANGUAGES = {
    "auto": ("跟随输入", "Write your output in the same language as the user's message."),
    "en": ("强制英文", "Write your output in English regardless of the input language."),
    "zh": ("强制中文", "Write your output in Chinese regardless of the input language."),
}
DEFAULT_LANGUAGE = "auto"


def count_words(text):
    """英文按空格，中文按字。混合文本两者相加。"""
    if not text:
        return 0
    cjk = len(re.findall(r"[一-鿿]", text))
    latin = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", text))
    return cjk + latin


# booru 格式强制带 score/rating 标签，这部分是固定开销，
# 不算进预算的话每次都会误报超长。
BOORU_OVERHEAD = 4


def compute_budget(input_text, strength, style_texts=None, format_id=None):
    """按输入长度和强度算输出词数上限。

    风格词要单独计入。否则会出现"输入 5 词、预算 10 词，但选中的风格词
    本身就有 14 词"的情况——模型只能二选一：要么丢内容，要么丢风格。
    把风格词的长度加到预算上，等于让用户选风格时能直接看到它的字数成本。
    """
    ratio = STRENGTHS.get(strength, STRENGTHS[DEFAULT_STRENGTH])["ratio"]
    n = count_words(input_text)
    base = MIN_BUDGET if n == 0 else max(MIN_BUDGET, min(MAX_BUDGET, int(round(n * ratio))))
    style_words = sum(count_words(t) for t in (style_texts or []))
    overhead = 0
    if format_id and fmt_mod.get(format_id)["family"] == "booru":
        overhead = BOORU_OVERHEAD
    return base + style_words + overhead


# --------------------------------------------------------------------------
# 模式 A：软约束自由改写
# --------------------------------------------------------------------------

_BASE_RULES = """You rewrite image-generation prompts. You do not invent content.

SOURCE RULE — this overrides everything else:
The user's message is the ONLY source of subject matter. Every subject, character, \
object, location, time of day, and action in your output must come from it. \
Do NOT introduce anything the user did not write — no extra people, props, \
buildings, weather, backstory, or events. Do not turn one object into a scene. \
Do not describe what something looks like beyond what the user implied.

SURVIVAL RULE — equally important:
Everything the user did write must still be recognisable in your output. \
If the user named a subject, an action, or a place, all of those must survive. \
Style directives say HOW it looks; they never replace WHAT is depicted. \
Never drop the user's content in order to fit style words in. \
When the style list is long, keep less of it — not less of the user's message. \
If you can only fit one thing, it must be the user's subject.

{allowance}"""

_USER_MSG_SECTION = """THE USER'S MESSAGE — your output depicts this and nothing else:

  "{user_msg}"

That text is the subject. Everything your output depicts must come from it."""

_WHITELIST_HEAD = """STYLE WORDS — the only thing you may add:

{items}

Nothing else may appear in your output that is not in the user's message above."""

_WHITELIST_EMPTY = """WHAT YOU MAY ADD — nothing at all.

No style directives were selected. Your output must contain nothing that is not \
already present in the user's message. You may only fix grammar and punctuation."""

_WHITELIST_NOTE = """These are style descriptors, NOT subjects. They describe how the \
image looks. They are never something to depict, and they never replace the user's \
subject. Weave in only as many as fit — when the list is long, use fewer of these, \
never less of the user's message."""

_LENGTH_HEAD = """LENGTH — hard limit:

The user's message is {n} words. The style directives total {s} words. \
Your output must not exceed {m} words. \
This is a ceiling, not a target. Do not pad. If the input is short, the output \
should be short."""

_SLOT_MODE_RULES = """You extract structured fields from a prompt idea. You do not invent.

Return a JSON object with exactly these keys:

  "subject"     — the main thing being depicted. Use the user's own wording.
  "action"      — what it is doing. Empty string if the user did not say.
  "environment" — where it is. Empty string if the user did not say.
  "style"       — the style directives, verbatim, if any were supplied.

RULES:
- If the user did not state a field, the value MUST be an empty string "".
  Do not guess. Do not fill it in to be helpful.
- Do not add adjectives, objects, or details that are not in the user's message.
- Output the JSON object only. No markdown fence, no explanation."""

_SLOT_MODE_STYLE = """Style directives to place in the "style" field:

{items}"""


def _style_block(style_texts):
    if not style_texts:
        return _WHITELIST_EMPTY
    items = "\n".join(f"  - {t}" for t in style_texts)
    return _WHITELIST_HEAD.format(items=items) + "\n\n" + _WHITELIST_NOTE


def build_system_prompt(mode, format_id, style_texts, strength,
                        input_text, language=DEFAULT_LANGUAGE):
    """组装 system prompt。

    mode: "free" 软约束自由改写 / "slots" 精确槽位填充
    """
    f = fmt_mod.get(format_id)
    strength_cfg = STRENGTHS.get(strength, STRENGTHS[DEFAULT_STRENGTH])
    lang_label, lang_rule = LANGUAGES.get(language, LANGUAGES[DEFAULT_LANGUAGE])

    parts = []

    if mode == "slots":
        # 槽位模式：模型只填 JSON，拼装交给程序，所以不需要长度和格式指令。
        parts.append(_SLOT_MODE_RULES)
        if style_texts:
            parts.append(_SLOT_MODE_STYLE.format(items="\n".join(
                f"  - {t}" for t in style_texts)))
        parts.append(f"STYLE DIRECTIVES:\n{f['inject']}")
        parts.append(lang_rule)
    else:
        parts.append(_BASE_RULES.format(allowance=strength_cfg["allowance"]))
        # 用户的输入要原样引在风格列表之前。
        #
        # 实测教训：只在 user 回合给出输入时，遇到较长的风格串，模型会把
        # 风格列表本身当成要处理的内容，输出变成"把风格词改写成句子"，
        # 用户的输入整个丢失（保留率 0%）。把它引到 system prompt 里、
        # 且排在风格段落之前，模型才把它当成主体而不是配角。
        parts.append(_USER_MSG_SECTION.format(user_msg=input_text))
        parts.append(_style_block(style_texts))
        n = count_words(input_text)
        s = sum(count_words(t) for t in style_texts)
        m = compute_budget(input_text, strength, style_texts, format_id)
        parts.append(_LENGTH_HEAD.format(n=n, s=s, m=m))
        parts.append(f"OUTPUT FORMAT:\n{f['inject']}")
        parts.append(lang_rule)
        parts.append(
            "OUTPUT:\nReturn only the finished prompt. No preamble, no explanation, "
            "no headings, no markdown, no surrounding quotes, no thinking."
        )

    return "\n\n".join(parts)


# --------------------------------------------------------------------------
# 模式 B：槽位拼装
# --------------------------------------------------------------------------

# 各语法族的拼装模板。槽位模式最有价值的地方在这里——
# 模型只负责填词，长什么样由模板决定，所以不可能膨胀。
# 环境槽位可能自带介词（"by the window"），这时不能再补一个 "in"，
# 否则拼出 "in by the window"。覆盖面要够宽，介词表写全。
_ENV_PREPS = (
    "in ", "at ", "on ", "by ", "near ", "under ", "over ", "behind ",
    "beside ", "inside ", "outside ", "within ", "against ", "beneath ",
    "above ", "below ", "across ", "among ", "around ", "through ",
    "between ", "amid ", "upon ", "along ",
)


def _assemble_prose(slots, style_texts):
    bits = []
    subj = slots.get("subject", "").strip()
    act = slots.get("action", "").strip()
    env = slots.get("environment", "").strip()

    if subj and act:
        bits.append(f"{subj} {act}")
    elif subj:
        bits.append(subj)
    elif act:
        bits.append(act)

    if env:
        lower = env.lower()
        if lower.startswith(_ENV_PREPS):
            bits.append(env)
        else:
            bits.append(f"in {env}")

    body = ", ".join(b for b in bits if b)
    style = ", ".join(style_texts)
    if body and style:
        return f"{body}, {style}"
    return body or style


def _assemble_tags(slots, style_texts):
    bits = []
    for key in ("subject", "action", "environment"):
        v = slots.get(key, "").strip()
        if v:
            bits.append(v)
    bits.extend(style_texts)
    return ", ".join(bits)


def _assemble_booru(slots, style_texts, rating="rating_safe"):
    """booru 族要带 score 前缀和 rating 标签。"""
    bits = ["score_9", "score_8_up", "score_7_up", rating]
    for key in ("subject", "action", "environment"):
        v = slots.get(key, "").strip()
        if v:
            # booru 惯例：多词用下划线
            bits.append(re.sub(r"\s+", "_", v.lower()))
    bits.extend(style_texts)
    return ", ".join(bits)


def assemble_from_slots(slots, format_id, style_texts, rating="rating_safe"):
    """把模型填的槽位拼成最终提示词。

    这里是程序侧拼装，不走模型，所以输出结构是确定的。
    """
    f = fmt_mod.get(format_id)
    family = f["family"]
    if family == "tags":
        return _assemble_tags(slots, style_texts)
    if family == "booru":
        return _assemble_booru(slots, style_texts, rating)
    return _assemble_prose(slots, style_texts)


_SLOT_KEYS = ("subject", "action", "environment", "style")


def parse_slots(raw):
    """从模型输出里抠出 JSON。

    模型可能套 markdown 围栏、可能前后带废话，所以做多级兜底。
    解析失败返回 None，调用方据此回退到自由模式。
    """
    if not raw:
        return None
    text = raw.strip()

    # 去 markdown 围栏
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    candidates = [text]
    # 取第一个 { 到最后一个 } 之间的内容
    i, j = text.find("{"), text.rfind("}")
    if 0 <= i < j:
        candidates.append(text[i:j + 1])

    for cand in candidates:
        try:
            obj = json.loads(cand)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        slots = {}
        for k in _SLOT_KEYS:
            v = obj.get(k, "")
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            slots[k] = str(v or "").strip()
        # 至少要有个主体，否则认为是无效解析
        if slots.get("subject"):
            return slots
    return None


# --------------------------------------------------------------------------

def options():
    """给前端的可选项。"""
    return {
        "strengths": [
            {"id": k, "label": v["label"], "note": v["note"]}
            for k, v in STRENGTHS.items()
        ],
        "languages": [
            {"id": k, "label": v[0]} for k, v in LANGUAGES.items()
        ],
        "default_strength": DEFAULT_STRENGTH,
        "default_language": DEFAULT_LANGUAGE,
        "budget_range": [MIN_BUDGET, MAX_BUDGET],
    }


if __name__ == "__main__":
    import sys, os, io
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    demo_in = "cyberpunk girl by the window"
    styles = [
        "oil painting, visible impasto brushwork, painterly texture",
        "neon lighting, colored tube glow, wet reflections",
    ]

    print("=" * 70)
    print("模式 A · 软约束自由改写")
    print("=" * 70)
    print(build_system_prompt("free", "flux", styles, "light", demo_in))
    print()
    print(f"输入 {count_words(demo_in)} 词 -> 预算 "
          f"{compute_budget(demo_in, 'light')} 词")
    for s in ("light", "standard", "free"):
        print(f"  强度 {STRENGTHS[s]['label']}: {compute_budget(demo_in, s)} 词")

    print()
    print("=" * 70)
    print("模式 B · 槽位填充")
    print("=" * 70)
    print(build_system_prompt("slots", "pony", styles, "standard", demo_in))
    print()
    slots = {"subject": "cyberpunk girl", "action": "standing",
             "environment": "by the window", "style": ""}
    for fid in ("flux", "sdxl", "pony"):
        print(f"  {fmt_mod.get(fid)['zh']:<22} -> "
              f"{assemble_from_slots(slots, fid, styles)}")
