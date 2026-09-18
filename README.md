# Rebels Prompt Studio

独立的本地提示词增强器。不接入 ComfyUI，浏览器里用，模型跑在本地。

针对旧节点包（RebelsPromptEnhancer）的三个问题重做：

| 问题 | 这里的解法 |
|---|---|
| 每次输出数百词、偏离原意、原话被稀释 | 来源规则 + 风格白名单 + 长度预算，三道约束叠加 |
| 没法在结果上再改 | 不需要 —— 直接出干净结果，你拿去自己改 |
| 风格和预制场景不够多 | 7 维 198 条内置 + 62 个场景预设 + 3755 条本机外挂库 |

---

## 快速开始

```
双击 启动.bat
```

浏览器自动打开 `http://127.0.0.1:7860`。关掉命令行窗口即停止服务。

首次使用建议先导入外挂风格库（把本机 ComfyUI 生态里已有的 3000+ 条风格接进来）：

```
G:\ComfyUI_Mie_V34\python_embeded\python.exe tools\import_local_styles.py
```

---

## 三道约束怎么起作用

旧工具的 system prompt 里写着 "Cover subject, environment, lighting,
composition, and mood" —— 这等于命令模型把五个维度全部补上。膨胀是必然的。

这里换成了三条：

**1. 来源规则**　用户输入是唯一的内容来源。明确禁止引入任何用户没写的东西。

**2. 风格白名单**　模型唯一被允许新增的，是你自己点选的风格词。
这条把"预设风格省打字"和"不许偏离原意"这对矛盾解开了——
风格词是你主动提供的，不是模型自由发挥的。

**3. 长度预算**　按输入词数算出硬上限写进提示词，并且**把风格词的长度单独计入**。
输入 5 词、预算 10 词、而选中的风格词本身有 14 词，这种情况会让模型
只能在丢内容和丢风格之间二选一，所以预算必须分开算。

---

## 实测对比

同一台机器、同一个模型（Qwen3.5-9B-Uncensored Q6_K）、同一个输入
`cyberpunk girl by the window`：

| | 旧节点包 | 本工具（轻强度） |
|---|---|---|
| 耗时 | 4.97 s | **1.17 s** |
| 输出 token | 335 | **22** |
| 模型自加词 | **258 个** | **2 个** |

旧工具的实际输出（节选）：

> A lone cyberpunk girl stands silhouetted against a towering window in a
> rain-soaked, dystopian metropolis... a cramped, cluttered apartment
> **filled with humming servers and tangled wires**... **an old-fashioned
> desk lamp**... **holographic data streams projecting onto her retinas**...
> cybernetic implants embedded in **her temples and fingers**...
> **heavy bass thumping through the floorboards**... **flying cars**...

输入是 7 个词。模型编了一整间公寓、服务器、台灯、飞车和一段剧情。

本工具的输出：

> A cyberpunk girl stands by the window, illuminated by neon lighting,
> colored tube glow, and wet reflections.

---

## 溯源面板

结果里的每个词都标了来源，四种颜色：

- <span>绿</span> **你的输入** —— 你自己打的词
- <span>紫</span> **你选的风格** —— 来自你点选的风格：维度或外挂库
- <span>红</span> **模型自加** —— 模型自己发挥的，**这是你要盯的**
- <span>灰</span> **语法词** —— the / a / of 这类连接词

外加三个数字：

- **原话保留率** —— 你输入里的实词有几个进了最终结果。这是"被稀释"的量化指标
- **模型自加词数** —— 0 最好
- **输出长度 / 预算** —— 超了会标红

还会列出"你的输入里有这些词没进最终结果"，直接点名丢了什么。

---

## 两种模式

**自由改写（默认）**　模型重写整句，但受上面三道约束。读起来自然。

**精确槽位**　模型只输出结构化字段（subject / action / environment / style），
最终文本由程序按目标格式的语法族拼装。结构完全确定，**不可能膨胀**。
输入里没说的字段，模型必须留空——所以它没有加戏的空间。

JSON 解析失败会自动回退到自由模式，不会让你拿到一坨 JSON。

---

## 参数说明

**别动的**（改了容易出问题）：

| 参数 | 位置 | 为什么 |
|---|---|---|
| `think_mode` | config.json | 必须保持 `off`。见下面「坑」第一条 |
| `n_ctx` | config.json | 4096 够用。system prompt 最长约 700 token |
| `n_gpu_layers` | config.json | `-1` = 全部层上显卡。显存不够改成 `0` 走 CPU |

**可以随便调的**：

| 参数 | 说明 |
|---|---|
| 模型 | 界面右上角下拉。默认自动选最大的那个 |
| 强度 | 轻 / 标准 / 自由。控制允许模型加多少东西 |
| 目标模型 | 决定输出语法。编码器信息写在选项下方的提示里 |
| 温度 | 高级里。0.7 合适；想更保守调到 0.3~0.5 |
| 附加指令 | 高级里。会作为附加风格一起送进模型，同样受白名单管辖 |

**显存不够时**：点右上角「卸载」把模型从显存里让出去；
或在 config.json 里设 `idle_unload_seconds: 300`，空闲 5 分钟自动卸载。

---

## 坑

**1. 思考模式必须关掉**

本机的 Qwen3.5-9B 系列默认开思考，而且这个 uncensored 微调把推理直接写成正文
（以 `Thinking Process:` 开头）。实测跑满 900 token 都出不了答案。

三条常规关闭途径在这台机器上都不可用：

- `/no_think` 软开关 —— 该模型的 chat template 里根本没有 `no_think`（0 次命中）
- `chat_template_kwargs={"enable_thinking": False}` —— llama-cpp-python 0.3.35
  的 `create_chat_completion` 不接受这个参数
- `Llama(chat_template=...)` —— `__init__` 只收 `chat_format` / `chat_handler`

本工具的做法是**绕开 chat 模板，手工拼 ChatML，把空的思考块直接写进去**：
模板逻辑是 `enable_thinking is false` 时渲染 `<think>\n\n</think>\n\n`，
所以手工拼到那一步，模型接着写的就是答案。实测 1.0 s 出结果且正常收尾。

另外，旧工具那套 `stop` 序列里的 `Thinking Process:` / `Analysis:` 必须删掉——
它们会在模型开始推理的第一个 token 就截断，导致**输出恒为空**。
本工具只保留回合边界 stop（`<|im_end|>` 等）。

**2. Python 是 isolated 模式**

ComfyUI 的 `python_embeded` 带 `python312._pth`，处于 isolated 模式：
**脚本所在目录不会自动进 `sys.path`**，`PYTHONPATH` 也被忽略。
所以项目内导入之前必须手动补路径。代码里已经在每个入口做了这件事，
但你如果要加新模块，记得它不会自动被找到。

**3. `data` 不能当包名**

site-packages 里已有一个叫 `data` 的包，会抢在我们的目录前面。
所以本地数据包叫 `catalog`，别改回去。

---

## 目录结构

```
RebelsPromptStudio/
├── app.py                    FastAPI 后端 + 静态文件服务
├── config.json               模型目录、加载策略、采样参数
├── 启动.bat                  一键启动
├── engine/
│   ├── llm.py                llama-cpp-python 封装、ChatML 手工路径、常驻/按需
│   ├── prompt.py             分层 system prompt 组装、两种模式、长度预算
│   ├── audit.py              词溯源、原话保留率
│   └── clean.py              输出清洗（移植自旧节点包并改造）
├── catalog/
│   ├── styles.py             7 维 198 条风格词条
│   ├── presets.py            62 个场景预设
│   ├── formats.py            11 种目标模型格式
│   ├── local.py              外挂库读取
│   └── local_styles.json     导入产物（3755 条）
├── tools/
│   └── import_local_styles.py  从本机 ComfyUI 生态导入风格库
└── static/                   前端（原生 JS，零构建）
```

---

## 外挂风格库

`tools/import_local_styles.py` 会扫描本机 ComfyUI 并导入：

| 来源 | 条数 |
|---|---|
| `ComfyUI-Apt_Preset/csv/styles*.csv` | 321（中文风格名） |
| `ComfyUI-Easy-Use/resources/fooocus_styles.json` | 275 |
| `ComfyUI_Lam/styles/*.json` | 275 |
| `comfyui-art-venture/.../sdxl_styles_*.json` | 106 |
| `ComfyUI-Apt_Preset/wildcards/*.txt` | 85 组 2700+ |

**导入时会剥离质量样板词**。这些库的条目普遍混着大量
`(masterpiece:1.3), (best quality:1.3), 8k resolution, RAW photo,
hyper-realistic` 这类词——最极端的一条「通用-写实」30 个词全是质量样板，
真正的风格信息是零。原样导入等于把旧工具的膨胀问题搬进新工具。

清洗器还处理了"包裹式模板"：`a cinematic photograph of {prompt}`
剥掉占位符后剩半句话，会被还原成 `cinematic photograph`。

导入后界面上每条会显示**词数**，超过 20 词的标红提醒——那是它的长度成本。

换 ComfyUI 目录的话改脚本顶部的 `DEFAULT_COMFY`，或用
`--comfy "D:\你的路径\ComfyUI"`。

---

## 扩展内置风格库

编辑 `catalog/styles.py` 的 `STYLE_DIMENSIONS`，按现有格式加一条：

```python
{"id": "my_style", "zh": "中文名", "en": "English name",
 "inject": "short english phrase, 3-8 words"},
```

**`inject` 保持短**。旧节点包的 `AESTHETIC_DESCRIPTORS` 每条是 15-25 词的
形容词堆（赛博朋克那条一次塞 7 个元素），点一个风格就自动注入一长串，
这本身就是膨胀源。这里的约定是 3-8 词。

加完重启即可，会同时出现在维度下拉和场景预设的引用范围里。

---

## 出问题怎么查

后端会记录每一次增强：

- 控制台一行摘要：`[11:51:09] free/standard 71/52词 保留100% 自加21 5.07s`
- 完整记录在 `logs/enhance.jsonl`（输入、风格、拼装出的 system prompt、
  模型原始输出、最终结果、溯源片段、统计），超过 8MB 自动轮转
- 也可以用 `http://127.0.0.1:7860/api/logs?limit=20` 直接看

```
浏览器里看到的结果不对
   ↓
curl "http://127.0.0.1:7860/api/logs?limit=1"
   ↓
比对 final 字段（真实输出）和 spans 字段（界面渲染用的分色片段）
两者拼起来不一致 = 分色逻辑的问题；一致 = 模型或提示词的问题
```

`stats.span_rebuild_failed` 为 `true` 表示分色片段无法还原原文，
后端会自动降级成不分色并在界面提示——文字仍然正确，只是没有颜色。
