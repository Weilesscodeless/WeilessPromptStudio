/* Rebels Prompt Studio 前端。零构建，原生 JS。 */

const $ = (id) => document.getElementById(id);
const el = (tag, cls, txt) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (txt != null) n.textContent = txt;
  return n;
};

const S = {
  meta: null,
  mode: "free",
  strength: "standard",
  language: "auto",
  format: "universal",
  styleIds: {},                 // {dimKey: itemId}
  localPicks: new Set(),        // "group#index"
  localGroup: null,
  localQuery: "",
  presetCat: null,
  busy: false,
};

/* ---------------- 初始化 ---------------- */

async function boot() {
  try {
    const r = await fetch("/api/meta");
    S.meta = await r.json();
  } catch (e) {
    document.body.innerHTML =
      '<p style="padding:40px;color:#ff6b5e">连不上后端。确认 app.py 还在运行。</p>';
    return;
  }
  renderCounts();
  renderModels();
  renderFormats();
  renderStrengths();
  renderLanguages();
  renderMode();
  renderDimensions();
  renderPresets();
  renderLocal();
  bindActions();
  refreshStatus();
  setInterval(refreshStatus, 15000);
}

function renderCounts() {
  const c = S.meta.counts;
  $("counts").textContent =
    `${c.style_items} 风格 · ${c.presets} 预设 · ${c.local_styles} 外挂 · ${c.formats} 格式`;
  $("localCount").textContent = c.local_styles
    ? `${c.local_styles} 条 / ${S.meta.local_styles.length} 组`
    : "未导入（跑 tools/import_local_styles.py）";
}

/* ---------------- 模型 ---------------- */

function renderModels() {
  const sel = $("modelSelect");
  sel.innerHTML = "";
  const models = S.meta.models || [];
  if (!models.length) {
    sel.appendChild(el("option", null, "未找到 GGUF"));
    return;
  }
  models.forEach((m, i) => {
    const o = el("option", null, `${m.name}  (${m.size_human})`);
    o.value = m.path;
    if (i === 0) o.selected = true;
    o.title = m.path;
    sel.appendChild(o);
  });
  sel.onchange = () => applyStatus(S.meta.status);
}

function currentModel() {
  return $("modelSelect").value;
}

async function refreshStatus() {
  try {
    const st = await (await fetch("/api/status")).json();
    S.meta.status = st;
    applyStatus(st);
  } catch (e) { /* 后端还没起来 */ }
}

function applyStatus(st) {
  const v = st.vram || {};
  $("vramBox").textContent = v.total_gb
    ? `显存 ${v.used_gb} / ${v.total_gb} GB`
    : "显存 —";
  $("vramBox").title = v.device || "";
  const loaded = st.loaded && st.loaded_path === currentModel();
  $("btnLoad").textContent = loaded ? "已加载" : "预加载";
  $("btnLoad").disabled = loaded;
  $("btnUnload").disabled = !st.loaded;
}

/* ---------------- 选项渲染 ---------------- */

function renderFormats() {
  const sel = $("formatSelect");
  sel.innerHTML = "";
  (S.meta.formats || []).forEach((f) => {
    const o = el("option", null, f.zh);
    o.value = f.id;
    sel.appendChild(o);
  });
  sel.value = S.format;
  sel.onchange = () => { S.format = sel.value; };
  updateFormatHint();
}

function updateFormatHint() {
  const f = (S.meta.formats || []).find((x) => x.id === S.format);
  if (!f) return;
  const fam = { prose: "自然语言", tags: "标签+权重", booru: "booru 标签" }[f.family] || f.family;
  $("formatHint").textContent = `编码器：${f.encoder}　语法族：${fam}　${f.note}`;
}

function renderStrengths() {
  const box = $("strengthSeg");
  box.innerHTML = "";
  (S.meta.options.strengths || []).forEach((s) => {
    const b = el("button", s.id === S.strength ? "on" : "", s.label);
    b.dataset.v = s.id;
    b.onclick = () => {
      S.strength = s.id;
      [...box.children].forEach((c) => c.classList.toggle("on", c === b));
      updateStrengthHint();
      updateBudget();
    };
    box.appendChild(b);
  });
  updateStrengthHint();
}

function updateStrengthHint() {
  const s = (S.meta.options.strengths || []).find((x) => x.id === S.strength);
  $("strengthHint").textContent = s ? s.note : "";
}

function renderLanguages() {
  const box = $("langSeg");
  box.innerHTML = "";
  (S.meta.options.languages || []).forEach((l) => {
    const b = el("button", l.id === S.language ? "on" : "", l.label);
    b.dataset.v = l.id;
    b.onclick = () => {
      S.language = l.id;
      [...box.children].forEach((c) => c.classList.toggle("on", c === b));
    };
    box.appendChild(b);
  });
}

function renderMode() {
  const box = $("modeSeg");
  [...box.children].forEach((b) => {
    b.onclick = () => {
      S.mode = b.dataset.v;
      [...box.children].forEach((c) => c.classList.toggle("on", c === b));
      $("modeHint").textContent = S.mode === "free"
        ? "模型自由重写，但受来源规则和长度预算双重约束。"
        : "模型只输出结构化字段，最终文本由程序拼装，结构完全确定、不可能膨胀。";
    };
  });
}

/* ---------------- 风格维度 ---------------- */

function renderDimensions() {
  const box = $("dimensions");
  box.innerHTML = "";
  (S.meta.styles || []).forEach((d) => {
    const row = el("div", "dim");
    row.appendChild(el("span", "lbl", d.label));
    const sel = el("select");
    const none = el("option", null, "— 不指定 —");
    none.value = "";
    sel.appendChild(none);
    d.items.forEach((it) => {
      const o = el("option", null, it.zh);
      o.value = it.id;
      sel.appendChild(o);
    });
    sel.title = d.hint;
    sel.onchange = () => {
      if (sel.value) S.styleIds[d.key] = sel.value;
      else delete S.styleIds[d.key];
      updateStyleCount();
    };
    row.appendChild(sel);
    box.appendChild(row);
  });
}

function updateStyleCount() {
  const n = Object.keys(S.styleIds).length;
  $("btnClearStyles").textContent = n ? `清空风格（已选 ${n}）` : "清空风格";
  updateBudget();
}

function applyPreset(p) {
  // 预设填进各维度下拉；用户随后可以改其中任何一项
  S.styleIds = {};
  (S.meta.styles || []).forEach((d) => {
    const sel = $("dimensions").querySelectorAll("select")[
      (S.meta.styles || []).indexOf(d)
    ];
    const want = p.styles[d.key] || "";
    if (sel) sel.value = want;
    if (want) S.styleIds[d.key] = want;
  });
  // 输入框只填场景骨架，主体留给你
  const inp = $("input");
  if (!inp.value.trim() || confirm2("输入框已有内容，用预设的场景骨架替换掉？")) {
    inp.value = p.scaffold;
  }
  updateStyleCount();
  updateInputStat();
}

function confirm2(msg) {
  return window.confirm(msg);
}

/* ---------------- 场景预设 ---------------- */

function renderPresets() {
  const tabs = $("presetTabs");
  tabs.innerHTML = "";
  const cats = ["全部"].concat(S.meta.preset_categories || []);
  cats.forEach((c) => {
    const b = el("button", S.presetCat === c || (!S.presetCat && c === "全部") ? "on" : "", c);
    b.onclick = () => {
      S.presetCat = c === "全部" ? null : c;
      renderPresets();
    };
    tabs.appendChild(b);
  });

  const grid = $("presetGrid");
  grid.innerHTML = "";
  const list = (S.meta.presets || []).filter(
    (p) => !S.presetCat || p.category === S.presetCat
  );
  list.forEach((p) => {
    const b = el("button");
    b.appendChild(el("span", null, p.zh));
    b.appendChild(el("small", null, p.hint));
    b.title = p.scaffold;
    b.onclick = () => applyPreset(p);
    grid.appendChild(b);
  });
}

/* ---------------- 外挂风格库 ---------------- */

function buildLocalIndex() {
  const flat = [];
  (S.meta.local_styles || []).forEach((g) => {
    g.items.forEach((it) => {
      flat.push({ group: g.key, groupLabel: g.label, index: it.i, zh: it.zh, words: it.words });
    });
  });
  return flat;
}

function renderLocal() {
  const groups = S.meta.local_styles || [];
  const tabs = $("localTabs");
  tabs.innerHTML = "";
  if (!groups.length) {
    $("localList").innerHTML =
      '<div class="empty">未导入外挂风格库<br>跑 tools/import_local_styles.py 后刷新</div>';
    return;
  }
  const all = el("button", !S.localGroup ? "on" : "", "全部");
  all.onclick = () => { S.localGroup = null; renderLocal(); };
  tabs.appendChild(all);
  groups.forEach((g) => {
    const b = el("button", S.localGroup === g.key ? "on" : "", `${g.label} ${g.count}`);
    b.onclick = () => { S.localGroup = g.key; renderLocal(); };
    tabs.appendChild(b);
  });
  renderLocalList();
}

function renderLocalList() {
  const box = $("localList");
  box.innerHTML = "";
  const q = S.localQuery.trim().toLowerCase();
  let list = buildLocalIndex();
  if (S.localGroup) list = list.filter((x) => x.group === S.localGroup);
  if (q) {
    list = list.filter(
      (x) => x.zh.toLowerCase().includes(q) || x.groupLabel.toLowerCase().includes(q)
    );
  }
  list = list.slice(0, 400);   // 渲染上限，用搜索缩小范围

  if (!list.length) {
    box.appendChild(el("div", "empty", "没有匹配项"));
    return;
  }
  list.forEach((x) => {
    const key = `${x.group}#${x.index}`;
    const it = el("div", "it" + (S.localPicks.has(key) ? " on" : ""));
    it.appendChild(el("span", "nm", x.zh));
    const wc = el("span", "wc" + (x.words > 20 ? " warn" : ""), `${x.words} 词`);
    wc.title = x.words > 20 ? "这条较长，会明显拉长输出" : "";
    it.appendChild(wc);
    it.onclick = () => {
      if (S.localPicks.has(key)) S.localPicks.delete(key);
      else S.localPicks.add(key);
      it.classList.toggle("on");
      updateLocalPicked();
    };
    box.appendChild(it);
  });
  updateLocalPicked();
}

function updateLocalPicked() {
  $("localPickedCount").textContent = S.localPicks.size;
  updateBudget();
}

/* ---------------- 长度预算预览 ---------------- */

function countWords(t) {
  const cjk = (t.match(/[一-鿿]/g) || []).length;
  const latin = (t.match(/[A-Za-z0-9][A-Za-z0-9'\-]*/g) || []).length;
  return cjk + latin;
}

function updateInputStat() {
  const n = countWords($("input").value);
  $("inputStat").textContent = n ? `${n} 词` : "—";
}

function updateBudget() {
  const txt = $("input").value;
  const n = countWords(txt);
  const ratio = { light: 1.3, standard: 1.8, free: 3.0 }[S.strength] || 1.8;
  // 风格词数：维度词条的长度在服务端才知道，这里粗略估 6 词/条
  const styleN = Object.keys(S.styleIds).length * 6 + S.localPicks.size * 6;
  const base = Math.max(10, Math.min(150, Math.round(n * ratio)));
  const budget = base + styleN;
  $("budgetStat").textContent = n
    ? `预算约 ${budget} 词（内容 ${base} + 风格约 ${styleN}）`
    : "";
}

/* ---------------- 提交 ---------------- */

function bindActions() {
  $("input").addEventListener("input", () => { updateInputStat(); updateBudget(); });

  $("btnClearStyles").onclick = () => {
    S.styleIds = {};
    $("dimensions").querySelectorAll("select").forEach((s) => (s.value = ""));
    updateStyleCount();
  };

  $("btnClearLocal").onclick = () => {
    S.localPicks.clear();
    renderLocalList();
  };

  $("localSearch").addEventListener("input", (e) => {
    S.localQuery = e.target.value;
    renderLocalList();
  });

  $("temp").addEventListener("input", (e) => {
    $("tempVal").textContent = Number(e.target.value).toFixed(2);
  });

  $("btnGo").onclick = submit;
  $("input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit();
  });

  $("btnCopy").onclick = async () => {
    const t = $("output").dataset.plain || $("output").textContent;
    if (!t) return;
    await navigator.clipboard.writeText(t);
    $("btnCopy").textContent = "已复制";
    setTimeout(() => ($("btnCopy").textContent = "复制"), 1200);
  };

  $("btnUnload").onclick = async () => {
    await fetch("/api/unload", { method: "POST" });
    refreshStatus();
  };

  $("btnLoad").onclick = async () => {
    $("btnLoad").disabled = true;
    $("btnLoad").textContent = "加载中…";
    try {
      const r = await fetch("/api/preload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_path: currentModel() }),
      });
      if (!r.ok) alert("加载失败：" + (await r.json()).detail);
    } finally {
      refreshStatus();
    }
  };
}

async function submit() {
  if (S.busy) return;
  const input = $("input").value.trim();
  if (!input) { $("input").focus(); return; }

  S.busy = true;
  const btn = $("btnGo");
  btn.disabled = true;
  btn.textContent = "生成中…";
  $("goHint").textContent = "首次调用要加载模型，可能要十几秒";

  const body = {
    input,
    mode: S.mode,
    format: S.format,
    strength: S.strength,
    language: S.language,
    style_ids: S.styleIds,
    local_picks: [...S.localPicks].map((k) => {
      const [group, index] = k.split("#");
      return { group, index: Number(index) };
    }),
    model_path: currentModel(),
    extra_instruction: $("extra").value,
    temperature: Number($("temp").value),
  };

  try {
    const r = await fetch("/api/enhance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "请求失败");
    showResult(data);
    $("goHint").textContent = "";
  } catch (e) {
    $("output").className = "output";
    $("output").textContent = "出错了：" + e.message;
    $("goHint").textContent = "";
  } finally {
    S.busy = false;
    btn.disabled = false;
    btn.textContent = "增 强";
    refreshStatus();
  }
}

/* ---------------- 结果渲染 ---------------- */

function showResult(d) {
  const out = $("output");
  out.className = "output";
  out.innerHTML = "";
  out.dataset.plain = d.prompt;

  (d.spans || []).forEach((s) => {
    const sp = el("span", "sp " + s.source, s.text);
    if (s.source === "added") sp.title = "模型自行添加的内容";
    if (s.source === "input") sp.title = "来自你的输入";
    if (s.source === "style") sp.title = "来自你选中的风格";
    out.appendChild(sp);
  });
  if (!d.spans || !d.spans.length) out.textContent = d.prompt;

  // 统计
  const st = d.stats || {};
  const box = $("stats");
  box.innerHTML = "";
  const pct = Math.round((st.retention || 0) * 100);
  addStat(box, "原话保留", pct + "%",
    pct >= 90 ? "good" : pct >= 60 ? "" : "bad");
  addStat(box, "模型自加", st.added_words + " 词",
    st.added_words === 0 ? "good" : st.added_words > 20 ? "bad" : "");
  addStat(box, "输出长度", `${st.output_words} / ${st.budget} 词`,
    st.over_budget ? "bad" : "good");
  addStat(box, "耗时", d.elapsed + " s");

  $("summary").textContent = d.summary || "";

  const wbox = $("warnings");
  wbox.innerHTML = "";
  (d.warnings || []).forEach((w) => wbox.appendChild(el("div", "warn", "⚠ " + w)));
  (d.missing || []).length &&
    wbox.appendChild(el("div", "warn",
      "⚠ 你的输入里有这些词没进最终结果：" + d.missing.join("、")));

  // 诊断
  const g = d.diagnostics || {};
  const l = g.llm || {};
  $("diagLine").textContent =
    `${l.model || ""}　路径 ${l.path || ""}　`
    + `加载 ${l.load_seconds || 0}s　生成 ${l.generate_seconds || 0}s　`
    + `出 ${l.output_tokens || 0} token　思考模式 ${l.think_mode || "-"}`;
  $("dSys").textContent = g.system_prompt || "";
  $("dRaw").textContent = g.raw_output || "";
  $("dClean").textContent = (g.clean_steps || []).length
    ? g.clean_steps.map((s) => `${s.label}　剥掉 ${s.removed} 字符`).join("\n")
    : "（未做任何清洗）";
  $("dSlots").textContent = d.slots
    ? JSON.stringify(d.slots, null, 2)
    : "（非槽位模式）";
}

function addStat(box, k, v, cls) {
  const d = el("div", "stat" + (cls ? " " + cls : ""));
  d.appendChild(el("span", "k", k));
  d.appendChild(el("span", "v", v));
  box.appendChild(d);
}

boot();
