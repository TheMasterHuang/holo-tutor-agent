from __future__ import annotations

import os
from typing import Any, Dict, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from visual_spec import get_content_md, get_meta_date, get_meta_title, get_meta_watermark


def _script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _register_cjk_font() -> str:
    """
    Prefer a bundled TTF if provided; otherwise fall back to a built-in CID font.
    """
    candidates = [
        os.path.abspath(os.path.join(_script_dir(), "..", "assets", "fonts", "NotoSansSC-Regular.ttf")),
        os.path.abspath(os.path.join(_script_dir(), "..", "assets", "fonts", "SourceHanSansSC-Regular.ttf")),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont("HoloCJK", path))
            return "HoloCJK"
        except Exception:
            continue

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception:
        return "Helvetica"


def _string_width(text: str, font_name: str, font_size: int) -> float:
    try:
        return pdfmetrics.stringWidth(text, font_name, font_size)
    except Exception:
        return 0.0


def _wrap_line(text: str, font_name: str, font_size: int, max_width: float) -> List[str]:
    if text.strip() == "":
        return [""]
    if _string_width(text, font_name, font_size) <= max_width:
        return [text]

    # For CJK lines without spaces, fallback to character wrapping.
    lines: List[str] = []
    buf = ""
    for ch in text:
        cand = buf + ch
        if _string_width(cand, font_name, font_size) <= max_width:
            buf = cand
        else:
            if buf:
                lines.append(buf)
                buf = ch
            else:
                lines.append(ch)
                buf = ""
    if buf:
        lines.append(buf)
    return lines


def draw_watermark(c: canvas.Canvas, text: str, *, font_name: str):
    w, h = A4
    c.saveState()
    c.translate(w / 2, h / 2)
    c.rotate(30)
    c.setFillGray(0.85)
    c.setFont(font_name, 28)
    for y in range(-600, 650, 120):
        for x in range(-600, 650, 220):
            c.drawString(x, y, text)
    c.restoreState()


def draw_paragraph(
    c: canvas.Canvas,
    x: float,
    y: float,
    text: str,
    *,
    max_width: float,
    font_name: str,
    font_size: int = 11,
    leading: int = 15,
) -> float:
    c.setFont(font_name, font_size)
    for raw in (text or "").replace("\r\n", "\n").split("\n"):
        for line in _wrap_line(raw, font_name, font_size, max_width):
            c.drawString(x, y, line)
            y -= leading
    return y


def render_pdf(course_data: Dict[str, Any], out_pdf_path: str):
    title = get_meta_title(course_data)
    date = get_meta_date(course_data)
    watermark = get_meta_watermark(course_data)

    sections: List[Dict[str, Any]] = course_data.get("lecture_notes") or course_data.get("sections") or []

    font_name = _register_cjk_font()

    c = canvas.Canvas(out_pdf_path, pagesize=A4)
    w, h = A4

    # Cover + TOC
    draw_watermark(c, watermark, font_name=font_name)
    c.setFillGray(0.1)
    c.setFont(font_name, 24)
    c.drawString(25 * mm, h - 35 * mm, title)

    c.setFont(font_name, 11)
    c.setFillGray(0.35)
    c.drawString(25 * mm, h - 45 * mm, f"Date: {date}")
    c.drawString(25 * mm, h - 52 * mm, f"Watermark: {watermark}")

    y = h - 70 * mm
    c.setFillGray(0.15)
    c.setFont(font_name, 14)
    c.drawString(25 * mm, y, "目录")
    y -= 10 * mm

    c.setFont(font_name, 11)
    for i, sec in enumerate(sections, start=1):
        c.drawString(28 * mm, y, f"{i}. {sec.get('title', '')}")
        y -= 7 * mm
        if y < 25 * mm:
            c.showPage()
            draw_watermark(c, watermark, font_name=font_name)
            y = h - 25 * mm

    c.showPage()

    # Body pages
    for sec in sections:
        draw_watermark(c, watermark, font_name=font_name)
        c.setFillGray(0.1)
        c.setFont(font_name, 16)
        c.drawString(20 * mm, h - 25 * mm, sec.get("title", ""))

        c.setFillGray(0.15)
        body = get_content_md(sec)
        y = h - 38 * mm
        y = draw_paragraph(c, 20 * mm, y, body, max_width=w - 40 * mm, font_name=font_name)

        c.showPage()

    c.save()
