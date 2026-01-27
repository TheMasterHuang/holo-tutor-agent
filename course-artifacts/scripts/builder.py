# course-artifacts/scripts/builder.py
import json
import os
from datetime import datetime
from typing import List

from visual_spec import (
    BUILDER_VERSION,
    VisualSpecValidationError,
    compute_spec_hash,
    get_content_md,
    get_meta_date,
    get_meta_title,
    get_meta_watermark,
    normalize_exports,
    normalize_visual_spec,
    parse_only_list,
    resolve_outdir,
    sanitize_filename_component,
    validate_visual_spec_v1_1,
)
from render_pdf import render_pdf
from render_docx import render_lecture_docx, render_quiz_docx
from pack_zip import pack, write_manifest


# ----------------------------
# Utils
# ----------------------------
def escape_html(s: str) -> str:
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def safe_remove(path: str) -> bool:
    """Try remove existing output file. Return True if removed or not exist; False if cannot remove."""
    try:
        if os.path.exists(path):
            os.remove(path)
        return True
    except PermissionError:
        return False
    except Exception:
        return False


def now_stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def md_to_basic_html(md: str) -> str:
    """
    v1: minimal markdown -> HTML
    - supports bullet lines '- '
    - supports blank line paragraph breaks
    - supports code blocks fenced by ```
    Everything is escaped.
    """
    if md is None:
        return ""

    text = md.replace("\r\n", "\n")
    lines = text.split("\n")

    out = []
    in_ul = False
    in_code = False
    code_buf = []

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def close_code():
        nonlocal in_code, code_buf
        if in_code:
            code_html = escape_html("\n".join(code_buf))
            out.append(f"<pre class='code'><code>{code_html}</code></pre>")
            code_buf = []
            in_code = False

    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                close_code()
            else:
                close_ul()
                in_code = True
            continue

        if in_code:
            code_buf.append(line)
            continue

        if line.strip().startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            item = escape_html(line.strip()[2:])
            out.append(f"<li>{item}</li>")
            continue

        # normal line
        close_ul()
        if line.strip() == "":
            out.append("<div class='p-spacer'></div>")
        else:
            out.append(f"<p>{escape_html(line)}</p>")

    close_ul()
    close_code()
    return "\n".join(out)


# ----------------------------
# VisualSpec v1 renderers (HTML)
# ----------------------------
def render_visual_mermaid(v: dict) -> str:
    title = escape_html(v.get("title", ""))
    caption = escape_html(v.get("caption", ""))
    mermaid = v.get("data", {}).get("mermaid", "")
    mermaid_esc = escape_html(mermaid)

    return f"""
    <div class="viz-card">
      <div class="viz-title">{title}</div>
      <div class="viz-caption">{caption}</div>
      <div class="viz-body">
        <div class="mermaid">{mermaid_esc}</div>
        <details class="viz-src">
          <summary>查看 Mermaid 源码</summary>
          <pre>{mermaid_esc}</pre>
        </details>
      </div>
    </div>
    """


def render_visual_plot(v: dict, idx: int) -> str:
    title = escape_html(v.get("title", ""))
    caption = escape_html(v.get("caption", ""))
    data = v.get("data", {})
    canvas_id = f"plot_{idx}"

    payload = escape_html(json.dumps(data, ensure_ascii=False))

    return f"""
    <div class="viz-card">
      <div class="viz-title">{title}</div>
      <div class="viz-caption">{caption}</div>
      <div class="viz-body">
        <canvas class="plot-canvas" id="{canvas_id}" data-plot="{payload}"></canvas>
        <details class="viz-src">
          <summary>查看 Plot 数据</summary>
          <pre>{escape_html(json.dumps(data, ensure_ascii=False, indent=2))}</pre>
        </details>
      </div>
    </div>
    """


def render_visual_cards(v: dict) -> str:
    title = escape_html(v.get("title", ""))
    caption = escape_html(v.get("caption", ""))
    cards = v.get("data", {}).get("cards", [])

    card_html = []
    for i, c in enumerate(cards):
        front = escape_html(c.get("front", ""))
        back = escape_html(c.get("back", ""))
        card_html.append(f"""
        <div class="flip-card" onclick="this.classList.toggle('flipped')">
          <div class="flip-inner">
            <div class="flip-front">
              <div class="flip-label">Q{i+1}</div>
              <div class="flip-text">{front}</div>
              <div class="flip-tip">点击翻面</div>
            </div>
            <div class="flip-back">
              <div class="flip-label">A{i+1}</div>
              <div class="flip-text">{back}</div>
              <div class="flip-tip">点击返回</div>
            </div>
          </div>
        </div>
        """)

    return f"""
    <div class="viz-card">
      <div class="viz-title">{title}</div>
      <div class="viz-caption">{caption}</div>
      <div class="viz-body">
        <div class="flip-grid">
          {''.join(card_html)}
        </div>
      </div>
    </div>
    """


def render_visual_unknown(v: dict) -> str:
    title = escape_html(v.get("title", "(untitled)"))
    vtype = escape_html((v.get("type") or "").lower())
    caption = escape_html(v.get("caption", ""))
    return f"""
    <div class="viz-card">
      <div class="viz-title">{title}</div>
      <div class="viz-caption">{caption}</div>
      <div class="viz-body">
        <div class="warn">未支持的可视化类型：<b>{vtype}</b>（已降级展示）</div>
        <details class="viz-src">
          <summary>查看原始数据</summary>
          <pre>{escape_html(json.dumps(v, ensure_ascii=False, indent=2))}</pre>
        </details>
      </div>
    </div>
    """


# ----------------------------
# build_html
# ----------------------------
def build_html(data: dict) -> str:
    meta = data.get("meta", {}) or {}
    title = meta.get("title", "课程")
    generated_at = meta.get("generated_at") or datetime.now().strftime("%Y-%m-%d")
    watermark = meta.get("watermark", "holo-tutor-agent")

    # v1.1 compat (meta.date + stable defaults)
    title = get_meta_title(data)
    generated_at = get_meta_date(data)
    watermark = get_meta_watermark(data)

    # VisualSpec v1
    sections = data.get("sections", []) or []
    visuals = data.get("visuals", []) or []

    interactive = data.get("interactive", {}) or {}
    params = interactive.get("params", {}) or {}
    domain = interactive.get("domain", {}) or {}
    yrange = interactive.get("range", {}) or {}
    plot_config = interactive.get("plot_config", {}) or {}
    features = interactive.get("features", {}) or {}

    def _num(v, default):
        try:
            return float(v)
        except Exception:
            return default

    def _int(v, default):
        try:
            return int(v)
        except Exception:
            return default

    a_spec = params.get("a", {}) or {}
    b_spec = params.get("b", {}) or {}
    c_spec = params.get("c", {}) or {}

    a0 = _num(a_spec.get("default", 1.0), 1.0)
    b0 = _num(b_spec.get("default", 0.0), 0.0)
    c0 = _num(c_spec.get("default", 0.0), 0.0)

    interactive_cfg = {
        "type": interactive.get("type", ""),
        "domain": {"x_min": _num(domain.get("x_min", -10), -10), "x_max": _num(domain.get("x_max", 10), 10)},
        "range": {"y_min": _num(yrange.get("y_min", -10), -10), "y_max": _num(yrange.get("y_max", 10), 10)},
        "params": {
            "a": {
                "min": _num(a_spec.get("min", -5), -5),
                "max": _num(a_spec.get("max", 5), 5),
                "step": _num(a_spec.get("step", 0.01), 0.01),
                "default": a0,
            },
            "b": {
                "min": _num(b_spec.get("min", -10), -10),
                "max": _num(b_spec.get("max", 10), 10),
                "step": _num(b_spec.get("step", 0.01), 0.01),
                "default": b0,
            },
            "c": {
                "min": _num(c_spec.get("min", -10), -10),
                "max": _num(c_spec.get("max", 10), 10),
                "step": _num(c_spec.get("step", 0.01), 0.01),
                "default": c0,
            },
        },
        "plot_config": {
            "samples": _int(plot_config.get("samples", 800), 800),
            "grid": bool(plot_config.get("grid", True)),
        },
        "features": {
            "show_vertex": bool(features.get("show_vertex", True)),
            "show_axis": bool(features.get("show_axis", True)),
            "show_intercepts": bool(features.get("show_intercepts", False)),
        },
    }

    # Render visuals blocks
    viz_blocks = []
    for idx, v in enumerate(visuals):
        vtype = (v.get("type") or "").lower()
        if vtype in ("flow", "structure", "cycle"):
            viz_blocks.append(render_visual_mermaid(v))
        elif vtype == "plot":
            viz_blocks.append(render_visual_plot(v, idx))
        elif vtype == "cards":
            viz_blocks.append(render_visual_cards(v))
        else:
            viz_blocks.append(render_visual_unknown(v))
    viz_html = "\n".join(viz_blocks)

    # Render sections
    section_html = []
    for sec in sections:
        st = escape_html(sec.get("title", ""))
        content_md = get_content_md(sec)
        content_html = md_to_basic_html(content_md)
        sid = escape_html(sec.get("id", ""))
        section_html.append(f"""
        <details class="section" open>
          <summary><span class="caret">▼</span> {st}</summary>
          <div class="section-body" id="{sid}">
            {content_html}
          </div>
        </details>
        """)
    sections_html = "\n".join(section_html)

    # Interactive block (if present)
    has_interactive = isinstance(params, dict) and all(k in params for k in ("a", "b", "c"))

    interactive_html = ""
    if has_interactive:
        payload = escape_html(json.dumps(interactive_cfg, ensure_ascii=False))
        interactive_html = f"""
        <div class="card">
          <h2 class="card-title">交互可视化： y = ax² + bx + c</h2>
          <div class="grid-2">
            <div class="chart-wrap">
              <canvas id="parabolaCanvas" width="860" height="420" data-interactive="{payload}"></canvas>
            </div>
            <div class="controls">
              <div class="ctrl">
                <div class="ctrl-row">
                  <div class="ctrl-label">二次项系数 a：</div>
                  <div class="ctrl-val" id="valA">{a0:.2f}</div>
                </div>
                <input type="range" id="sliderA" min="{interactive_cfg['params']['a']['min']}" max="{interactive_cfg['params']['a']['max']}" step="{interactive_cfg['params']['a']['step']}" value="{a0}">
              </div>

              <div class="ctrl">
                <div class="ctrl-row">
                  <div class="ctrl-label">一次项系数 b：</div>
                  <div class="ctrl-val" id="valB">{b0:.2f}</div>
                </div>
                <input type="range" id="sliderB" min="{interactive_cfg['params']['b']['min']}" max="{interactive_cfg['params']['b']['max']}" step="{interactive_cfg['params']['b']['step']}" value="{b0}">
              </div>

              <div class="ctrl">
                <div class="ctrl-row">
                  <div class="ctrl-label">常数项 c：</div>
                  <div class="ctrl-val" id="valC">{c0:.2f}</div>
                </div>
                <input type="range" id="sliderC" min="{interactive_cfg['params']['c']['min']}" max="{interactive_cfg['params']['c']['max']}" step="{interactive_cfg['params']['c']['step']}" value="{c0}">
              </div>

              <div class="hint">
                拖动滑块调整系数，观察抛物线的开口方向、顶点位置与整体平移变化。
              </div>
            </div>
          </div>
        </div>
        """

    html = f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{escape_html(title)}</title>
  <style>
    :root {{
      --bg: #f6f8fb;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #667085;
      --border: rgba(0,0,0,.06);
      --shadow: 0 6px 18px rgba(0,0,0,.06);
      --brand: #2563eb;
    }}

    body {{
      margin:0;
      font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
      background: var(--bg);
      color: var(--text);
      position: relative;
    }}

    /* Watermark */
    body::before {{
      content: "{escape_html(watermark)}";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: 0.08;
      font-size: 28px;
      transform: rotate(-22deg);
      display: grid;
      place-items: center;
      background-image:
        repeating-linear-gradient(
          -22deg,
          rgba(0,0,0,0.12) 0,
          rgba(0,0,0,0.12) 2px,
          transparent 2px,
          transparent 140px
        );
      mix-blend-mode: multiply;
    }}

    .container {{
      max-width: 1100px;
      margin: 26px auto;
      padding: 0 16px 60px;
      position: relative;
      z-index: 1;
    }}

    .hero {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 18px 18px;
      box-shadow: var(--shadow);
      margin-bottom: 16px;
    }}

    .hero h1 {{
      margin: 0;
      font-size: 30px;
      letter-spacing: 0.2px;
    }}

    .meta {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }}

    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 16px;
      box-shadow: var(--shadow);
      margin: 16px 0;
    }}

    .card-title {{
      margin: 0 0 12px 0;
      font-size: 18px;
    }}

    .grid-2 {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 16px;
    }}
    @media(max-width: 960px) {{
      .grid-2 {{ grid-template-columns: 1fr; }}
    }}

    .chart-wrap {{
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
      background: #fff;
    }}

    .controls .ctrl {{
      margin-bottom: 14px;
    }}
    .ctrl-row {{
      display:flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 6px;
    }}
    .ctrl-label {{
      color: var(--muted);
      font-size: 13px;
    }}
    .ctrl-val {{
      font-weight: 700;
      color: var(--brand);
      font-variant-numeric: tabular-nums;
    }}

    input[type="range"] {{
      width: 100%;
    }}

    .hint {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.4;
    }}

    .section {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: var(--shadow);
      margin: 14px 0;
      overflow: hidden;
    }}

    summary {{
      cursor: pointer;
      padding: 14px 16px;
      font-weight: 700;
      list-style: none;
      display:flex;
      gap:10px;
      align-items:center;
    }}
    summary::-webkit-details-marker {{ display:none; }}
    .caret {{ color: var(--muted); font-weight: 900; }}

    .section-body {{
      padding: 0 16px 16px 16px;
      color: #111827;
      line-height: 1.6;
    }}
    .section-body p {{ margin: 8px 0; }}
    .p-spacer {{ height: 10px; }}
    .section-body ul {{ margin: 8px 0 8px 22px; }}

    pre.code {{
      background: #0b1220;
      color: #e5e7eb;
      padding: 12px;
      border-radius: 12px;
      overflow:auto;
    }}

    /* Visuals */
    .viz-card {{
      background:#fff;
      border:1px solid var(--border);
      border-radius:16px;
      padding:16px;
      margin:16px 0;
      box-shadow: var(--shadow);
    }}
    .viz-title {{ font-size:18px; font-weight:800; margin-bottom:4px; }}
    .viz-caption {{ color: var(--muted); font-size:13px; margin-bottom:10px; }}
    .viz-body {{ overflow:auto; }}
    .viz-src pre {{
      white-space: pre-wrap;
      background: #0b1220;
      color: #e5e7eb;
      padding: 12px;
      border-radius: 12px;
      overflow:auto;
    }}
    .warn {{
      background: #fff7ed;
      border: 1px solid rgba(249,115,22,.25);
      color: #7c2d12;
      padding: 10px 12px;
      border-radius: 12px;
      margin-bottom: 10px;
      font-size: 13px;
    }}

    /* plot canvas */
    .plot-canvas {{
      width: 100%;
      height: 360px;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: #fff;
      display: block;
    }}

    /* flip cards */
    .flip-grid {{
      display:grid;
      grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
      gap:12px;
    }}
    .flip-card {{
      perspective:1000px;
      cursor:pointer;
      user-select:none;
    }}
    .flip-inner {{
      position:relative;
      width:100%;
      min-height:170px;
      transform-style:preserve-3d;
      transition:transform .5s;
    }}
    .flip-card.flipped .flip-inner {{ transform:rotateY(180deg); }}
    .flip-front,.flip-back {{
      position:absolute; inset:0;
      border:1px solid var(--border);
      border-radius:16px;
      padding:14px;
      backface-visibility:hidden;
      display:flex;
      flex-direction:column;
      justify-content:space-between;
    }}
    .flip-front {{ background:#f8fafc; }}
    .flip-back {{ background:#eef6ff; transform:rotateY(180deg); }}
    .flip-label {{ font-weight:800; color:#1f2937; }}
    .flip-text {{ font-size:14px; color:#111827; line-height:1.45; margin-top:8px; flex:1; }}
    .flip-tip {{ font-size:12px; color: var(--muted); margin-top:12px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="hero">
      <h1>{escape_html(title)}</h1>
      <div class="meta">生成时间：{escape_html(generated_at)} ｜ Watermark: {escape_html(watermark)}</div>
    </div>

    {interactive_html}

    {viz_html}

    {sections_html}
  </div>

  <!-- Mermaid (optional). If unavailable/offline, visuals still show source. -->
  <script>
    (function initMermaidIfPresent(){{
      const hasMermaid = document.querySelector(".mermaid");
      if(!hasMermaid) return;

      function init(){{
        if(!window.mermaid) return;
        try {{
          window.mermaid.initialize({{ startOnLoad: true, theme: "default" }});
        }} catch(e) {{}}
      }}

      if(window.mermaid) {{ init(); return; }}

      // Load local asset if provided (no CDN dependency by default).
      const s = document.createElement("script");
      s.src = "assets/mermaid.min.js";
      s.onload = init;
      s.onerror = function(){{ /* keep source text */ }};
      document.head.appendChild(s);
    }})();
  </script>

  <script>
    // --------- Plot renderer (visuals type=plot) ----------
    function drawPlotCanvas(canvas){{
      const payload = canvas.getAttribute("data-plot");
      if(!payload) return;

      let data;
      try{{ data = JSON.parse(payload); }}catch(e){{ return; }}

      const series = (data.series || []);
      if(series.length === 0) return;

      // set real pixels based on CSS size for crisp lines
      const cssW = canvas.clientWidth || 800;
      const cssH = canvas.clientHeight || 360;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(cssW * dpr);
      canvas.height = Math.floor(cssH * dpr);

      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr,0,0,dpr,0,0);
      ctx.clearRect(0,0,cssW,cssH);

      // bounds
      let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity;
      series.forEach(s=>{{
        (s.x||[]).forEach(v=>{{ xmin=Math.min(xmin,v); xmax=Math.max(xmax,v); }});
        (s.y||[]).forEach(v=>{{ ymin=Math.min(ymin,v); ymax=Math.max(ymax,v); }});
      }});
      if(!isFinite(xmin)||!isFinite(ymin)) return;
      if(xmin===xmax) xmax=xmin+1;
      if(ymin===ymax) ymax=ymin+1;

      const pad=42;
      const X = x=> pad + (x-xmin)*(cssW-2*pad)/(xmax-xmin);
      const Y = y=> cssH-pad - (y-ymin)*(cssH-2*pad)/(ymax-ymin);

      // axes
      ctx.globalAlpha = 0.9;
      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(0,0,0,0.25)";
      ctx.beginPath();
      ctx.moveTo(pad, pad);
      ctx.lineTo(pad, cssH-pad);
      ctx.lineTo(cssW-pad, cssH-pad);
      ctx.stroke();

      // labels
      ctx.fillStyle = "rgba(0,0,0,0.65)";
      ctx.font = "12px sans-serif";
      ctx.fillText(data.y_label || "y", 10, pad);
      ctx.fillText(data.x_label || "x", cssW-pad+10, cssH-pad+4);

      // draw series
      ctx.strokeStyle = "#2563eb";
      ctx.lineWidth = 2;

      series.forEach(s=>{{
        const xs = s.x||[], ys=s.y||[];
        ctx.beginPath();
        for(let i=0;i<Math.min(xs.length, ys.length);i++) {{
          const cx = X(xs[i]);
          const cy = Y(ys[i]);
          if(i===0) ctx.moveTo(cx,cy); else ctx.lineTo(cx,cy);
        }}
        ctx.stroke();
      }});
    }}

    document.querySelectorAll("canvas[data-plot]").forEach(drawPlotCanvas);


    // --------- Interactive parabola module (data-driven) ----------
    (function initParabolaIfPresent(){{
      const canvas = document.getElementById("parabolaCanvas");
      const sa = document.getElementById("sliderA");
      const sb = document.getElementById("sliderB");
      const sc = document.getElementById("sliderC");
      if(!canvas || !sa || !sb || !sc) return;

      let cfg = {{}};
      try {{
        cfg = JSON.parse(canvas.getAttribute("data-interactive") || "{{}}") || {{}};
      }} catch(e) {{
        cfg = {{}};
      }}

      const xMin = Number(cfg?.domain?.x_min ?? -10);
      const xMax = Number(cfg?.domain?.x_max ?? 10);
      const yMin = Number(cfg?.range?.y_min ?? -10);
      const yMax = Number(cfg?.range?.y_max ?? 10);
      const samples = Math.max(10, parseInt(cfg?.plot_config?.samples ?? 800, 10));
      const grid = Boolean(cfg?.plot_config?.grid ?? true);
      const showVertex = Boolean(cfg?.features?.show_vertex ?? true);
      const showAxis = Boolean(cfg?.features?.show_axis ?? true);
      const showIntercepts = Boolean(cfg?.features?.show_intercepts ?? false);

      const cssW = canvas.clientWidth || canvas.width || 860;
      const cssH = canvas.clientHeight || canvas.height || 420;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(cssW * dpr);
      canvas.height = Math.floor(cssH * dpr);

      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      function safeDiv(num, den, fallback) {{
        return den === 0 ? fallback : (num / den);
      }}

      function toCanvasX(x) {{
        return safeDiv((x - xMin) * cssW, (xMax - xMin), cssW / 2);
      }}
      function toCanvasY(y) {{
        return safeDiv((yMax - y) * cssH, (yMax - yMin), cssH / 2);
      }}

      function drawAxes() {{
        ctx.strokeStyle = "rgba(0,0,0,0.25)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        if(xMin < 0 && xMax > 0) {{
          const ax = toCanvasX(0);
          ctx.moveTo(ax, 0); ctx.lineTo(ax, cssH);
        }}
        if(yMin < 0 && yMax > 0) {{
          const ay = toCanvasY(0);
          ctx.moveTo(0, ay); ctx.lineTo(cssW, ay);
        }}
        ctx.stroke();
      }}

      function drawGrid() {{
        ctx.clearRect(0,0,cssW,cssH);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0,0,cssW,cssH);

        if(grid) {{
          ctx.strokeStyle = "rgba(0,0,0,0.06)";
          ctx.lineWidth = 1;
          const step = 40;
          for(let x=0; x<=cssW; x+=step) {{
            ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,cssH); ctx.stroke();
          }}
          for(let y=0; y<=cssH; y+=step) {{
            ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(cssW,y); ctx.stroke();
          }}
        }}

        drawAxes();
      }}

      function drawPoint(cx, cy, label) {{
        ctx.fillStyle = "#111827";
        ctx.beginPath(); ctx.arc(cx, cy, 4, 0, Math.PI*2); ctx.fill();
        if(label) {{
          ctx.fillStyle = "rgba(17,24,39,0.7)";
          ctx.font = "12px sans-serif";
          ctx.fillText(label, cx + 8, cy - 8);
        }}
      }}

      function drawParabola(a,b,c) {{
        drawGrid();

        // curve
        ctx.strokeStyle = "#2563eb";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        let first = true;
        for(let i=0; i<=samples; i++) {{
          const t = safeDiv(i, samples, 0);
          const x = xMin + (xMax - xMin) * t;
          const y = a*x*x + b*x + c;
          const cx = toCanvasX(x);
          const cy = toCanvasY(y);
          if(first) {{ ctx.moveTo(cx,cy); first=false; }}
          else ctx.lineTo(cx,cy);
        }}
        ctx.stroke();

        // features
        if(showVertex || showAxis) {{
          let vx = 0;
          if(a !== 0) vx = -b/(2*a);
          const vy = a*vx*vx + b*vx + c;
          const px = toCanvasX(vx);
          const py = toCanvasY(vy);

          if(showAxis) {{
            ctx.strokeStyle = "rgba(37,99,235,0.45)";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(px, 0);
            ctx.lineTo(px, cssH);
            ctx.stroke();
          }}

          if(showVertex) {{
            drawPoint(px, py, "V(" + vx.toFixed(2) + ", " + vy.toFixed(2) + ")");
          }}
        }}

        if(showIntercepts) {{
          // y-intercept at x=0
          const y0 = c;
          drawPoint(toCanvasX(0), toCanvasY(y0), "y-intercept");

          // x-intercepts: ax^2 + bx + c = 0
          const d = b*b - 4*a*c;
          if(a !== 0 && d >= 0) {{
            const sqrtD = Math.sqrt(d);
            const x1 = (-b + sqrtD) / (2*a);
            const x2 = (-b - sqrtD) / (2*a);
            drawPoint(toCanvasX(x1), toCanvasY(0), "x1=" + x1.toFixed(2));
            drawPoint(toCanvasX(x2), toCanvasY(0), "x2=" + x2.toFixed(2));
          }}
        }}
      }}

      function update() {{
        const a = parseFloat(sa.value);
        const b = parseFloat(sb.value);
        const c = parseFloat(sc.value);
        document.getElementById("valA").textContent = a.toFixed(2);
        document.getElementById("valB").textContent = b.toFixed(2);
        document.getElementById("valC").textContent = c.toFixed(2);
        drawParabola(a,b,c);
      }}

      sa.addEventListener("input", update);
      sb.addEventListener("input", update);
      sc.addEventListener("input", update);

      update();
    }})();
  </script>
</body>
</html>
"""
    return html


# ----------------------------
# Main
# ----------------------------
def main():
    import argparse
    import sys

    try:
        sys.stdout.reconfigure(errors="backslashreplace")
        sys.stderr.reconfigure(errors="backslashreplace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="VisualSpec builder (HTML/DOCX/PDF/ZIP)")
    parser.add_argument("json_path", help="Path to course_data.json (VisualSpec)")
    parser.add_argument(
        "--outdir",
        default="output",
        help="Output directory (if relative: resolved against input JSON folder)",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Comma-separated exports override: html,lecture_docx,quiz_docx,pdf,zip",
    )
    parser.add_argument("--validate-only", action="store_true", help="Validate spec and exit")
    args = parser.parse_args()

    with open(args.json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    spec_hash = compute_spec_hash(data)
    data = normalize_visual_spec(data)

    spec_version = str(data.get("spec_version") or "")
    try:
        if spec_version.startswith("1.1") or spec_version.startswith("v1.1"):
            validate_visual_spec_v1_1(data)
        else:
            print("[WARN] spec_version is not v1.1; schema validation skipped.")
    except VisualSpecValidationError as e:
        print(f"[ERROR] VisualSpec validation failed: {e}")
        sys.exit(1)

    if args.validate_only:
        print("[SUCCESS] VisualSpec validation passed.")
        return

    outdir = resolve_outdir(args.json_path, args.outdir)
    os.makedirs(outdir, exist_ok=True)

    only = parse_only_list(args.only)
    exports = normalize_exports(data.get("exports"), only=only)

    title_safe = sanitize_filename_component(get_meta_title(data))

    outputs: List[str] = []

    # 1) HTML
    if exports["html"]:
        out_html = os.path.join(outdir, "course_interactive.html")
        if not safe_remove(out_html):
            out_html = os.path.join(outdir, f"course_interactive_{now_stamp()}.html")
        html = build_html(data)
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(html)
        outputs.append(os.path.basename(out_html))
        print(f"[SUCCESS] HTML generated: {out_html}")

    # 2) Lecture DOCX
    if exports["lecture_docx"]:
        out_docx = os.path.join(outdir, f"{title_safe}_讲稿.docx")
        if not safe_remove(out_docx):
            out_docx = os.path.join(outdir, f"{title_safe}_讲稿_{now_stamp()}.docx")
        render_lecture_docx(data, out_docx)
        outputs.append(os.path.basename(out_docx))
        print(f"[SUCCESS] Lecture DOCX generated: {out_docx}")

    # 3) Quiz DOCX
    if exports["quiz_docx"]:
        out_quiz = os.path.join(outdir, f"{title_safe}_习题集.docx")
        if not safe_remove(out_quiz):
            out_quiz = os.path.join(outdir, f"{title_safe}_习题集_{now_stamp()}.docx")
        render_quiz_docx(data, out_quiz)
        outputs.append(os.path.basename(out_quiz))
        print(f"[SUCCESS] Quiz DOCX generated: {out_quiz}")

    # 4) PDF
    if exports["pdf"]:
        out_pdf = os.path.join(outdir, "course_notes.pdf")
        if not safe_remove(out_pdf):
            out_pdf = os.path.join(outdir, f"course_notes_{now_stamp()}.pdf")
        render_pdf(data, out_pdf)
        outputs.append(os.path.basename(out_pdf))
        print(f"[SUCCESS] PDF generated: {out_pdf}")

    zip_name_final = None
    if exports["zip"]:
        zip_name_final = exports["zip_name"]
        zip_path = os.path.join(outdir, zip_name_final)
        if not safe_remove(zip_path):
            root, _ext = os.path.splitext(zip_name_final)
            zip_name_final = f"{root}_{now_stamp()}.zip"

    # 5) manifest.json (always)
    manifest_path = write_manifest(
        outdir,
        files=outputs,
        spec_version=spec_version,
        builder_version=BUILDER_VERSION,
        spec_hash=spec_hash,
        zip_name=zip_name_final,
    )
    print(f"[SUCCESS] Manifest generated: {manifest_path}")

    # 6) ZIP (optional)
    if zip_name_final:
        res = pack(outdir, zip_name_final, files=outputs, manifest_path=manifest_path)
        print(f"[SUCCESS] ZIP generated: {res['zip']}")


if __name__ == "__main__":
    main()
