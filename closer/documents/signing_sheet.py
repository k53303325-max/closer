"""Simple signing sheet PDF for Stage 3."""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from closer.compat import UTC


def build_signing_sheet_pdf(
    *,
    contract_number: str,
    pdf_sha256: str,
    parties: list[tuple[str, str, datetime | None]],
    pep_version: str,
    out_path: str,
) -> None:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Лист подписания Closer")
    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Договор № {contract_number}")
    y -= 20
    c.drawString(50, y, f"Контрольная сумма документа: {pdf_sha256[:8].upper()}")
    y -= 20
    c.drawString(50, y, f"Версия соглашения о ПЭП: {pep_version}")
    y -= 30
    for role, name, signed_at in parties:
        when = signed_at.strftime("%d.%m.%Y %H:%M UTC") if signed_at else "—"
        c.drawString(50, y, f"{role}: {name}, подпись: {when}")
        y -= 18
    y -= 20
    c.drawString(50, y, "Проверка: отправьте PDF боту через «Проверить документ».")
    c.save()
    with open(out_path, "wb") as f:
        f.write(buf.getvalue())