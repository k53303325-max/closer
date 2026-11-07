"""Fill a Closer DOCX template by content-control tags and render it to PDF.

Templates are the author's Word files. Every field is a content control (w:sdt)
whose tag (w:tag) is the field key, e.g. "price", "customer". This module:
  1. replaces the text of each tagged control with the value,
  2. removes the control wrapper so the final document is plain text,
  3. fails if any tagged field is left unfilled,
  4. converts the result to PDF with LibreOffice.

Text, styles and layout of the template are never changed.
"""
from __future__ import annotations

import copy
import hashlib
import io
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def q(tag: str) -> str:
    return f"{{{W}}}{tag}"


class TemplateError(ValueError):
    pass


def _outer_sdts(root):
    return [s for s in root.iter(q("sdt")) if not s.xpath("ancestor::w:sdt", namespaces=NS)]


def _tag(sdt) -> str | None:
    t = sdt.find("w:sdtPr/w:tag", NS)
    return t.get(q("val")) if t is not None and t.get(q("val")) else None


def template_fields(path: str | Path) -> list[str]:
    """Keys of all tagged fields in a template, in document order (duplicates kept once)."""
    root = etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    seen: list[str] = []
    for s in _outer_sdts(root):
        k = _tag(s)
        if k and k not in seen:
            seen.append(k)
    return seen


def _base_rpr(sdt):
    """Formatting of the field's first run, without placeholder highlight/hidden flags."""
    for r in sdt.iter(q("r")):
        rp = r.find("w:rPr", NS)
        if r.find("w:t", NS) is not None:
            rp = copy.deepcopy(rp) if rp is not None else etree.Element(q("rPr"))
            for tag in ("highlight", "vanish", "rStyle", "shd"):
                for e in rp.findall(f"w:{tag}", NS):
                    rp.remove(e)
            return rp
    return etree.Element(q("rPr"))


def _runs(value: str, rpr):
    """One run per line, separated by line breaks (for multi-line requisites)."""
    out = []
    for i, line in enumerate(value.split("\n")):
        r = etree.Element(q("r"))
        r.append(copy.deepcopy(rpr))
        if i:
            etree.SubElement(r, q("br"))
        t = etree.SubElement(r, q("t"))
        t.set(XML_SPACE, "preserve")
        t.text = line
        out.append(r)
    return out


def _left_align(p):
    """Multi-line values (requisites) look broken when the paragraph is justified."""
    ppr = p.find("w:pPr", NS)
    if ppr is None:
        ppr = etree.Element(q("pPr"))
        p.insert(0, ppr)
    jc = ppr.find("w:jc", NS)
    if jc is None:
        jc = etree.SubElement(ppr, q("jc"))
    jc.set(q("val"), "left")


def _fill_sdt(sdt, value: str):
    content = sdt.find("w:sdtContent", NS)
    if "\n" in value:
        host = content.find("w:p", NS)
        if host is None:
            host = sdt.xpath("ancestor::w:p[1]", namespaces=NS)[0]
        _left_align(host)
    rpr = _base_rpr(sdt)
    block = content.find("w:p", NS) is not None  # block-level control (whole paragraph)
    if block:
        p = content.find("w:p", NS)
        for el in list(p):
            if el.tag != q("pPr"):
                p.remove(el)
        for r in _runs(value, rpr):
            p.append(r)
        for extra in content.findall("w:p", NS)[1:]:
            content.remove(extra)
    else:
        for el in list(content):
            content.remove(el)
        for r in _runs(value, rpr):
            content.append(r)
    # unwrap: put content in place of the control
    parent = sdt.getparent()
    idx = parent.index(sdt)
    for ch in list(content):
        parent.insert(idx, ch)
        idx += 1
    parent.remove(sdt)


def fill_docx(template: str | Path, values: dict[str, str], out: str | Path) -> Path:
    """Fill every tagged field. Raises TemplateError if a template field has no value."""
    template, out = Path(template), Path(out)
    with zipfile.ZipFile(template) as zin:
        root = etree.fromstring(zin.read("word/document.xml"))
        missing = sorted({k for s in _outer_sdts(root) if (k := _tag(s)) and k not in values})
        if missing:
            raise TemplateError(f"{template.name}: no values for {', '.join(missing)}")
        for s in _outer_sdts(root):
            k = _tag(s)
            if k:
                v = values[k]
                if v is None or str(v).strip() == "":
                    raise TemplateError(f"{template.name}: empty value for {k}")
                _fill_sdt(s, str(v))
        # placeholder shading is part of the template look, not of a signed document
        for h in root.xpath("//w:highlight[@w:val='lightGray']", namespaces=NS):
            h.getparent().remove(h)
        leftovers = [s for s in _outer_sdts(root) if _tag(s)]
        if leftovers:
            raise TemplateError(f"{template.name}: unfilled fields remain")
        xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = xml if item.filename == "word/document.xml" else zin.read(item.filename)
                zout.writestr(item, data)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(buf.getvalue())
    return out


def to_pdf(docx: str | Path, out_dir: str | Path | None = None, timeout: int = 60) -> Path:
    """Convert DOCX to PDF with LibreOffice (soffice must be installed in the container)."""
    docx = Path(docx)
    out_dir = Path(out_dir or docx.parent)
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("LibreOffice (soffice) is not installed")
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [soffice, f"-env:UserInstallation=file://{profile}", "--headless",
             "--convert-to", "pdf", "--outdir", str(out_dir), str(docx)],
            check=True, timeout=timeout, capture_output=True,
        )
    return out_dir / (docx.stem + ".pdf")


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()
