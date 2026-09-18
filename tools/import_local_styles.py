# -*- coding: utf-8 -*-
"""把本机 ComfyUI 生态里已有的风格库导入成本工具的「外挂风格包」。

为什么要先清洗再导入：
    这些库的条目普遍混着大量质量样板词。最极端的例子是 Apt_Preset 的
    「通用-写实」，风格部分 30 个词全是 (masterpiece:1.3), (best quality:1.3),
    8k resolution, RAW photo, photographic masterpiece, hyper-realistic...
    真正的风格信息是零。原样导入 = 把旧工具的膨胀问题搬进新工具。

    所以这里做一遍剥离：去掉质量词和权重语法，只留风格内核，
    并给每条标出清洗后的词数，让用户在界面上能看见成本。

输出：catalog/local_styles.json

用法：
    python tools/import_local_styles.py
"""

import json
import os
import re
import sys
import csv

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_PATH = os.path.join(ROOT, "catalog", "local_styles.json")

# 本机 ComfyUI 整合包位置。其它机器上跑就改这里，或用 --comfy 指定。
DEFAULT_COMFY = r"G:\ComfyUI_Mie_V34\ComfyUI"


# --------------------------------------------------------------------------
# 质量样板词表
#
# 只剥离"纯粹表达生成质量、不携带任何视觉风格信息"的词。
# 刻意不剥离 octane render / unreal engine / v-ray 这类——它们是渲染器名，
# 属于真实的风格信息（选了就是 3D 渲染质感）。
# --------------------------------------------------------------------------
BOILERPLATE = {
    # 质量等级
    "masterpiece", "best quality", "high quality", "highest quality",
    "ultra quality", "normal quality", "worst quality", "low quality",
    "bad quality", "top quality", "good quality", "great quality",
    "ultra-high quality", "super quality", "amazing quality", "perfect quality",
    # 分辨率 / 清晰度
    "high resolution", "ultra high resolution", "ultra-high resolution",
    "highest resolution", "8k", "4k", "16k", "2k", "1080p", "uhd",
    "ultra hd", "highres", "absurdres", "high resolution", "resolution",
    "8k resolution", "4k resolution", "超高分辨率", "高清",
    # 细节
    "highly detailed", "ultra detailed", "ultra-detailed", "extremely detailed",
    "super detailed", "very detailed", "high detail", "intricate details",
    "lots of detail", "insane detail", "extreme detail", "detailed",
    "crisp details", "sharp details", "fine details", "rich details",
    "maximum detail", "incredible detail", "超细节", "细节丰富",
    # 写实类样板（注意：photorealistic 本身是风格，但在这类库中
    # 几乎总是和质量词一起出现，且用户在维度库里能单独选「摄影」，
    # 所以这里剥掉，由维度库负责写实风格）
    "raw photo", "photographic masterpiece", "true-to-life photo realism",
    "true-to-life", "ultra-realistic", "ultra realistic", "hyper-realistic",
    "hyperrealistic", "super realistic", "super-realistic", "photo-realistic",
    "photorealistic", "realistic photo", "hyper realistic", "extremely realistic",
    # 通用夸奖
    "best", "perfect", "award winning", "award-winning", "professional",
    "masterwork", "top tier", "exceptional", "stunning", "beautiful",
    "gorgeous", "flawless", "impeccable", "premium", "epic",
    # 平台引流词
    "trending on artstation", "artstation", "deviantart", "pixiv",
    "featured on artstation", "concept art award",
    "trending on cg society", "cg society",
    # 解剖/质量修正样板
    "perfect anatomy", "perfect proportions", "detailed face",
    "beautiful detailed eyes", "detailed skin", "detailed background",
    "sharp focus", "shallow depth of field", "professional lighting",
    "studio lighting", "cinematic lighting", "volumetric lighting",
    "dramatic lighting", "beautiful lighting", "great composition",
    "professional photography", "professional photo", "award winning photo",
}

# 这些词单独出现时是"权重语法残留"，剥掉括号和数字后如果命中样板就丢
WEIGHT_RE = re.compile(r"^\s*\(+([^():]*?)(?::[\d.]+)?\)+\s*$")
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_]*prompt[a-zA-Z_]*\}", re.IGNORECASE)
NUMERIC_WEIGHT_RE = re.compile(r"^\(+.*?:[\d.]+\)+$")

# 包裹式模板的残骸处理。
# 很多库的条目形如 "a cinematic photograph of {prompt}" —— 占位符在末尾，
# 剥掉后剩 "a cinematic photograph of"，是半句话不是风格短语。
# 去掉冠词和悬空介词后还原成可用的 "cinematic photograph"。
LEAD_ARTICLE_RE = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)
TRAIL_PREP_RE = re.compile(
    r"\s+(?:of|with|in|on|at|by|for|to|from|as|into|over|under|about|"
    r"featuring|showing|depicting)\s*$",
    re.IGNORECASE,
)
# 占位符剥掉后可能留下的孤立标点
STRAY_PUNCT_RE = re.compile(r"\s*[.,;]\s*(?=[.,;])")


def clean_style(text):
    """剥离质量样板，返回清洗后的风格文本。

    返回空字符串表示这条除了样板词以外什么都没有（应当丢弃）。
    """
    if not text:
        return ""
    # 占位符换成逗号，这样 "a photo of {prompt}, grainy" 会拆成
    # "a photo of" 和 "grainy" 两段，半句模板不会被粘进结果
    text = PLACEHOLDER_RE.sub(" , ", text)

    # 先整体去一层权重语法，再逐段判断
    parts = re.split(r"[,\n;]", text)
    kept = []
    for raw in parts:
        frag = raw.strip().strip(".").strip()
        if not frag:
            continue

        # 去掉外层括号和 :数字 权重，拿到"裸词"用于判定
        m = WEIGHT_RE.match(frag)
        bare = (m.group(1) if m else frag).strip().lower()
        bare = re.sub(r"\s+", " ", bare)
        # 去掉开头的 BREAK / AND 之类连接词
        bare = re.sub(r"^(break|and|add|with)\s+", "", bare)

        # 包裹式模板残骸：剥掉冠词和悬空介词
        bare = LEAD_ARTICLE_RE.sub("", bare)
        for _ in range(2):  # "a photo of the" 这类要剥两轮
            new = TRAIL_PREP_RE.sub("", bare).strip()
            if new == bare:
                break
            bare = new
        bare = LEAD_ARTICLE_RE.sub("", bare).strip()

        if not bare:
            continue
        if bare in BOILERPLATE:
            continue
        # 纯数字权重残留
        if re.fullmatch(r"[\d.:()\s]+", bare):
            continue
        # 极短的噪声片段
        if len(bare) <= 2:
            continue
        # 剥完只剩冠词/介词的空壳
        if bare in ("a", "an", "the", "of", "with", "and", "in", "on", "at"):
            continue

        kept.append(bare)

    # 去重（保持顺序）
    seen = set()
    out = []
    for k in kept:
        if k not in seen:
            seen.add(k)
            out.append(k)
    joined = ", ".join(out)
    joined = STRAY_PUNCT_RE.sub("", joined)
    return joined.strip(" ,.;")


def word_count(text):
    return len([w for w in re.split(r"[\s,]+", text) if w])


# --------------------------------------------------------------------------
# 各来源的读取器
# --------------------------------------------------------------------------

def read_apt_csv(path):
    """Apt_Preset 的 styles*.csv：三列 名称,正向,负向。"""
    items = []
    if not os.path.isfile(path):
        return items
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            name, positive = row[0].strip(), row[1]
            if not name:
                continue
            items.append({"name": name, "text": positive})
    return items


def read_style_json(path):
    """Fooocus / SDXL styles JSON：数组，元素含 name + prompt 字段。

    字段名在不同合集里有出入，所以逐个兜底尝试。
    """
    items = []
    if not os.path.isfile(path):
        return items
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return items
    if not isinstance(data, list):
        return items

    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("style") or entry.get("title")
        text = (entry.get("prompt") or entry.get("positive")
                or entry.get("positive_prompt") or "")
        if not name:
            continue
        items.append({"name": str(name), "text": str(text)})
    return items


def read_wildcard_dir(path):
    """通配符词库：每个 .txt 一行一条，文件名即分类。"""
    groups = []
    if not os.path.isdir(path):
        return groups
    for fname in sorted(os.listdir(path)):
        if not fname.lower().endswith(".txt"):
            continue
        fpath = os.path.join(path, fname)
        lines = []
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    lines.append({"name": line, "text": line})
        except Exception:
            continue
        if lines:
            groups.append({"key": fname[:-4], "items": lines})
    return groups


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

def build(comfy_dir):
    c = lambda *p: os.path.join(comfy_dir, "custom_nodes", *p)
    groups = []
    source_notes = []

    def add_group(key, label, source, raw_items, keep_long=False):
        """清洗一组并去重，返回实际入库的条数。"""
        cleaned = []
        seen = set()
        dropped_empty = 0
        for it in raw_items:
            text = clean_style(it["text"])
            if not text:
                dropped_empty += 1
                continue
            wc = word_count(text)
            if wc > 30 and not keep_long:
                continue
            low = text.lower()
            if low in seen:
                continue
            seen.add(low)
            cleaned.append({
                "zh": it["name"],
                "text": text,
                "words": wc,
            })
        if cleaned:
            groups.append({
                "key": key,
                "label": label,
                "source": source,
                "items": cleaned,
            })
        source_notes.append(
            f"{label}: 原始 {len(raw_items)} 条 → 入库 {len(cleaned)} 条"
            f"（剥离后为空 {dropped_empty} 条，重复/过长丢弃 "
            f"{len(raw_items) - dropped_empty - len(cleaned)} 条）"
        )
        return len(cleaned)

    # --- 1. Apt_Preset 风格 CSV（中文名，最贴合用户需求） ---
    apt_items = []
    for fn in ("styles.csv", "stylesCN.csv", "stylesEN.csv"):
        apt_items += read_apt_csv(c("ComfyUI-Apt_Preset", "csv", fn))
    add_group("apt", "Apt 预设风格", "ComfyUI-Apt_Preset/csv/styles*.csv", apt_items)

    # --- 2. Fooocus 风格库 ---
    add_group(
        "fooocus", "Fooocus 风格",
        "ComfyUI-Easy-Use/resources/fooocus_styles.json",
        read_style_json(c("ComfyUI-Easy-Use", "resources", "fooocus_styles.json")),
    )

    # --- 3. ComfyUI_Lam 的 SDXL 风格合集 ---
    lam_items = []
    lam_dir = c("ComfyUI_Lam", "styles")
    if os.path.isdir(lam_dir):
        for fn in sorted(os.listdir(lam_dir)):
            if fn.endswith(".json"):
                lam_items += read_style_json(os.path.join(lam_dir, fn))
    add_group("sdxl_lam", "SDXL 风格合集 (Lam)",
              "ComfyUI_Lam/styles/*.json", lam_items)

    # --- 4. art-venture 的 SDXL styler ---
    av_items = []
    av_dir = c("comfyui-art-venture", "modules", "sdxl_prompt_styler")
    if os.path.isdir(av_dir):
        for fn in sorted(os.listdir(av_dir)):
            if fn.endswith(".json"):
                av_items += read_style_json(os.path.join(av_dir, fn))
    add_group("sdxl_av", "SDXL 风格合集 (art-venture)",
              "comfyui-art-venture/modules/sdxl_prompt_styler/*.json", av_items)

    # --- 5. 通配符词库：每类单独成组 ---
    wc_groups = read_wildcard_dir(c("ComfyUI-Apt_Preset", "wildcards"))
    for g in wc_groups:
        add_group(
            f"wc_{g['key']}", f"通配 · {g['key']}",
            f"ComfyUI-Apt_Preset/wildcards/{g['key']}.txt",
            g["items"],
        )

    total = sum(len(g["items"]) for g in groups)
    return {
        "comfy_dir": comfy_dir,
        "groups": groups,
        "total": total,
        "notes": source_notes,
    }


def main():
    comfy = DEFAULT_COMFY
    if "--comfy" in sys.argv:
        idx = sys.argv.index("--comfy")
        if idx + 1 < len(sys.argv):
            comfy = sys.argv[idx + 1]

    if not os.path.isdir(comfy):
        print(f"[错误] 找不到 ComfyUI 目录: {comfy}")
        print(f"       用 --comfy <路径> 指定，或改脚本顶部的 DEFAULT_COMFY")
        return 1

    print(f"从 {comfy} 导入风格库...\n")
    result = build(comfy)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    for note in result["notes"]:
        print("  " + note)
    print(f"\n合计入库 {result['total']} 条，分 {len(result['groups'])} 组")
    print(f"写出 {OUT_PATH}")

    # 抽几条看看清洗效果
    print("\n--- 清洗效果抽样 ---")
    shown = 0
    for g in result["groups"]:
        if g["key"] in ("apt", "sdxl_lam") and g["items"]:
            for it in g["items"][:2]:
                print(f"  [{g['label']}] {it['zh']}  ({it['words']} 词)")
                print(f"      {it['text'][:150]}")
                shown += 1
        if shown >= 6:
            break
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
