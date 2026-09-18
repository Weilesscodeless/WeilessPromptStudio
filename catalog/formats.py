# -*- coding: utf-8 -*-
"""目标模型格式。

跟旧节点包相比的两处改动：

  1. 补上 encoder 字段。用户选格式时最常问的是"我这个模型该选哪个"，
     答案取决于文本编码器而不是 UNet，所以直接把编码器写在选项里。

  2. 只保留"语法约束"，把"内容清单"降级为可选提示。
     旧版的 format 指令里混着大量 "Cover subject, environment, lighting,
     composition, and mood" 这类内容要求，等于命令模型把五个维度都补上，
     是膨胀的直接来源。这里语法写死，内容不强制。

family 字段用于精确模式（槽位填充）挑选拼装模板：
  prose  自然语言散文
  tags   逗号标签 + 括号权重
  booru  booru 风格标签 + score
"""

MODEL_FORMATS = [
    {
        "id": "flux",
        "zh": "Flux / Chroma",
        "en": "Flux / Chroma",
        "family": "prose",
        "encoder": "T5-XXL + CLIP-L",
        "note": "语言模型编码器，吃自然语言。无 CFG，负向提示词基本无效，也别写质量词。",
        "inject": (
            "Write flowing natural-language prose in complete sentences. "
            "No comma-separated tag lists. No parenthesis weights. "
            "No quality boosters such as 'masterpiece', 'best quality', or '8k'. "
            "Order the description so the main subject comes first."
        ),
    },
    {
        "id": "zimage",
        "zh": "Z-Image / Lumina-2",
        "en": "Z-Image / Lumina-2",
        "family": "prose",
        "encoder": "LLM 系（Qwen / Gemma 自回归模型）",
        "note": "编码器本身就是语言模型，能吃复杂从句和属性绑定关系。",
        "inject": (
            "Write descriptive natural-language prose suitable for an LLM text encoder. "
            "Complex sentences are fine. Be concrete and specific rather than ornate. "
            "No tag syntax, no weights."
        ),
    },
    {
        "id": "hidream",
        "zh": "HiDream",
        "en": "HiDream",
        "family": "prose",
        "encoder": "Llama-3.1-8B + T5-XXL + CLIP-L + bigG（四路）",
        "note": "多编码器分工：语言模型管长句composition，CLIP 管具象视觉词。",
        "inject": (
            "Write flowing natural language that weaves in concrete photographic and "
            "material descriptors — lighting type, lens feel, surface texture. "
            "Keep it prose, not a tag list. No weight syntax."
        ),
    },
    {
        "id": "sdxl",
        "zh": "SDXL",
        "en": "SDXL",
        "family": "tags",
        "encoder": "CLIP ViT-L + OpenCLIP ViT-bigG",
        "note": "CLIP 对语序理解弱，靠堆标签和加权传递重点。用括号权重。",
        "inject": (
            "Format as a comma-separated list of short descriptive tags. "
            "Use parenthesis weight syntax for emphasis, e.g. (cinematic lighting:1.2). "
            "Keep each tag short. No sentences, no filler words."
        ),
    },
    {
        "id": "sd15",
        "zh": "SD 1.5",
        "en": "SD 1.5",
        "family": "tags",
        "encoder": "CLIP ViT-L/14",
        "note": "同上，标签要更短更直接。",
        "inject": (
            "Format as a comma-separated list of short, direct descriptive tags. "
            "Use parenthesis weight syntax for emphasis. "
            "Keep every tag under four words. No sentences."
        ),
    },
    {
        "id": "pony",
        "zh": "Pony / Illustrious",
        "en": "Pony / Illustrious",
        "family": "booru",
        "encoder": "CLIP ViT-L + OpenCLIP ViT-bigG（同 SDXL，差异在训练数据）",
        "note": "架构跟 SDXL 一样，区别只在微调数据是 booru 图库，所以要 booru 标签法。",
        "inject": (
            "Format as comma-separated booru-style tags. "
            "Begin with score tags: score_9, score_8_up, score_7_up. "
            "Then choose one rating tag: rating_safe, rating_questionable, or rating_explicit. "
            "Use underscores for multi-word tags, e.g. long_hair, blue_eyes. "
            "Use a SEPARATE tag for each distinct concept — do not merge the whole "
            "description into one long underscored tag. "
            "Do not use parenthesis weight syntax."
        ),
    },
    {
        "id": "ltx",
        "zh": "LTX Video",
        "en": "LTX Video",
        "family": "prose",
        "encoder": "T5-XXL",
        "note": "视频模型。运动要写清楚谁在动、怎么动。",
        "inject": (
            "Write a video shot description in natural-language sentences. "
            "State what moves and how, plus camera movement if relevant. "
            "No tag syntax."
        ),
    },
    {
        "id": "hunyuan_wan",
        "zh": "Hunyuan / Wan Video",
        "en": "Hunyuan / Wan Video",
        "family": "prose",
        "encoder": "Hunyuan: MLLM + CLIP；Wan: umT5",
        "note": "中文提示词也能吃（umT5 多语言）。",
        "inject": (
            "Write a cinematic video description in natural-language sentences. "
            "Cover camera movement, subject action, and environmental motion if they "
            "are present in the input. No tag syntax."
        ),
    },
    {
        "id": "minimax_h3",
        "zh": "MiniMax H3（海螺）",
        "en": "MiniMax H3",
        "family": "prose",
        "encoder": "Qwen3-VL-32B（多模态）",
        "note": "全模态：一次生成视频 + 原生立体声。需要同时描述画面和声音。",
        "inject": (
            "Write a single flowing natural-language description for MiniMax H3. "
            "H3 generates video and synchronized audio in one pass, so describe both "
            "the visuals and the soundscape — dialogue, ambient sound, foley, music — "
            "but only if the input implies them. "
            "Use coherent sentences with explicit temporal flow. No tag syntax, no weights."
        ),
    },
    {
        "id": "universal",
        "zh": "通用自然语言",
        "en": "Universal natural language",
        "family": "prose",
        "encoder": "任意",
        "note": "拿不准选哪个就用这个。",
        "inject": (
            "Write a flowing natural-language description in concrete visual detail. "
            "No tags, no weights."
        ),
    },
]

_BY_ID = {f["id"]: f for f in MODEL_FORMATS}

DEFAULT_FORMAT = "universal"


def get(format_id):
    return _BY_ID.get(format_id) or _BY_ID[DEFAULT_FORMAT]


def catalog():
    """给前端用的格式列表（不含 inject）。"""
    return [
        {
            "id": f["id"],
            "zh": f["zh"],
            "en": f["en"],
            "family": f["family"],
            "encoder": f["encoder"],
            "note": f["note"],
        }
        for f in MODEL_FORMATS
    ]


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print(f"格式 {len(MODEL_FORMATS)} 种")
    for f in MODEL_FORMATS:
        print(f"  {f['zh']:<24} [{f['family']:<5}] {f['encoder']}")
