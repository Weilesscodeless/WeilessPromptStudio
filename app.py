# -*- coding: utf-8 -*-
"""Rebels Prompt Studio —— 本地提示词增强器后端。

独立网页工具，不依赖 ComfyUI。用 ComfyUI 整合包里的 python_embeded 跑，
复用机器上已有的 GGUF，零新增下载。

启动：
    python app.py            # 默认 http://127.0.0.1:7860
    python app.py --port 8000 --open
"""

import os
import sys
import json
import threading
import time
from contextlib import asynccontextmanager

# ComfyUI 的 python_embeded 是 isolated 模式（有 python312._pth），
# 脚本目录不会自动进 sys.path，项目内导入之前必须自己补上。
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from catalog import styles as styles_mod
from catalog import formats as formats_mod
from catalog import presets as presets_mod
from catalog import local as local_mod
from engine import prompt as prompt_mod
from engine import audit as audit_mod
from engine.clean import clean_output
from engine.llm import LlamaEngine

CONFIG_PATH = os.path.join(ROOT, "config.json")

DEFAULT_CONFIG = {
    "host": "127.0.0.1",
    "port": 7860,
    "model_dirs": None,          # None 表示用 engine.llm.DEFAULT_MODEL_DIRS
    "default_model": None,       # None 表示自动选最大的
    "mode": "resident",          # resident 常驻 / ondemand 按需
    "idle_unload_seconds": 0,    # >0 时空闲这么久自动卸载，把显存让给 ComfyUI
    "think_mode": "off",         # off 强制关闭模型思考（默认，快且稳定）
    "n_ctx": 4096,
    "n_gpu_layers": -1,
    "max_tokens": 400,
    "temperature": 0.7,
    "top_p": 0.9,
    "repeat_penalty": 1.15,
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f) or {})
        except Exception as e:
            print(f"[警告] config.json 读取失败，用默认配置: {e}")
    return cfg


CONFIG = load_config()
ENGINE = LlamaEngine(CONFIG)


def _idle_watchdog():
    """空闲够久就把模型卸载，把显存让给 ComfyUI。"""
    while True:
        time.sleep(30)
        try:
            ENGINE.maybe_idle_unload()
        except Exception:
            pass


def _print_banner():
    st = local_mod.stats()
    styles_s = styles_mod.stats()
    presets_s = presets_mod.stats()
    models = ENGINE.list_models()
    lines = [
        "",
        "=" * 62,
        "  Rebels Prompt Studio",
        "=" * 62,
        f"  风格维度   {styles_s['dimensions']} 维 / {styles_s['items']} 条",
        f"  场景预设   {presets_s['presets']} 个",
        f"  外挂风格库 {st['total']} 条 / {st['groups']} 组"
        + ("" if st["total"] else "   （未导入，跑 tools/import_local_styles.py）"),
        f"  可用模型   {len(models)} 个",
    ]
    if models:
        lines.append(f"  默认模型   {os.path.basename(ENGINE.default_model_path())}")
    lines += [
        f"  加载策略   {CONFIG['mode']}"
        + (f"（空闲 {CONFIG['idle_unload_seconds']}s 自动卸载）"
           if CONFIG["idle_unload_seconds"] else ""),
        f"  思考模式   {'关闭（快）' if CONFIG['think_mode'] == 'off' else '开启'}",
        "=" * 62,
        f"  打开 http://{CONFIG['host']}:{CONFIG['port']}",
        "",
    ]
    # flush 是必须的：启动脚本把输出重定向到控制台时，
    # 不 flush 的话这段横幅会卡在缓冲区里，用户以为没启动。
    print("\n".join(lines), flush=True)


@asynccontextmanager
async def lifespan(_app):
    threading.Thread(target=_idle_watchdog, daemon=True).start()
    _print_banner()
    yield


app = FastAPI(title="Rebels Prompt Studio", lifespan=lifespan)


# ==========================================================================
# 请求模型
# ==========================================================================

class EnhanceRequest(BaseModel):
    input: str = ""
    mode: str = "free"                  # free 软约束自由改写 / slots 精确槽位
    format: str = "universal"
    strength: str = "standard"
    language: str = "auto"
    # 维度风格：{"medium": "oil", "lighting": "neon", ...}
    style_ids: Dict[str, str] = {}
    # 外挂风格库：[{"group": "apt", "index": 3}, ...]
    local_picks: List[Dict[str, Any]] = []
    model_path: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    # 覆盖值（界面上可调）
    extra_instruction: str = ""


class ModelRequest(BaseModel):
    model_path: str


# ==========================================================================
# 内部工具
# ==========================================================================

def resolve_style_texts(style_ids, local_picks):
    """把前端的风格选择解析成注入文本列表。

    两条来源：内置维度库（198 条）和外挂库（3755 条）。
    不存在的 id 静默丢弃，避免脏数据进 system prompt。
    """
    texts = []
    labels = []

    items = styles_mod.resolve(style_ids or {})
    for it in items:
        texts.append(it["inject"])
        labels.append(f"{it['dimension_label']}·{it['zh']}")

    for pick in (local_picks or []):
        gk = pick.get("group")
        idx = pick.get("index")
        if gk is None or idx is None:
            continue
        text = local_mod.get_text(gk, int(idx))
        if text:
            texts.append(text)
            labels.append(f"外挂·{gk}#{idx}")

    return texts, labels


def pick_model(req_path):
    if req_path:
        return req_path
    if CONFIG.get("default_model"):
        return CONFIG["default_model"]
    return ENGINE.default_model_path()


# ==========================================================================
# 请求日志
#
# 之前后端没记任何请求，用户报告"输出里词叠在一起"时手上零线索，
# 只能靠猜着复现。这个日志就是为了不再发生那种情况：
# 每次增强的输入、风格、拼装出的 system prompt、模型原始输出、
# 最终结果和溯源片段全部落盘，事后能一字不差地重放。
# ==========================================================================

LOG_DIR = os.path.join(ROOT, "logs")
LOG_PATH = os.path.join(LOG_DIR, "enhance.jsonl")
LOG_BACKUP = LOG_PATH + ".1"
MAX_LOG_BYTES = 8 * 1024 * 1024


def _log_enhance(entry):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        if os.path.isfile(LOG_PATH) and os.path.getsize(LOG_PATH) > MAX_LOG_BYTES:
            try:
                if os.path.isfile(LOG_BACKUP):
                    os.remove(LOG_BACKUP)
                os.replace(LOG_PATH, LOG_BACKUP)
            except Exception:
                pass
        entry["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _read_log(limit=20):
    """读最近 N 条记录，新的在前。"""
    if not os.path.isfile(LOG_PATH):
        return []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []
    out = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    out.reverse()
    return out


# ==========================================================================
# 接口
# ==========================================================================

@app.get("/api/meta")
def api_meta():
    """前端启动时拉一次：所有可选项 + 模型列表 + 引擎状态。"""
    return {
        "styles": styles_mod.catalog(),
        "formats": formats_mod.catalog(),
        "presets": presets_mod.catalog(),
        "preset_categories": presets_mod.categories(),
        "local_styles": local_mod.catalog(),
        "options": prompt_mod.options(),
        "models": ENGINE.list_models(),
        "status": ENGINE.status(),
        "config": {
            "mode": CONFIG["mode"],
            "think_mode": CONFIG["think_mode"],
            "max_tokens": CONFIG["max_tokens"],
            "temperature": CONFIG["temperature"],
        },
        "counts": {
            "style_items": styles_mod.stats()["items"],
            "presets": presets_mod.stats()["presets"],
            "local_styles": local_mod.stats()["total"],
            "formats": len(formats_mod.MODEL_FORMATS),
        },
    }


@app.post("/api/enhance")
def api_enhance(req: EnhanceRequest):
    user_input = (req.input or "").strip()
    if not user_input:
        raise HTTPException(400, "输入不能为空")

    style_texts, style_labels = resolve_style_texts(req.style_ids, req.local_picks)
    model_path = pick_model(req.model_path)
    if not model_path:
        raise HTTPException(400, "没找到任何 GGUF 模型，检查 config.json 的 model_dirs")

    # 额外指令作为附加风格注入（同样受白名单管辖）
    if req.extra_instruction.strip():
        style_texts.append(req.extra_instruction.strip())
        style_labels.append("自定义附加")

    system_prompt = prompt_mod.build_system_prompt(
        mode=req.mode,
        format_id=req.format,
        style_texts=style_texts,
        strength=req.strength,
        input_text=user_input,
        language=req.language,
    )

    warnings = []

    # 语言适配提示。用户在界面上显式选了中文、而目标编码器只认英文时，
    # 尊重他的选择但不假装能生效。
    fmt_entry = formats_mod.get(req.format)
    eff_lang, in_lang, translating = prompt_mod.resolve_language(
        req.language, req.format, user_input)
    if req.language == "zh" and fmt_entry["lang"] == "en":
        warnings.append(
            f"{fmt_entry['zh']} 的编码器（{fmt_entry['encoder']}）只认英文，"
            "输出中文基本不会生效，建议改回「自动」"
        )

    budget = prompt_mod.compute_budget(user_input, req.strength, style_texts, req.format)
    max_tokens = req.max_tokens or CONFIG["max_tokens"]
    temperature = req.temperature if req.temperature is not None else CONFIG["temperature"]

    t0 = time.time()
    try:
        raw_text, llm_diag = ENGINE.generate(
            system_prompt=system_prompt,
            user_message=user_input,
            model_path=model_path,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=CONFIG["top_p"],
            repeat_penalty=CONFIG["repeat_penalty"],
        )
    except Exception as e:
        raise HTTPException(500, f"模型调用失败: {type(e).__name__}: {e}")

    slots = None

    if req.mode == "slots":
        slots = prompt_mod.parse_slots(raw_text)
        if slots is None:
            # JSON 没解析出来，回退到自由模式再跑一次，别让用户拿到一坨 JSON
            warnings.append("槽位模式解析失败，已自动回退到自由改写")
            fb_prompt = prompt_mod.build_system_prompt(
                mode="free", format_id=req.format, style_texts=style_texts,
                strength=req.strength, input_text=user_input, language=req.language,
            )
            raw_text, llm_diag = ENGINE.generate(
                system_prompt=fb_prompt, user_message=user_input,
                model_path=model_path, max_tokens=max_tokens,
                temperature=temperature, top_p=CONFIG["top_p"],
                repeat_penalty=CONFIG["repeat_penalty"],
            )
            final, clean_diag = clean_output(raw_text, user_input)
        else:
            # 槽位模式由程序拼装，不走模型，所以结构确定
            final = prompt_mod.assemble_from_slots(slots, req.format, style_texts)
            clean_diag = {"raw": raw_text, "steps": [("槽位拼装（未经模型）", 0)], "final": final}
    else:
        final, clean_diag = clean_output(raw_text, user_input)

    if not final.strip():
        final = raw_text
        warnings.append("清洗后为空，已回退为模型原始输出")

    spans, stats, missing = audit_mod.audit(final, user_input, style_texts, budget=budget)

    # 兜底重试。
    #
    # 实测：外挂库里较长的风格串会诱使模型把风格当成整个任务，把用户输入
    # 整个丢掉——出现过保留率 0%、输出只剩风格词的情况。system prompt 里
    # 已经写了 SURVIVAL RULE，但模型的遵守是概率性的，所以这里在程序侧
    # 再兜一道：检测到原话大量丢失就重试一次，并在提示词末尾点名。
    # 只重试一次，避免在模型不稳定时反复烧时间。
    # 保留率在跨语种时是 None（译文和原文对不上，算不出有意义的数字），
    # 所以必须先判 None 再比大小。
    if (req.mode != "slots" and not stats.get("cross_lang")
            and stats["retention"] is not None
            and stats["input_words"] >= 2 and stats["retention"] < 0.4):
        retry_sys = system_prompt + (
            "\n\nREMINDER — your previous attempt dropped the user's own words. "
            f"The user's message was: {user_input}. "
            "Every concept in it must appear in your output. "
            "If you are over the length limit, drop style words — never the "
            "user's content."
        )
        raw2, llm_diag = ENGINE.generate(
            system_prompt=retry_sys, user_message=user_input,
            model_path=model_path, max_tokens=max_tokens,
            temperature=max(0.2, temperature - 0.2),   # 降温度提高遵守度
            top_p=CONFIG["top_p"], repeat_penalty=CONFIG["repeat_penalty"],
        )
        final2, clean_diag2 = clean_output(raw2, user_input)
        spans2, stats2, missing2 = audit_mod.audit(
            final2, user_input, style_texts, budget=budget)
        # 只有确实改善了才采纳，否则保留第一次的结果
        was = int(stats["retention"] * 100)
        if stats2["retention"] > stats["retention"]:
            final, clean_diag = final2, clean_diag2
            spans, stats, missing = spans2, stats2, missing2
            warnings.append(
                f"首次生成只保留了 {was}% 的原话，已自动重试并采用更忠实的一版"
            )
        else:
            warnings.append(
                f"模型丢失了部分原话（保留 {was}%）且重试未改善，"
                "建议减少风格选择或改用精确槽位模式"
            )

    summary = audit_mod.summarize(spans, stats)

    if stats["over_budget"]:
        warnings.append(
            f"超出长度预算 {stats['output_words'] - budget} 词，可降低强度或减少风格选择"
        )
    if (stats["retention"] is not None and stats["retention"] < 0.6
            and stats["input_words"] >= 2):
        warnings.append(f"原话保留率偏低（{int(stats['retention']*100)}%），模型改写了较多内容")

    # 溯源片段拼不回原文时说明分色逻辑出了问题，这时界面上的文字会错乱。
    # 后端已经降级成不分色保证文字正确，但要让用户知道分色不可信。
    if stats.get("span_rebuild_failed"):
        warnings.append("溯源分色不可用（片段无法还原原文），已关闭分色以保证文字正确")

    result = {
        "prompt": final,
        "spans": spans,
        "stats": stats,
        "summary": summary,
        "missing": missing,
        "slots": slots,
        "style_labels": style_labels,
        "warnings": warnings,
        "elapsed": round(time.time() - t0, 2),
        "diagnostics": {
            "system_prompt": system_prompt,
            "raw_output": clean_diag.get("raw", raw_text),
            "clean_steps": [
                {"label": lbl, "removed": n} for lbl, n in clean_diag.get("steps", [])
            ],
            "llm": llm_diag,
        },
    }

    _log_enhance({
        "request": {
            "input": user_input, "mode": req.mode, "format": req.format,
            "strength": req.strength, "language": req.language,
            "style_ids": req.style_ids, "local_picks": req.local_picks,
            "temperature": temperature, "model": os.path.basename(model_path),
        },
        "style_texts": style_texts,
        "system_prompt": system_prompt,
        "raw_output": clean_diag.get("raw", raw_text),
        "final": final,
        "spans": spans,
        "stats": stats,
        "warnings": warnings,
        "elapsed": result["elapsed"],
    })
    # 保留率可能是 None（跨语种时算不出），日志不能直接乘 100
    if stats["retention"] is None:
        keep = f"译文{stats['translated_words']}词"
    else:
        keep = f"保留{int(stats['retention'] * 100)}%"
    print(
        f"[{time.strftime('%H:%M:%S')}] {req.mode}/{req.strength} "
        f"{stats['output_words']}/{budget}词 {keep} "
        f"自加{stats['added_words']} {result['elapsed']}s",
        flush=True,
    )
    return result


@app.post("/api/unload")
def api_unload():
    ENGINE.unload()
    return {"ok": True, "status": ENGINE.status()}


@app.post("/api/preload")
def api_preload(req: ModelRequest):
    """预加载模型。界面上点一下就能先把模型读进显存，避免第一次生成等加载。"""
    try:
        ENGINE._load(req.model_path)
    except Exception as e:
        raise HTTPException(500, f"加载失败: {type(e).__name__}: {e}")
    return {"ok": True, "status": ENGINE.status()}


@app.get("/api/status")
def api_status():
    return ENGINE.status()


@app.get("/api/logs")
def api_logs(limit: int = 20):
    """最近几次增强的完整记录。出问题时看这个，不用靠复现。"""
    return {
        "path": LOG_PATH,
        "entries": _read_log(limit),
    }


# ==========================================================================
# 静态文件
# ==========================================================================

STATIC_DIR = os.path.join(ROOT, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


def main():
    import argparse
    import uvicorn
    import webbrowser

    ap = argparse.ArgumentParser(description="Rebels Prompt Studio")
    ap.add_argument("--port", type=int, default=CONFIG["port"])
    ap.add_argument("--host", default=CONFIG["host"])
    ap.add_argument("--open", action="store_true", help="启动后自动打开浏览器")
    ap.add_argument("--reload", action="store_true")
    args = ap.parse_args()

    if args.open:
        threading.Timer(1.5, lambda: webbrowser.open(
            f"http://{args.host}:{args.port}")).start()

    uvicorn.run(
        "app:app" if args.reload else app,
        host=args.host, port=args.port,
        reload=args.reload, log_level="warning",
    )


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
