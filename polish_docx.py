"""Keep each table and figure on one page with its caption.

Quarto cannot set this for Word output, so run this after rendering:

    python polish_docx.py _site/final_report.docx

It edits the .docx in place. For every table row it turns off splitting a
row across pages, and it marks every row except the last as "keep with next",
which is how Word keeps a table (and a caption) together.
"""

import shutil
import sys
import tempfile
import zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def q(tag):
    return f"{{{W}}}{tag}"


def ensure_child(parent, tag, first=False):
    el = parent.find(f"w:{tag}", NS)
    if el is None:
        el = etree.Element(q(tag))
        if first:
            parent.insert(0, el)
        else:
            parent.append(el)
    return el


def keep_next(paragraph):
    ppr = paragraph.find("w:pPr", NS)
    if ppr is None:
        ppr = etree.Element(q("pPr"))
        paragraph.insert(0, ppr)
    if ppr.find("w:keepNext", NS) is None:
        # keepNext goes after pStyle if present
        style = ppr.find("w:pStyle", NS)
        el = etree.Element(q("keepNext"))
        if style is not None:
            style.addnext(el)
        else:
            ppr.insert(0, el)


LONG_TABLE_CHARS = 1150  # tables with more text than this may break between rows


def is_long(tbl):
    return len("".join(tbl.itertext())) > LONG_TABLE_CHARS


def no_row_split(tr):
    trpr = tr.find("w:trPr", NS)
    if trpr is None:
        trpr = etree.Element(q("trPr"))
        # trPr must follow tblPrEx if present, else be first
        prex = tr.find("w:tblPrEx", NS)
        if prex is not None:
            prex.addnext(trpr)
        else:
            tr.insert(0, trpr)
    if trpr.find("w:cantSplit", NS) is None:
        trpr.insert(0, etree.Element(q("cantSplit")))


PPR_ORDER = [
    "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl",
    "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens",
    "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE",
    "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind",
    "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
    "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr",
    "sectPr", "pPrChange",
]


def tidy_paragraph_properties(root):
    """Quarto writes two property blocks on caption paragraphs; Word expects one,
    with its settings in a fixed order. Merge them (later value wins)."""
    parents = {ppr.getparent() for ppr in root.iter(q("pPr"))}
    for p in parents:
        pprs = p.findall("w:pPr", NS)
        if not pprs:
            continue
        position = list(p).index(pprs[0])
        seen = {}
        for ppr in pprs:
            for child in list(ppr):
                if not isinstance(child.tag, str):
                    continue
                name = etree.QName(child).localname
                seen[name] = child  # later value wins, as Word and LibreOffice read it
        merged = etree.Element(q("pPr"))
        for name in sorted(seen, key=lambda n: PPR_ORDER.index(n) if n in PPR_ORDER else 99):
            merged.append(seen[name])
        for ppr in pprs:
            p.remove(ppr)
        p.insert(position, merged)


def tidy_page_margins(root):
    for pgmar in root.iter(q("pgMar")):
        for attr, val in (("header", "720"), ("footer", "720"), ("gutter", "0")):
            if pgmar.get(q(attr)) is None:
                pgmar.set(q(attr), val)



def unwrap_captioned_tables(root):
    """Quarto places a captioned table inside a one-cell table (caption, then the
    real table). Word and LibreOffice cannot keep a caption in that outer cell
    with the table below it, so lift the caption and table out of the wrapper
    and mark the caption "keep with next"."""
    for outer in list(root.iter(q("tbl"))):
        rows = outer.findall("w:tr", NS)
        if len(rows) != 1:
            continue
        cells = rows[0].findall("w:tc", NS)
        if len(cells) != 1 or cells[0].find("w:tbl", NS) is None:
            continue
        parent = outer.getparent()
        if parent is None:
            continue
        kids = [k for k in cells[0] if not (isinstance(k.tag, str) and etree.QName(k).localname == "tcPr")]
        # drop the empty paragraph Word requires at the end of a cell
        while kids and isinstance(kids[-1].tag, str) and etree.QName(kids[-1]).localname in ("p", "bookmarkEnd"):
            last = kids[-1]
            if etree.QName(last).localname == "p" and not "".join(last.itertext()).strip():
                kids.pop()
                continue
            break
        for k in kids:
            if isinstance(k.tag, str) and etree.QName(k).localname == "p":
                keep_next(k)
        pos = list(parent).index(outer)
        parent.remove(outer)
        for offset, k in enumerate(kids):
            parent.insert(pos + offset, k)


def tighten(paragraph):
    """Less space between table rows than between body paragraphs."""
    ppr = paragraph.find("w:pPr", NS)
    if ppr is None:
        ppr = etree.Element(q("pPr"))
        paragraph.insert(0, ppr)
    sp = ppr.find("w:spacing", NS)
    if sp is None:
        sp = etree.Element(q("spacing"))
        ppr.append(sp)
    sp.set(q("before"), "30")
    sp.set(q("after"), "50")
    sp.set(q("line"), "240")      # single-spaced inside tables
    sp.set(q("lineRule"), "auto")
    # keep the schema order of the paragraph properties
    kids = sorted(ppr, key=lambda c: PPR_ORDER.index(etree.QName(c).localname) if etree.QName(c).localname in PPR_ORDER else 99)
    for c in kids:
        ppr.remove(c)
        ppr.append(c)


def polish(xml_bytes):
    root = etree.fromstring(xml_bytes)
    tidy_paragraph_properties(root)
    tidy_page_margins(root)
    unwrap_captioned_tables(root)
    for tbl in list(root.iter(q("tbl"))):
        rows = tbl.findall("w:tr", NS)
        has_image = tbl.find(".//w:drawing", NS) is not None
        if has_image:
            # Quarto puts each figure and its caption in a one-cell table:
            # keep that cell on one page.
            for tr in rows:
                no_row_split(tr)
                for p in tr.iter(q("p")):
                    if p.find(".//w:drawing", NS) is not None:
                        keep_next(p)
            continue
        long_table = is_long(tbl)
        for i, tr in enumerate(rows):
            no_row_split(tr)
            for p in tr.iter(q("p")):
                tighten(p)
            # Short tables stay on one page. Long tables keep the header
            # with the first row and may then break between rows, with the
            # header repeated on the next page.
            if i < len(rows) - 1 and (not long_table or i == 0):
                for p in tr.iter(q("p")):
                    keep_next(p)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def main(path):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = polish(data)
            elif item.filename == "word/styles.xml":
                sroot = etree.fromstring(data)
                tidy_paragraph_properties(sroot)
                data = etree.tostring(sroot, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif item.filename == "[Content_Types].xml" and b'Extension="png"' not in data:
                data = data.replace(
                    b"<Default Extension=\"xml\"",
                    b"<Default Extension=\"png\" ContentType=\"image/png\" /><Default Extension=\"xml\"",
                    1,
                )
            zout.writestr(item, data)
    shutil.move(tmp, path)
    print(f"Polished {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "_site/final_report.docx")
