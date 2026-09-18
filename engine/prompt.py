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
    "auto": ("自动（按模型）", "Write your output in the same language as the user's message."),
    "en": ("强制英文", "Write your output in English regardless of the input language."),
    "zh": ("强制中文", "Write your output in Chinese regardless of the input language."),
}
DEFAULT_LANGUAGE = "auto"

_CJK_RE = re.compile(r"[一-鿿]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def detect_language(text):
    """判断文本语种。只区分中/英/混合，够用了。"""
    if not text:
        return "unknown"
    cjk = len(_CJK_RE.findall(text))
    latin = len(_LATIN_RE.findall(text))
    if cjk == 0 and latin == 0:
        return "unknown"
    if cjk == 0:
        return "en"
    if latin == 0:
        return "zh"
    # 哪个占多数算哪个（中文一个字信息量大，所以给个偏置）
    return "zh" if cjk * 2 >= latin else "en"


def resolve_language(requested, format_id, input_text):
    """决定实际输出语言。

    这是"适配不支持中文的模型"的核心。

    有些编码器只认英文：CLIP（SD1.5/SDXL/Pony）、T5-XXL（Flux/LTX/HiDream）
    都是在英文语料上训的，喂中文等于喂噪声——不是效果差一点，是几乎不生效。
    用户用中文写提示词、又选了这类模型时，工具必须自动改成英文，
    并且在提示词里明确要求"翻译"，而不能只说"用英文写"。

    只写"Write in English"不够：模型常会把中文原样留着再补几句英文。
    必须点明"把含义翻译过去，不要保留任何非英文字"。

    format 的 lang 字段标了编码器能力：en 只认英文，multi 支持中文。
    """
    f = fmt_mod.get(format_id)
    cap = f.get("lang", "en")
    in_lang = detect_language(input_text)

    if requested == "en":
        return "en", in_lang, False
    if requested == "zh":
        # 用户明确要中文，即使编码器不吃也照办（可能只是拿去做别的用途），
        # 但要标记出来供上层提示风险。
        return "zh", in_lang, False
    # auto：跟随编码器能力
    if cap == "en":
        if in_lang in ("zh", "mixed"):
            # 需要翻译
            return "en", in_lang, True
        return "en", in_lang, False
    return "auto", in_lang, False


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
    if format_id:
        f = fmt_mod.get(format_id)
        if f["family"] == "booru":
            overhead += BOORU_OVERHEAD
        # 有些格式天生要更多词：H3 要同时描述画面和声音，视频类要写运动。
        # 不加这部分的话，这些格式每次都会误报超长。
        overhead += f.get("budget_bonus", 0)

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
  "style"       — every style word from the list at the bottom of this prompt,
                  translated into the output language. Empty string if that list
                  is absent.

RULES:
- If the user did not state a field, the value MUST be an empty string "".
  Do not guess. Do not fill it in to be helpful.
- Do not add adjectives, objects, or details that are not in the user's message.
- The style words describe HOW the image looks, not WHAT is depicted. Never
  move subject matter into the "style" field.
- Output the JSON object only. No markdown fence, no explanation."""

_SLOT_MODE_STYLE = """STYLE WORDS — put every one of these into the "style" field, \
TRANSLATED into {lang_name}. Do not copy them in English:

{items}"""

# 目标语种是中文时的追加强调。
# 通用规则模型遵守得时好时坏（实测同一输入同一参数，有时翻译有时照抄英文），
# 所以在列表下面再钉一句，把失败模式直接点名。
_SLOT_STYLE_ZH_HARD = """The style words above are English text. Your "style" field \
must contain Chinese words with the same meaning. An output whose "style" field is \
English is WRONG."""

# 翻译场景专用。只写 "Write in English" 不够——模型会把中文原样留着
# 再补几句英文，结果送进只认英文的编码器还是噪声。必须点明"不要保留
# 任何非英文字符"。
_TRANSLATE_RULE = """TRANSLATION — the user wrote in {src}, your output must be English:

Translate the MEANING of the user's message into English. Do NOT leave any \
non-English characters in your output — not the user's original words, not \
names, nothing. The style words listed below are already English; use them as \
written. Every concept from the user's message must survive the translation."""

# 跟随输入语种时的规则。
#
# 不能只写 "use the same language as the user"。实测：风格词全是英文，用户
# 的中文输入又短，英文风格词在提示词里占压倒性比重，模型会整个漂成英文
# ——输入"一对男女在做爱"配几个英文风格词，输出会是
# "establishing wide shot ... a couple making love under ..."。
# 所以必须点破：风格词是英文，不代表输出要用英文。
_LANG_ZH = """LANGUAGE — your entire output must be in Chinese:

The user wrote in Chinese, so EVERY word of your output must be Chinese, \
including the parts that describe style. The style words listed below happen \
to be written in English — translate their meaning into Chinese as you weave \
them in. Do NOT switch to English just because those words are English. \
The style words are not the content; they do not set the language."""

_LANG_EN = """LANGUAGE — your entire output must be in English:

Write every word in English. If the user wrote in another language, translate \
their meaning rather than keeping their original wording."""

_LANG_GENERIC = """LANGUAGE — match the user's language:

Write your output in the same language as the user's message. The style words \
listed below are in English for convenience; that does not mean your output \
should be in English."""


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

    # 语言按编码器能力解析。选到只认英文的模型而输入是中文时，
    # 这里会转成强制英文 + 翻译指令——见 resolve_language 的说明。
    eff_lang, in_lang, translating = resolve_language(language, format_id, input_text)
    if translating:
        lang_rule = _TRANSLATE_RULE.format(
            src="Chinese" if in_lang == "zh" else "a mix of Chinese and English")
    elif eff_lang == "zh":
        lang_rule = _LANG_ZH
    elif eff_lang == "en":
        lang_rule = _LANG_EN
    elif in_lang == "zh":
        lang_rule = _LANG_ZH
    elif in_lang == "en":
        lang_rule = _LANG_EN
    else:
        lang_rule = _LANG_GENERIC

    parts = []

    if mode == "slots":
        # 槽位模式不把格式指令给模型。
        #
        # 拼装由程序做，格式跟模型无关，给了没有收益；反而出过事：
        # Pony 的格式指令里写着 "Begin with score tags: score_9, score_8_up,
        # score_7_up..."，模型把它当成风格词抄进 style 字段，拼装时程序又
        # 自动加一遍，最终输出里 score 标签出现两次。
        parts.append(_SLOT_MODE_RULES)
        parts.append(lang_rule)          # 语言规则要显眼，排在风格列表前面
        if style_texts:
            want_zh = lang_rule in (_LANG_ZH, _TRANSLATE_RULE) or in_lang == "zh"
            head = _SLOT_MODE_STYLE.format(
                lang_name="Chinese" if want_zh else "English",
                items="\n".join(f"  - {t}" for t in style_texts),
            )
            if want_zh:
                head += "\n\n" + _SLOT_STYLE_ZH_HARD
            parts.append(head)
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
        # 环境词已经被主体或动作包含了就别重复拼。
        # 实测模型会把"在沙发上睡觉"填进 action、把"沙发上"填进 environment，
        # 拼出来就是「一只猫 在沙发上睡觉, 沙发上」。
        head = " ".join(bits).lower()
        if env.lower() not in head:
            lower = env.lower()
            # 中文环境词不能补英文介词。实测"沙发上"会被拼成 "in 沙发上"。
            # 中文靠语序和"在/于"表达方位，不需要前置介词。
            if lower.startswith(_ENV_PREPS) or _CJK_RE.search(env):
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

    风格部分优先用模型填的 style 字段，而不是库里存的英文原文。
    库里存的都是英文，直接用会让中文输出里混进一大段英文——实测槽位模式
    下中文输入会拼出「一只猫 在沙发上睡觉, oil painting, visible impasto
    brushwork...」这种半中半英。模型已经在 style 字段里按目标语言翻译好了，
    用它的结果。只在它返回空时才回退到原文。
    """
    f = fmt_mod.get(format_id)
    family = f["family"]

    model_style = (slots.get("style") or "").strip()
    styles = [model_style] if model_style else list(style_texts or [])

    if family == "tags":
        return _assemble_tags(slots, styles)
    if family == "booru":
        return _assemble_booru(slots, styles, rating)
    return _assemble_prose(slots, styles)


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
