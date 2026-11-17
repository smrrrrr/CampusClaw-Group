"""Render the canonical report.md to a two-page PDF reading copy.

Requires reportlab and pypdf in an authoring environment, not the application.
No business data, network requests, or application configuration are used.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from html import escape
from pathlib import Path
from urllib.parse import quote

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/smrrrrr/CampusClaw-Group/blob/main/"


def inline(text: str) -> str:
    """Small renderer for this report's links, bold text and inline paths."""
    pattern = r"(\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|`[^`]+`)"
    parts = []
    for token in re.split(pattern, text):
        if token.startswith("["):
            match = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", token)
            if match:
                label, target = match.groups()
                url = target if target.startswith("https://") else REPO + quote(target, safe="/#")
                parts.append(f'<link href="{escape(url, quote=True)}" color="#185477">{escape(label)}</link>')
                continue
        if token.startswith("**") and token.endswith("**"):
            parts.append(f"<b>{escape(token[2:-2])}</b>")
        elif token.startswith("`") and token.endswith("`"):
            parts.append(f'<font color="#264560">{escape(token[1:-1])}</font>')
        else:
            parts.append(escape(token))
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output/pdf/CampusClaw-project-report.pdf")
    parser.add_argument("--font", type=Path, help="Chinese TrueType font, e.g. simsun.ttc")
    args = parser.parse_args()
    source = ROOT / "report.md"
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8-sig")
    font_path = args.font or Path("C:/Windows/Fonts/simsun.ttc")
    if font_path.exists():
        pdfmetrics.registerFont(TTFont("ReportCJK", str(font_path), subfontIndex=0))
        regular = "ReportCJK"
        bold_path = Path("C:/Windows/Fonts/simhei.ttf")
        if bold_path.exists():
            pdfmetrics.registerFont(TTFont("ReportCJKBold", str(bold_path)))
            bold = "ReportCJKBold"
        else:
            bold = regular
        pdfmetrics.registerFontFamily(regular, normal=regular, bold=bold, italic=regular, boldItalic=bold)
    else:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        regular = bold = "STSong-Light"
        pdfmetrics.registerFontFamily(regular, normal=regular, bold=bold, italic=regular, boldItalic=bold)

    common = dict(fontName=regular, wordWrap="CJK", splitLongWords=True, alignment=TA_LEFT)
    body = ParagraphStyle("body", fontSize=10.1, leading=14.2, spaceAfter=5, **common)
    meta = ParagraphStyle("meta", fontSize=9.1, leading=12.5, spaceAfter=7, textColor=colors.HexColor("#425164"), **common)
    cell = ParagraphStyle("cell", fontSize=9.6, leading=13.3, spaceAfter=0, **common)
    heading = ParagraphStyle("heading", fontSize=11.8, leading=16, spaceBefore=9, spaceAfter=5, keepWithNext=True,
                             fontName=bold, textColor=colors.HexColor("#17324F"))
    title = ParagraphStyle("title", fontSize=19, leading=25, spaceAfter=8, fontName=bold,
                           textColor=colors.HexColor("#17324F"))
    story = []
    lines = text.splitlines()
    idx = 0
    before_first_section = True
    page_width = A4[0] - 76
    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), title))
            idx += 1
            continue
        if line.startswith("## "):
            if line.startswith("## 4."):
                story.append(PageBreak())
            before_first_section = False
            story.append(Paragraph(inline(line[3:]), heading))
            idx += 1
            continue
        if line.startswith("|"):
            rows = []
            while idx < len(lines) and lines[idx].strip().startswith("|"):
                row = [p.strip() for p in lines[idx].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", p) for p in row):
                    rows.append([Paragraph(inline(p), cell) for p in row])
                idx += 1
            table_label = rows[0][0].getPlainText()
            first_col = 58 if "类别" in table_label else 175 if "检查与记录" in table_label else 146
            table = Table(rows, colWidths=[first_col, page_width-first_col], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EEF5")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FB")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), .5, colors.HexColor("#C4D2DE")),
            ]))
            story.extend([table, Spacer(1, 5)])
            continue
        paragraph = [line]
        idx += 1
        while idx < len(lines) and lines[idx].strip() and not lines[idx].startswith(("#", "|")):
            paragraph.append(lines[idx].strip())
            idx += 1
        story.append(Paragraph(inline(" ".join(paragraph)), meta if before_first_section else body))

    args.output.parent.mkdir(parents=True, exist_ok=True)

    def decorate(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D4DCE5"))
        canvas.line(38, 30, A4[0]-38, 30)
        canvas.setFont(regular, 8)
        canvas.setFillColor(colors.HexColor("#607082"))
        canvas.drawString(38, 18, f"CampusClaw | report.md | SHA-256 {digest[:16]}")
        canvas.drawRightString(A4[0]-38, 18, f"{document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(str(args.output), pagesize=A4, leftMargin=38, rightMargin=38,
                                 topMargin=30, bottomMargin=40, title="项目报告 · CampusClaw",
                                 author="CampusClaw-Group", subject=f"Canonical report.md SHA-256 {digest}")
    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    count = len(PdfReader(args.output).pages)
    if count != 2:
        raise SystemExit(f"Expected 2 pages, got {count}; inspect and adjust report before delivery.")
    print(f"PDF created: {args.output}; pages={count}; source_sha256={digest}")


if __name__ == "__main__":
    main()
