"""把教案字典渲染为排版规范的 Word (docx) 字节流。

纯函数模块，不依赖数据库或网络；排版遵循中文教学文档惯例：
- 页面 A4、默认边距
- 主标题：黑体二号（22pt）居中
- 章节标题：黑体四号（14pt）
- 正文：宋体小四（12pt）、1.5 倍行距
- 教学流程使用三列表格（表头加粗、浅灰底纹、全边框）
"""

from __future__ import annotations

import io
import re
from typing import Any

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

HEADING_FONT = "黑体"
BODY_FONT = "宋体"
TITLE_SIZE = Pt(22)  # 二号
SUBTITLE_SIZE = Pt(14)  # 四号
SECTION_SIZE = Pt(14)  # 四号
BODY_SIZE = Pt(12)  # 小四
EXCERPT_SIZE = Pt(10.5)  # 五号
HEADER_FILL = "D9D9D9"
LABEL_FILL = "F2F2F2"
PLACEHOLDER = "—"
CN_NUMERALS = ("一", "二", "三", "四", "五", "六", "七", "八", "九", "十")

_LIST_SECTION_FIELDS = (
    ("objectives", "教学目标"),
    ("key_points", "教学重点"),
    ("difficulties", "教学难点"),
    ("questions", "课堂提问"),
    ("exercises", "课堂练习"),
    ("homework", "课后作业"),
)

_FILENAME_INVALID_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]')


def _text(value: Any) -> str:
    """统一做 str() + strip 清洗，避免把 None 写进文档。"""
    if value is None:
        return ""
    return str(value).strip()


def _int_or_zero(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _string_items(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [item for item in (_text(entry) for entry in value) if item]


def _set_run_font(run: Any, *, font: str, size: Pt, bold: bool = False) -> None:
    run.font.name = font
    run.font.size = size
    run.font.bold = bold
    rpr = run._element.get_or_add_rPr()
    rpr.get_or_add_rFonts().set(qn("w:eastAsia"), font)


def _add_paragraph(
    document: Any,
    text: str,
    *,
    font: str = BODY_FONT,
    size: Pt = BODY_SIZE,
    bold: bool = False,
    align: Any = None,
    space_before: float = 0,
    space_after: float = 0,
    line_spacing: float | None = None,
    indent_left: float | None = None,
) -> Any:
    paragraph = document.add_paragraph()
    run = paragraph.add_run(text)
    _set_run_font(run, font=font, size=size, bold=bold)
    fmt = paragraph.paragraph_format
    if align is not None:
        fmt.alignment = align
    fmt.space_before = Pt(space_before)
    fmt.space_after = Pt(space_after)
    if line_spacing is not None:
        fmt.line_spacing = line_spacing
    if indent_left is not None:
        fmt.left_indent = Cm(indent_left)
    return paragraph


def _shade_cell(cell: Any, fill: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    cell._tc.get_or_add_tcPr().append(shd)


def _set_table_borders(table: Any) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "000000")


def _set_column_widths(table: Any, widths: list[Cm]) -> None:
    table.autofit = False
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = width


def _fill_cell(cell: Any, text: str, *, bold: bool = False, size: Pt = BODY_SIZE, font: str = BODY_FONT) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(text)
    _set_run_font(run, font=font, size=size, bold=bold)
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(2)


def _setup_page(document: Any) -> None:
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.18)
    section.right_margin = Cm(3.18)


def _setup_default_style(document: Any) -> None:
    normal = document.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = BODY_SIZE
    normal.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), BODY_FONT)


def _render_title(document: Any, plan: dict) -> None:
    course_name = _text(plan.get("course_name"))
    title = _text(plan.get("title")) or _text(plan.get("topic")) or "教案"
    _add_paragraph(
        document,
        title,
        font=HEADING_FONT,
        size=TITLE_SIZE,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=6,
    )
    subtitle = f"{course_name} 教案" if course_name else "教案"
    _add_paragraph(
        document,
        subtitle,
        font=BODY_FONT,
        size=SUBTITLE_SIZE,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=12,
    )


def _render_info_table(document: Any, plan: dict) -> None:
    duration = _int_or_zero(plan.get("duration_minutes"))
    table = document.add_table(rows=2, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(table)
    rows = (
        ("课程名称", _text(plan.get("course_name")) or PLACEHOLDER, "授课对象", _text(plan.get("audience")) or PLACEHOLDER),
        ("备课主题", _text(plan.get("topic")) or PLACEHOLDER, "课时", f"{duration} 分钟" if duration > 0 else PLACEHOLDER),
    )
    for row, values in zip(table.rows, rows):
        label_a, value_a, label_b, value_b = values
        for cell, text, is_label in (
            (row.cells[0], label_a, True),
            (row.cells[1], value_a, False),
            (row.cells[2], label_b, True),
            (row.cells[3], value_b, False),
        ):
            _fill_cell(cell, text, bold=is_label)
            if is_label:
                _shade_cell(cell, LABEL_FILL)
    _set_column_widths(table, [Cm(3.2), Cm(4.6), Cm(3.2), Cm(4.6)])


def _render_numbered_list(document: Any, items: list[str]) -> None:
    for index, item in enumerate(items, start=1):
        _add_paragraph(document, f"{index}. {item}", line_spacing=1.5, space_after=2)


def _flow_items(value: Any) -> list[tuple[str, int, str]]:
    if not isinstance(value, (list, tuple)):
        return []
    items = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        stage = _text(entry.get("stage"))
        content = _text(entry.get("content"))
        if not stage and not content:
            continue
        items.append((stage or PLACEHOLDER, _int_or_zero(entry.get("minutes")), content or PLACEHOLDER))
    return items


def _render_flow_table(document: Any, flow: list[tuple[str, int, str]]) -> None:
    table = document.add_table(rows=1 + len(flow), cols=3)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(table)
    header = table.rows[0]
    for cell, text in zip(header.cells, ("教学环节", "时长(分钟)", "教学内容")):
        _fill_cell(cell, text, bold=True)
        _shade_cell(cell, HEADER_FILL)
    for row, (stage, minutes, content) in zip(table.rows[1:], flow):
        _fill_cell(row.cells[0], stage)
        _fill_cell(row.cells[1], str(minutes))
        _fill_cell(row.cells[2], content)
    _set_column_widths(table, [Cm(3.4), Cm(2.4), Cm(8.6)])


def _render_summary(document: Any, summary: str) -> None:
    for chunk in summary.splitlines():
        chunk = chunk.strip()
        if chunk:
            _add_paragraph(document, chunk, line_spacing=1.5, space_after=2)


def _citation_items(value: Any) -> list[tuple[str, int, str]]:
    if not isinstance(value, (list, tuple)):
        return []
    items = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        name = _text(entry.get("name"))
        excerpt = _text(entry.get("excerpt"))
        if not name and not excerpt:
            continue
        items.append((name, _int_or_zero(entry.get("page")), excerpt))
    return items


def _render_citations(document: Any, citations: list[tuple[str, int, str]]) -> None:
    for index, (name, page, excerpt) in enumerate(citations, start=1):
        line = f"{index}. {name or '未命名课件'}"
        if page >= 1:
            line += f" 第{page}页"
        _add_paragraph(document, line, line_spacing=1.5, space_after=2)
        if excerpt:
            _add_paragraph(
                document,
                f"摘录：{excerpt}",
                size=EXCERPT_SIZE,
                line_spacing=1.5,
                indent_left=0.74,
                space_after=2,
            )


def _sections(plan: dict) -> list[tuple[str, list[tuple[str, Any]]]]:
    """返回 [(章节名, 渲染数据列表)]，空章节不进入列表。

    章节按 一、教学目标 / 二、教学重点 / 三、教学难点 / 四、教学流程 /
    五、课堂提问 / 六、课堂练习 / 七、课后作业 / [课件总结] / 八、课件依据
    顺序动态编号；跳过的空章节不占编号。
    """
    sections: list[tuple[str, list[tuple[str, Any]]]] = []
    for key, heading in _LIST_SECTION_FIELDS[:3]:
        items = _string_items(plan.get(key))
        if items:
            sections.append((heading, [("list", items)]))
    flow = _flow_items(plan.get("teaching_flow"))
    if flow:
        sections.append(("教学流程", [("flow", flow)]))
    for key, heading in _LIST_SECTION_FIELDS[3:]:
        items = _string_items(plan.get(key))
        if items:
            sections.append((heading, [("list", items)]))
    summary = _text(plan.get("summary"))
    if summary:
        sections.append(("课件总结", [("summary", summary)]))
    citations = _citation_items(plan.get("citations"))
    if citations:
        sections.append(("课件依据", [("citations", citations)]))
    return sections


def _render_section(document: Any, kind: str, data: Any) -> None:
    if kind == "list":
        _render_numbered_list(document, data)
    elif kind == "flow":
        _render_flow_table(document, data)
    elif kind == "summary":
        _render_summary(document, data)
    elif kind == "citations":
        _render_citations(document, data)


def build_lesson_plan_docx(plan: dict) -> bytes:
    """把教案字典渲染为 docx 字节流；空章节自动跳过。"""
    document = Document()
    _setup_page(document)
    _setup_default_style(document)
    _render_title(document, plan)
    _render_info_table(document, plan)
    for index, (heading, renderers) in enumerate(_sections(plan), start=1):
        numeral = CN_NUMERALS[index - 1] if index <= len(CN_NUMERALS) else str(index)
        _add_paragraph(
            document,
            f"{numeral}、{heading}",
            font=HEADING_FONT,
            size=SECTION_SIZE,
            space_before=12,
            space_after=6,
        )
        for kind, data in renderers:
            _render_section(document, kind, data)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def build_docx_filename(title: str) -> str:
    """由教案标题生成安全的下载文件名：非法字符替换为下划线，标题截断到 60 字符内。"""
    cleaned = _FILENAME_INVALID_CHARS.sub("_", _text(title))
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip("._")
    if len(cleaned) > 60:
        cleaned = cleaned[:60].rstrip().strip("._")
    if not cleaned:
        cleaned = "未命名"
    return f"{cleaned}-教案.docx"
