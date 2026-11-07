"""Fill both service templates with sample data and render PDFs.

Run from the repo root:  python tools/fill_example.py
Result: out/example/contract.docx|pdf, out/example/act.docx|pdf
Use it as a smoke test after any change to the templates.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from closer.documents.docx_fill import fill_docx, sha256, template_fields, to_pdf  # noqa: E402
from closer.documents.parties import IP, SELF_EMPLOYED, Party, party_details, party_line, sign_name, vat_text  # noqa: E402

T = Path("templates/uslugi")
OUT = Path("out/example")

customer = Party(status=IP, full_name="Петров Петр Петрович", phone="+7 900 111-22-33",
                 inn="771234567890", ogrn="321774600123456", address="г. Москва, ул. Тверская, д. 1",
                 vat_mode="none")
executor = Party(status=SELF_EMPLOYED, full_name="Иванов Иван Иванович", phone="+7 900 000-00-00",
                 passport="4510 123456", inn="500100732259", sbp="+7 900 000-00-00, Т-Банк")

common = {
    "number": "CL-2026-000123",
    "customer": party_line(customer),
    "executor": party_line(executor),
    "services": "разработке логотипа и фирменного стиля",
    "price": "45 000",
    "vat": vat_text(executor),
    "customer_sign": sign_name(customer),
    "executor_sign": sign_name(executor),
}
contract = common | {
    "date": "29.10.2026",
    "term": "до 30.11.2026",
    "payment": "50 % в течение 3 дней после подписания Договора, остальное – в течение 3 дней после подписания Акта",
    "customer_details": party_details(customer),
    "executor_details": party_details(executor),
}
act = common | {
    "date": "28.11.2026",
    "contract_date": "29.10.2026",
    "start": "29.10.2026",
    "end": "28.11.2026",
}

for name, values in (("contract", contract), ("act", act)):
    tpl = T / f"{name}.docx"
    print(name, "fields:", template_fields(tpl))
    docx = fill_docx(tpl, values, OUT / f"{name}.docx")
    pdf = to_pdf(docx)
    print(" ->", pdf, sha256(pdf)[:16])
