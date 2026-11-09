from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas


def _watermark_page(width: float, height: float, text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.saveState()
    c.setFillColor(Color(0.75, 0.75, 0.75, alpha=0.35))
    c.setFont("Helvetica-Bold", 48)
    c.translate(width / 2, height / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, text)
    c.restoreState()
    c.save()
    return buf.getvalue()


def apply_draft_watermark(src: Path, dest: Path, text: str = "ЧЕРНОВИК") -> Path:
    reader = PdfReader(str(src))
    writer = PdfWriter()
    for page in reader.pages:
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        wm = PdfReader(io.BytesIO(_watermark_page(w, h, text)))
        page.merge_page(wm.pages[0])
        writer.add_page(page)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        writer.write(f)
    return dest
