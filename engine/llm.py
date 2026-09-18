# -*- coding: utf-8 -*-
"""本地模型封装。

复用你机器上已有的 GGUF，走 llama-cpp-python 进程内加载，不依赖
Ollama / llama-server（这台机器上都没装）。

加载策略：
    resident  常驻。首次调用时加载，之后一直在显存里。生成最快。
    ondemand  按需。每次调用加载、用完卸载。不占显存，但每次都要等加载。

    默认 resident——单独用这个工具时 9B Q6 占 7.4GB，RTX 5080 的 16GB 装得下。
    要同时跑 ComfyUI 生图时，界面上点「卸载模型」把显存让出去。
    也可以配 idle_unload 秒数，空闲够久自动卸载。

注意：Llama 对象不是线程安全的，FastAPI 是多线程，所以全程加锁。
"""

import os
import gc
import time
import threading

# model_dirs 默认值。用你机器上实际存在的位置。
DEFAULT_MODEL_DIRS = [
    r"G:\ComfyUI_Mie_V34\ComfyUI\models\LLM",
    r"C:\Users\10030\workspace\AI-DigitalHuman\llama.cpp\models",
    r"C:\Users\10030\workspace\RebelsPromptEnhancer\RebelsPromptEnhancer",
    r"C:\Users\10030\Downloads",
]

# 这些文件名片段表示不是独立文本模型，扫描时跳过
SKIP_MARKERS = ("mmproj", "clip_", "vae", "t5xxl", "text_encoder")


def _human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


class LlamaEngine:
    def __init__(self, config=None):
        cfg = config or {}
        self.model_dirs = cfg.get("model_dirs") or DEFAULT_MODEL_DIRS
        self.n_ctx = int(cfg.get("n_ctx", 4096))
        self.n_gpu_layers = int(cfg.get("n_gpu_layers", -1))
        self.mode = cfg.get("mode", "resident")
        self.idle_unload = int(cfg.get("idle_unload_seconds", 0))
        # off  = 强制关闭思考（默认，见下面 _build_chatml 的说明）
        # auto = 让模型正常思考，再由清洗层提取答案
        self.think_mode = cfg.get("think_mode", "off")

        self._llm = None
        self._loaded_path = None
        self._lock = threading.Lock()
        self._last_used = 0.0
        self._load_seconds = None
        self._dialect = None

    # ---------------- 模型发现 ----------------

    def list_models(self):
        """扫描所有配置目录，返回可用的 GGUF 列表。"""
        found = []
        seen = set()
        for d in self.model_dirs:
            if not d or not os.path.isdir(d):
                continue
            try:
                names = os.listdir(d)
            except Exception:
                continue
            for fn in names:
                if not fn.lower().endswith(".gguf"):
                    continue
                low = fn.lower()
                if any(m in low for m in SKIP_MARKERS):
                    continue
                path = os.path.join(d, fn)
                if path in seen:
                    continue
                seen.add(path)
                try:
                    size = os.path.getsize(path)
                except Exception:
                    size = 0
                found.append({
                    "name": fn,
                    "path": path,
                    "dir": d,
                    "size": size,
                    "size_human": _human_size(size),
                })
        found.sort(key=lambda x: x["size"], reverse=True)
        return found

    def default_model_path(self):
        """没指定就用最大的那个——通常是质量最好的。"""
        models = self.list_models()
        return models[0]["path"] if models else None

    # ---------------- 加载 / 卸载 ----------------

    def _detect_dialect(self):
        """从 GGUF 元数据判断对话模板方言，决定能不能走手工 ChatML 路径。

        为什么需要这个：Qwen3.5 系列默认开思考，而本机的
        Qwen3.5-9B-Uncensored 微调把推理直接写成正文（以 "Thinking Process:"
        开头），实测跑 900 token 都出不了答案。

        三条常规关闭途径都不可用：
          - /no_think 软开关：该模板里根本没有 no_think（0 次命中）
          - chat_template_kwargs={"enable_thinking": False}：
            llama-cpp-python 0.3.35 的 create_chat_completion 不接受这个参数
          - Llama(chat_template=...)：__init__ 只收 chat_format / chat_handler

        但模板里有一行关键逻辑：
            {%- if enable_thinking is defined and enable_thinking is false %}
                {{- '<think>\n\n</think>\n\n' }}     ← 渲染空思考块，直接答
        所以只要手工把提示词拼到那个空思考块为止，模型接着写的就是答案。
        实测 1.0s 出结果且 finish_reason=stop，而让它自由思考是 2.5s+ 且
        token 用尽仍无答案。
        """
        tmpl = ""
        try:
            tmpl = self._llm.metadata.get("tokenizer.chat_template", "") or ""
        except Exception:
            pass
        is_chatml = "<|im_start|>" in tmpl and "<|im_end|>" in tmpl
        is_thinking = "<think>" in tmpl or "enable_thinking" in tmpl
        self._dialect = {
            "has_template": bool(tmpl),
            "chatml": is_chatml,
            "thinking": is_thinking,
        }
        return self._dialect

    def _build_chatml(self, system_prompt, user_message):
        """手工拼 ChatML，助手回合预填空思考块。"""
        think = "<think>\n\n</think>\n\n" if self._dialect.get("thinking") else ""
        return (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_message}<|im_end|>\n"
            f"<|im_start|>assistant\n{think}"
        )

    def _load(self, model_path):
        if self._llm is not None and self._loaded_path == model_path:
            return self._llm
        if self._llm is not None:
            self._unload_locked()

        from llama_cpp import Llama
        t0 = time.time()
        self._llm = Llama(
            model_path=model_path,
            n_gpu_layers=self.n_gpu_layers,
            verbose=False,
            n_ctx=self.n_ctx,
        )
        self._loaded_path = model_path
        self._load_seconds = round(time.time() - t0, 1)
        self._detect_dialect()
        return self._llm

    def _unload_locked(self):
        if self._llm is None:
            return
        try:
            del self._llm
        except Exception:
            pass
        self._llm = None
        self._loaded_path = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def unload(self):
        with self._lock:
            self._unload_locked()

    def maybe_idle_unload(self):
        """空闲够久就自动卸载。由后台线程周期调用。"""
        if not self.idle_unload or self._llm is None:
            return
        if time.time() - self._last_used > self.idle_unload:
            self.unload()

    # ---------------- 推理 ----------------

    def generate(self, system_prompt, user_message, model_path=None,
                 max_tokens=600, temperature=0.7, top_p=0.9,
                 repeat_penalty=1.15, stop=None):
        """跑一次 chat completion，返回 (文本, 诊断信息)。

        诊断信息含耗时，界面用它显示"加载 8.2s / 生成 1.4s"，
        这样用户能判断慢在哪一环。
        """
        model_path = model_path or self.default_model_path()
        if not model_path:
            raise FileNotFoundError(
                "没找到任何 GGUF 模型。检查 config.json 里的 model_dirs。"
            )
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        from engine.clean import VERBOSE_STOPS

        with self._lock:
            t0 = time.time()
            fresh = self._loaded_path != model_path
            llm = self._load(model_path)
            load_t = time.time() - t0
            self._last_used = time.time()

            # 能用 ChatML 手工拼、且用户没要求保留思考时，走手工路径。
            # 这条路径能直接跳过思考阶段，实测比让模型自由思考快 2.5 倍，
            # 而且不会因为推理耗尽 token 而返回空结果。
            manual = self._dialect.get("chatml") and self.think_mode == "off"

            t1 = time.time()
            if manual:
                prompt = self._build_chatml(system_prompt, user_message)
                out = llm.create_completion(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    repeat_penalty=repeat_penalty,
                    stop=list(stop or []) + ["<|im_end|>", "<|im_start|>"],
                )
                text = out["choices"][0].get("text") or ""
            else:
                out = llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    repeat_penalty=repeat_penalty,
                    stop=stop if stop is not None else VERBOSE_STOPS,
                )
                text = out["choices"][0]["message"]["content"] or ""

            gen_t = time.time() - t1
            self._last_used = time.time()
            usage = out.get("usage") or {}
            if self.mode == "ondemand":
                self._unload_locked()

        diag = {
            "model": os.path.basename(model_path),
            "load_seconds": round(load_t, 1) if fresh else 0.0,
            "generate_seconds": round(gen_t, 2),
            "prompt_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "resident": self.mode == "resident",
            "think_mode": self.think_mode,
            "path": "manual_chatml" if manual else "chat_template",
        }
        return text.strip(), diag

    # ---------------- 状态 ----------------

    def status(self):
        vram = {}
        try:
            import torch
            if torch.cuda.is_available():
                free, total = torch.cuda.mem_get_info()
                vram = {
                    "free_gb": round(free / 1024 ** 3, 1),
                    "total_gb": round(total / 1024 ** 3, 1),
                    "used_gb": round((total - free) / 1024 ** 3, 1),
                    "device": torch.cuda.get_device_name(0),
                }
        except Exception:
            pass

        return {
            "loaded": self._llm is not None,
            "loaded_model": os.path.basename(self._loaded_path) if self._loaded_path else None,
            "loaded_path": self._loaded_path,
            "load_seconds": self._load_seconds,
            "mode": self.mode,
            "idle_unload_seconds": self.idle_unload,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "vram": vram,
        }


if __name__ == "__main__":
    import sys, io
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    eng = LlamaEngine()
    models = eng.list_models()
    print(f"扫描到 {len(models)} 个文本 GGUF:\n")
    for m in models:
        print(f"  {m['size_human']:>8}  {m['name']}")
        print(f"           {m['dir']}")
    print()
    print("默认选择（最大的）:", eng.default_model_path())
    print()
    st = eng.status()
    print("状态:", {k: v for k, v in st.items() if k != "loaded_path"})
