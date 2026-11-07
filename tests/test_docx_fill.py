import zipfile
from pathlib import Path

import pytest

from closer.documents.docx_fill import TemplateError, fill_docx, template_fields

T = Path(__file__).resolve().parents[1] / "templates" / "uslugi"


@pytest.mark.parametrize("name", ["contract", "act"])
def test_fill_all_fields(tmp_path, name):
    tpl = T / f"{name}.docx"
    keys = template_fields(tpl)
    values = {k: f"<{k}>" for k in keys}
    values["customer_details"] = "строка 1\nстрока 2"
    out = fill_docx(tpl, values, tmp_path / "out.docx")
    xml = zipfile.ZipFile(out).read("word/document.xml").decode()
    for k in keys:
        assert f"&lt;{k}&gt;" in xml or k == "customer_details"
    assert "<w:sdt>" not in xml and "<w:tag " not in xml


def test_missing_value_fails(tmp_path):
    with pytest.raises(TemplateError):
        fill_docx(T / "contract.docx", {"price": "1"}, tmp_path / "out.docx")


def test_template_fields_match_schema():
    import json
    schema = json.loads((T / "fields.json").read_text(encoding="utf-8"))
    for doc in ("contract", "act"):
        assert set(template_fields(T / f"{doc}.docx")) == set(schema["documents"][doc]["fields"])
