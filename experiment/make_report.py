r"""Render docs/实验报告.md into a .docx next to the course deck.

Only the Markdown subset used by the report is supported: headings, paragraphs
(with **bold** spans), bullet lists, pipe tables, fenced code blocks and
images.  That keeps the report editable as text while still producing a Word
file that can be submitted or exported to PDF.

NOTE: this builds the *body* only.  The submitted file adds a cover page
(logo + 课程/作者/论文信息) that is maintained inside the .docx; regenerating
overwrites it, so copy the cover back or ask for the cover to be scripted too.

Run:  PYTHONPATH=. python experiment/make_report.py
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs" / "实验报告.md"
DST = REPO.parent / "Bonsai_复现实验报告.docx"

BODY_FONT = "宋体"
HEAD_FONT = "黑体"
CODE_FONT = "Consolas"


def set_font(run, name: str, size: float, bold: bool = False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), name)


def add_paragraph(doc, text: str, size: float = 10.5, indent: bool = True,
                  font: str = BODY_FONT, align=None, space_after: float = 6):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Pt(21)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.35
    if align is not None:
        p.alignment = align
    add_runs(p, text, size, font)
    return p


TOKEN = re.compile(r"(\*\*.+?\*\*|`.+?`)")


def add_runs(p, text: str, size: float, font: str = BODY_FONT):
    """Split inline **bold** and `code` spans and render them accordingly."""
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = p.add_run(part[2:-2])
            set_font(run, font, size, bold=True)
        elif part.startswith("`") and part.endswith("`"):
            run = p.add_run(part[1:-1])
            set_font(run, CODE_FONT, size - 0.5)
        else:
            run = p.add_run(part)
            set_font(run, font, size)


def add_heading(doc, text: str, level: int, first: bool = False):
    sizes = {1: 16, 2: 14, 3: 12}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 2 else 12)
    p.paragraph_format.space_after = Pt(8)
    if first:
        sizes[1] = 20
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_font(run, HEAD_FONT, sizes.get(level, 12), bold=True)


def add_table(doc, rows: list[list[str]]):
    if not rows:
        return
    ncol = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=ncol)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r, row in enumerate(rows):
        for c in range(ncol):
            cell = table.cell(r, c)
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if (r == 0 or c > 0) else WD_ALIGN_PARAGRAPH.LEFT
            cell_size = 9 if ncol <= 4 else 8.5
            add_runs(p, (row[c] if c < len(row) else "").replace("`", ""), cell_size)
            if r == 0:
                for run in p.runs:
                    run.font.bold = True
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_image(doc, path: Path, caption: str):
    if not path.exists():
        print(f"  !! missing image {path}")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Cm(15.5))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cap.add_run(caption)
    set_font(run, BODY_FONT, 9, color=RGBColor(0x55, 0x55, 0x55))


def add_code(doc, block: list[str]):
    for line in block:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.1
        p.paragraph_format.left_indent = Pt(18)
        run = p.add_run(line)
        set_font(run, CODE_FONT, 9)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def main() -> None:
    md = SRC.read_text().splitlines()
    doc = Document()

    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.5)
    sec.top_margin = sec.bottom_margin = Cm(2.2)

    footer_p = sec.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run_el = OxmlElement("w:r")
    text_el = OxmlElement("w:t")
    text_el.text = "1"
    run_el.append(text_el)
    fld.append(run_el)
    footer_p._p.append(fld)

    doc.core_properties.title = "Bonsai 图凝缩算法复现实验报告"
    doc.core_properties.author = "数据可视化课程大作业"

    style = doc.styles["Normal"]
    style.font.name = BODY_FONT
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

    i = 0
    while i < len(md):
        line = md[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            add_heading(doc, stripped[level:].strip(), level,
                        first=(level == 1 and not doc.paragraphs[1:]))
            i += 1
            continue

        if set(stripped) <= {"-", "*"} and len(stripped) >= 3:
            i += 1
            continue

        if stripped.startswith("!["):
            m = re.match(r"!\[(.*?)\]\((.*?)\)", stripped)
            if m:
                add_image(doc, (SRC.parent / m.group(2)).resolve(), m.group(1))
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            block = []
            while i < len(md) and not md[i].strip().startswith("```"):
                block.append(md[i].rstrip())
                i += 1
            i += 1
            add_code(doc, block)
            continue

        if stripped.startswith("|"):
            rows = []
            while i < len(md) and md[i].strip().startswith("|"):
                cells = [c.strip() for c in md[i].strip().strip("|").split("|")]
                if not all(set(c) <= {"-", ":", " "} and c for c in cells):
                    rows.append(cells)
                i += 1
            add_table(doc, rows)
            continue

        if stripped.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(18)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run(stripped[2:])
            set_font(run, BODY_FONT, 9.5, color=RGBColor(0x6f, 0x6f, 0x6f))
            i += 1
            continue

        if stripped.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(3)
            body = stripped[2:]
            if body.startswith("[x] "):
                body = "✓ " + body[4:]
            add_runs(p, body, 10.5)
            i += 1
            continue

        add_paragraph(doc, stripped)
        i += 1

    doc.save(str(DST))
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()