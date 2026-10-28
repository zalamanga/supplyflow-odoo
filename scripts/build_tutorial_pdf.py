"""Build the Indonesian tutorial PDF from repository Markdown using ReportLab."""

import argparse
from html import escape
import re
from pathlib import Path
import shutil
from urllib.parse import quote

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Frame, LongTable, PageBreak, PageTemplate,
    Paragraph, Preformatted, Spacer, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "tutorial"
CHAPTERS = [
    "README.md", "01-persiapan-dan-docker.md", "02-kerangka-addon-dan-akses.md",
    "03-model-permintaan-dan-rfq.md", "04-receipt-masalah-dan-retur.md",
    "05-tampilan-workspace-dan-pdf.md", "06-pengujian-dan-debugging.md",
    "07-operasi-dan-latihan.md", "08-indeks-file-dan-fungsi.md",
]
REPOSITORY = "https://github.com/zalamanga/supplyflow-odoo/blob/main/"
INK = colors.HexColor("#202730")
ACCENT = colors.HexColor("#714b67")
MUTED = colors.HexColor("#52606d")
RULE = colors.HexColor("#dce1e7")


def register_fonts():
    candidates = [
        (Path("C:/Windows/Fonts"), "segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "consola.ttf"),
        (Path("/usr/share/fonts/truetype/dejavu"), "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf", "DejaVuSansMono.ttf"),
    ]
    for folder, regular, bold, italic, mono in candidates:
        if all((folder / item).is_file() for item in (regular, bold, italic, mono)):
            for name, filename in (("Guide", regular), ("Guide-Bold", bold), ("Guide-Italic", italic), ("Guide-Mono", mono)):
                pdfmetrics.registerFont(TTFont(name, str(folder / filename)))
            pdfmetrics.registerFontFamily("Guide", normal="Guide", bold="Guide-Bold", italic="Guide-Italic", boldItalic="Guide-Bold")
            return
    raise RuntimeError("Install Segoe UI/Consolas (Windows) or DejaVu Sans/Mono (Linux).")


def source_url(value, source_file):
    if value.startswith(("https://", "http://", "mailto:")):
        return value
    if value.startswith("#"):
        return ""
    file_part, _, anchor = value.partition("#")
    target = (source_file.parent / file_part).resolve()
    try:
        relative = target.relative_to(ROOT).as_posix()
    except ValueError:
        return ""
    return REPOSITORY + quote(relative, safe="/") + ("#" + anchor if anchor else "")


def inline(text, source_file):
    saved = []

    def token(markup):
        saved.append(markup)
        return f"ZZGUIDETOKEN{len(saved)-1}ZZ"

    text = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"`([^`]+)`", lambda m: token(f'<font name="Guide-Mono">{escape(m[1])}</font>'), text)

    def link(match):
        label, target = match.group(1), match.group(2)
        url = source_url(target, source_file)
        return token(f'<link href="{escape(url, quote=True)}" color="#714b67">{escape(label)}</link>' if url else escape(label))

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    for index in reversed(range(len(saved))):
        text = text.replace(f"ZZGUIDETOKEN{index}ZZ", saved[index])
    return text


class TutorialDocument(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=A4, leftMargin=44, rightMargin=44, topMargin=48, bottomMargin=44,
                         title="Membuat ERP Odoo dari Nol - SupplyFlow Office", author="Muhammad Rafik",
                         subject="Tutorial berurutan, penjelasan file dan fungsi SupplyFlow Office")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="guide", frames=[frame], onPage=self.decorate)])
        self.section = "SupplyFlow Office"
        self.bookmark_count = 0

    def beforeDocument(self):
        self.bookmark_count = 0
        self.section = "SupplyFlow Office"

    def decorate(self, canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.line(44, A4[1]-32, A4[0]-44, A4[1]-32)
        canvas.setFillColor(MUTED)
        canvas.setFont("Guide", 8)
        canvas.drawString(44, A4[1]-25, "SUPPLYFLOW OFFICE  /  TUTORIAL ODOO 19")
        canvas.drawString(44, 25, "Panduan kode dan praktik | 28 Oktober 2026")
        canvas.drawRightString(A4[0]-44, 25, str(document.page))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        level = getattr(flowable, "outline_level", None)
        if level is None:
            return
        title = flowable.getPlainText()
        bookmark = f"chapter-{self.bookmark_count}"
        self.bookmark_count += 1
        self.canv.bookmarkPage(bookmark)
        self.canv.addOutlineEntry(title, bookmark, level=level, closed=(level > 0))
        if level == 0:
            self.section = title
        self.notify("TOCEntry", (level, escape(title), self.page, bookmark))


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="GuideBody", fontName="Guide", fontSize=10, leading=14.8, textColor=INK, spaceAfter=7, splitLongWords=1))
    styles.add(ParagraphStyle(name="GuideH1", parent=styles["GuideBody"], fontName="Guide-Bold", fontSize=23, leading=28, spaceBefore=10, spaceAfter=18, keepWithNext=True))
    styles.add(ParagraphStyle(name="GuideH2", parent=styles["GuideBody"], fontName="Guide-Bold", fontSize=14, leading=19, spaceBefore=15, spaceAfter=8, keepWithNext=False, textColor=ACCENT))
    styles.add(ParagraphStyle(name="GuideH3", parent=styles["GuideBody"], fontName="Guide-Bold", fontSize=11, leading=15, spaceBefore=11, spaceAfter=6, keepWithNext=False))
    styles.add(ParagraphStyle(name="GuideCell", parent=styles["GuideBody"], fontSize=8.6, leading=12.2, spaceAfter=0, wordWrap="CJK"))
    styles.add(ParagraphStyle(name="GuideCode", fontName="Guide-Mono", fontSize=7.5, leading=10, leftIndent=8, rightIndent=8, borderPadding=7, backColor=colors.HexColor("#f3f5f7"), spaceBefore=4, spaceAfter=10))
    styles.add(ParagraphStyle(name="GuideQuote", parent=styles["GuideBody"], leftIndent=12, rightIndent=8, textColor=MUTED, borderColor=RULE, borderWidth=0.5, borderPadding=7, spaceBefore=4, spaceAfter=10))
    styles.add(ParagraphStyle(name="GuideList", parent=styles["GuideBody"], leftIndent=13, firstLineIndent=-10, spaceAfter=5))
    return styles


def code_lines(code, available_width, style):
    maximum = max(40, int((available_width-28) / pdfmetrics.stringWidth("M", "Guide-Mono", style.fontSize)))
    lines = []
    for original in code.expandtabs(4).splitlines():
        if not original:
            lines.append("")
            continue
        first = True
        remaining = original
        while len(remaining) > maximum:
            take = maximum if first else maximum-3
            lines.append(("" if first else "  >") + remaining[:take])
            remaining = remaining[take:]
            first = False
        lines.append(("" if first else "  >") + remaining)
    return "\n".join(lines)


def diagram_table(code, styles, width):
    rows = []
    if code.strip().startswith("sequenceDiagram"):
        names = dict(re.findall(r"participant\s+(\w+)\s+as\s+(.+)", code))
        rows.append(["Urutan", "Dari", "Ke", "Pesan / tindakan"])
        for source, target, message in re.findall(r"^\s*(\w+)-+>>?(\w+):\s*(.+)$", code, re.M):
            rows.append([str(len(rows)), names.get(source, source), names.get(target, target), message])
        widths = [width*.07, width*.22, width*.22, width*.49]
    else:
        edges = re.findall(r"^\s*(\w+(?:\[[^\]]+\])?)\s*-->\s*(?:\|([^|]+)\|\s*)?(\w+(?:\[[^\]]+\])?)\s*$", code, re.M)
        names = {}
        for source, _, target in edges:
            for item in (source, target):
                match = re.fullmatch(r"(\w+)\[([^\]]+)\]", item)
                if match:
                    names[match[1]] = match[2]
        rows.append(["Dari", "Aksi / kondisi", "Ke"])
        for source, action, target in edges:
            source_id, target_id = source.split("[")[0], target.split("[")[0]
            rows.append([names.get(source_id, source_id), action or "Langkah berikutnya", names.get(target_id, target_id)])
        widths = [width*.24, width*.40, width*.36]
    if len(rows) < 2:
        raise ValueError("Unsupported diagram syntax; keep the PDF and Markdown flow in sync.")
    table = LongTable([[Paragraph(escape(cell), styles["GuideCell"]) for cell in row] for row in rows], colWidths=widths, repeatRows=1, hAlign="LEFT", spaceAfter=11)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eee8ed")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 7), ("RIGHTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LINEBELOW", (0,0), (-1,-1), .4, RULE),
    ]))
    return table


def markdown_blocks(path, styles, width):
    lines = path.read_text(encoding="utf-8").splitlines()
    result = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("```"):
            language = line[3:].strip()
            code = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index])
                index += 1
            result.append(CondPageBreak(76))
            if language == "mermaid":
                result.append(Paragraph("Alur proses (tabel padanan diagram pada Markdown)", styles["GuideH3"]))
                result.append(diagram_table("\n".join(code), styles, width))
            else:
                result.append(Paragraph(escape(language or "kode"), styles["GuideH3"]))
                result.append(Preformatted(code_lines("\n".join(code), width, styles["GuideCode"]), styles["GuideCode"]))
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            level = len(heading[1])
            paragraph = Paragraph(inline(heading[2], path), styles["GuideH1" if level == 1 else "GuideH2" if level == 2 else "GuideH3"])
            if level <= 2:
                paragraph.outline_level = level-1
            if level > 1:
                result.append(CondPageBreak(86))
            result.append(paragraph)
            index += 1
            continue
        if line.lstrip().startswith("|"):
            rows = []
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                row = lines[index].strip().strip("|")
                cells = [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", row)]
                if not all(re.fullmatch(r":?-{2,}:?", cell or " ") for cell in cells):
                    rows.append(cells)
                index += 1
            columns = max(map(len, rows))
            if columns == 2:
                column_widths = [width*0.38, width*0.62]
            elif columns == 3:
                column_widths = [width*0.23, width*0.32, width*0.45]
            elif columns == 4:
                column_widths = [width*0.12, width*0.27, width*0.28, width*0.33]
            else:
                column_widths = [width/columns]*columns
            table_rows = [[Paragraph(inline(cell, path), styles["GuideCell"]) for cell in row+[""]*(columns-len(row))] for row in rows]
            table = LongTable(table_rows, colWidths=column_widths, repeatRows=1, hAlign="LEFT", spaceBefore=4, spaceAfter=11)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eee8ed")),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 7), ("RIGHTPADDING", (0,0), (-1,-1), 7),
                ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ("LINEBELOW", (0,0), (-1,0), 0.7, RULE),
                ("LINEBELOW", (0,1), (-1,-1), 0.35, RULE),
            ]))
            result.append(table)
            continue
        if line.startswith("<!--"):
            index += 1
            continue
        image = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if image:
            result.append(Paragraph(inline(f"Gambar: [{image[1]}]({image[2]})", path), styles["GuideBody"]))
            index += 1
            continue
        if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
            content = re.sub(r"^\s*[-*]\s+", "• ", line)
            result.append(Paragraph(inline(content.strip(), path), styles["GuideList"]))
            index += 1
            continue
        if line.startswith(">"):
            result.append(Paragraph(inline(line.lstrip("> "), path), styles["GuideQuote"]))
            index += 1
            continue
        paragraph = [line.strip()]
        index += 1
        while index < len(lines) and lines[index].strip() and not re.match(r"^(#|```|\||>|[-*]\s|\d+\.\s|<!--)", lines[index]):
            paragraph.append(lines[index].strip())
            index += 1
        result.append(Paragraph(inline(" ".join(paragraph), path), styles["GuideBody"]))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"output/pdf/supplyflow-office-tutorial.pdf")
    parser.add_argument("--publish-copy", action="store_true", help="Copy identical PDF into docs/tutorial for repository access.")
    arguments = parser.parse_args()
    register_fonts()
    styles = build_styles()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    document = TutorialDocument(arguments.output)
    story = [Spacer(1, 46), Paragraph("MEMBANGUN ADDON ERP", styles["GuideH2"]),
             Paragraph("Odoo dari Nol", styles["GuideH1"]),
             Paragraph("SupplyFlow Office", styles["GuideH2"]),
             Paragraph("Tutorial distributor perlengkapan kantor: dari Docker dan model pertama sampai persetujuan, RFQ, retur pemasok, antarmuka, pengujian, serta backup/restore.", styles["GuideBody"]),
             Spacer(1, 20), Paragraph("Muhammad Rafik | Odoo Community 19 | 28 Oktober 2026", styles["GuideBody"]),
             Spacer(1, 18), Paragraph("Cara memakai: ikuti bab 1-7, lalu gunakan indeks file/fungsi pada bab 8 ketika membuka source. Blok kode panjang dapat terbungkus pada PDF; tanda > di awal baris lanjutan hanya penanda tata letak. Salin kode dari Markdown/source yang ditautkan untuk mempertahankan baris aslinya.", styles["GuideQuote"]),
             PageBreak(), Paragraph("Daftar isi", styles["GuideH1"])]
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle(name="TOC0", fontName="Guide-Bold", fontSize=10.2, leading=15, leftIndent=0, firstLineIndent=0, spaceBefore=8),
                       ParagraphStyle(name="TOC1", fontName="Guide", fontSize=8.8, leading=12.8, leftIndent=13, firstLineIndent=0, spaceBefore=2)]
    story.append(toc)
    for name in CHAPTERS:
        source_file = SOURCE/name
        if not source_file.is_file():
            raise FileNotFoundError(source_file)
        story.append(PageBreak())
        story.extend(markdown_blocks(source_file, styles, document.width))
    document.multiBuild(story)
    if arguments.publish_copy:
        published = SOURCE/"supplyflow-office-tutorial.pdf"
        if arguments.output.resolve() != published.resolve():
            shutil.copyfile(arguments.output, published)
    print(f"Created {arguments.output.resolve()} ({arguments.output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
