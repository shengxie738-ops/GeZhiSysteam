"""
中国学术论文规范样式系统
- A4 纵向页面布局
- 宋体/Times New Roman 正文，1.5 倍行距，首行缩进 2 字符
- 黑体多级标题（自动编号 1 → 1.1 → 1.1.1）
- 三线表、学术封面、中英文摘要、参考文献等组件
- 多分节页眉页码（封面无页眉页码 / 前置罗马数字 / 正文阿拉伯数字）
"""
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Mm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ── 字体定义 ──
FONT_SONG = '宋体'           # 正文中文字体
FONT_HEI = '黑体'            # 标题中文字体
FONT_EN = 'Times New Roman'  # 西文字体

# ── 字号定义（pt）──
SIZE_COVER_TITLE = 22   # 二号（封面项目名）
SIZE_COVER_DOC = 16     # 三号（封面文档名）
SIZE_COVER_INFO = 15    # 小三（封面信息）
SIZE_H1 = 16            # 三号（一级标题）
SIZE_H2 = 14            # 四号（二级标题）
SIZE_H3 = 12            # 小四（三级标题）
SIZE_BODY = 12          # 小四（正文）
SIZE_TABLE = 10.5       # 五号（表格/题注）
SIZE_CAPTION = 10.5     # 五号（图表题注）

# ── 颜色定义（学术黑白）──
COLOR_BLACK = RGBColor(0, 0, 0)

# 向后兼容旧主题的颜色常量
COLOR_PRIMARY = COLOR_BLACK
COLOR_DARK_GRAY = COLOR_BLACK
COLOR_MED_GRAY = COLOR_BLACK
COLOR_GRAY = RGBColor(0x66, 0x66, 0x66)
COLOR_LIGHT_GRAY = RGBColor(0xD9, 0xD9, 0xD9)
COLOR_ZEBRA = RGBColor(0xF5, 0xF5, 0xF5)
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
COLOR_CAPTION = RGBColor(0x66, 0x66, 0x66)

# matplotlib 兼容配置（diagrams.py 有自己的配置，此处仅为向后兼容）
MPL_GRAY_PALETTE = ['#1A1A1A', '#4A4A4A', '#8C8C8C', '#BFBFBF', '#D9D9D9']
MPL_BG = '#FFFFFF'
MPL_EDGE = '#4A4A4A'
MPL_TEXT = '#1A1A1A'
MPL_FONT = 'SimSun'

FONT_TITLE = FONT_HEI   # 向后兼容
FONT_BODY = FONT_SONG   # 向后兼容

# 旧字号常量（向后兼容）
SIZE_COVER_SUBTITLE = 16

# 全局标题跟踪器（在 setup_document_styles 中初始化）
_heading_tracker = None


# ════════════════════════════════════════════════════════
#  底层 XML 工具函数
# ════════════════════════════════════════════════════════

def _set_run_font(run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=12, bold=False):
    """同时设置 ascii / hAnsi / eastAsia 三套字体。"""
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.name = en_font
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:ascii'), en_font)
    rfonts.set(qn('w:hAnsi'), en_font)
    rfonts.set(qn('w:eastAsia'), cn_font)


def _set_first_line_indent_chars(paragraph, chars=2):
    """以"字符"为单位设置首行缩进（chars=2 表示 2 字符）。"""
    pPr = paragraph._element.get_or_add_pPr()
    ind = pPr.find(qn('w:ind'))
    if ind is None:
        ind = OxmlElement('w:ind')
        pPr.append(ind)
    # firstLineChars 单位为 1/100 字符；firstLine 单位为 twips（兼容回退）
    ind.set(qn('w:firstLineChars'), str(chars * 100))
    ind.set(qn('w:firstLine'), str(chars * 210))  # 1 字符 ≈ 210 twips（10.5pt）


def _clear_first_line_indent(paragraph):
    """清除首行缩进。"""
    pPr = paragraph._element.get_or_add_pPr()
    ind = pPr.find(qn('w:ind'))
    if ind is None:
        ind = OxmlElement('w:ind')
        pPr.append(ind)
    ind.set(qn('w:firstLine'), '0')
    ind.set(qn('w:firstLineChars'), '0')


def _disable_snap_to_grid(paragraph):
    """取消对齐文档网格（autoSpaceDE / adjustRightInd / snapToGrid 均设为 false）。"""
    pPr = paragraph._element.get_or_add_pPr()
    for tag_name in ('w:snapToGrid', 'w:autoSpaceDE', 'w:autoSpaceDN', 'w:adjustRightInd'):
        existing = pPr.find(qn(tag_name))
        if existing is None:
            el = OxmlElement(tag_name)
            el.set(qn('w:val'), 'false')
            pPr.append(el)


def _set_line_spacing_15(paragraph):
    """1.5 倍行距（MULTIPLE 规则）。"""
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE


def _set_cell_border(cell, **kwargs):
    """设置单元格边框。kwargs 键: top/left/bottom/right；值: 边框属性 dict。"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = tcPr.find(qn('w:tcBorders'))
    if tcBorders is None:
        tcBorders = OxmlElement('w:tcBorders')
        tcPr.append(tcBorders)
    for edge in ('top', 'left', 'bottom', 'right'):
        if edge in kwargs:
            tag = qn(f'w:{edge}')
            element = tcBorders.find(tag)
            if element is None:
                element = OxmlElement(f'w:{edge}')
                tcBorders.append(element)
            for k, v in kwargs[edge].items():
                element.set(qn(f'w:{k}'), str(v))


def _remove_table_default_borders(table):
    """移除表格默认边框（为三线表做准备）。"""
    tbl = table._tbl
    tblPr = tbl.find(qn('w:tblPr'))
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl.insert(0, tblPr)
    tblBorders = tblPr.find(qn('w:tblBorders'))
    if tblBorders is None:
        tblBorders = OxmlElement('w:tblBorders')
        tblPr.append(tblBorders)
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        tag = qn(f'w:{edge}')
        element = tblBorders.find(tag)
        if element is None:
            element = OxmlElement(f'w:{edge}')
            tblBorders.append(element)
        element.set(qn('w:val'), 'nil')


def _set_pgnum_type(section, numfmt=None, start=None):
    """配置 section 的 pgNumType（页码格式与起始值）。"""
    sectPr = section._sectPr
    pgNumType = sectPr.find(qn('w:pgNumType'))
    if pgNumType is None:
        pgNumType = OxmlElement('w:pgNumType')
        sectPr.append(pgNumType)
    if numfmt is not None:
        pgNumType.set(qn('w:fmt'), numfmt)
    if start is not None:
        pgNumType.set(qn('w:start'), str(start))


def _clear_header_footer_content(section):
    """清空 section 的页眉页脚内容。"""
    for collection in (section.header, section.footer):
        for p in collection.paragraphs:
            for run in list(p.runs):
                run._element.getparent().remove(run._element)


def _apply_page_layout(section):
    """对指定 section 应用 A4 纵向页面布局。"""
    section.page_height = Mm(297)
    section.page_width = Mm(210)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.5)
    section.gutter = Cm(0.5)
    section.header_distance = Cm(1.5)
    section.footer_distance = Cm(1.75)


# ════════════════════════════════════════════════════════
#  公开 API
# ════════════════════════════════════════════════════════

def setup_document_styles(doc: Document):
    """配置 A4 页面布局与 Normal 正文样式（宋体小四，1.5 倍行距）。"""
    global _heading_tracker
    # 延迟导入避免循环依赖
    from toc_builder import HeadingTracker
    _heading_tracker = HeadingTracker()

    # 页面布局
    _apply_page_layout(doc.sections[0])

    # Normal 样式：宋体 / Times New Roman 小四
    style = doc.styles['Normal']
    style.font.name = FONT_EN
    style.font.size = Pt(SIZE_BODY)
    style.font.color.rgb = COLOR_BLACK
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:ascii'), FONT_EN)
    rfonts.set(qn('w:hAnsi'), FONT_EN)
    rfonts.set(qn('w:eastAsia'), FONT_SONG)

    pf = style.paragraph_format
    pf.line_spacing = 1.5
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def add_heading_styled(doc: Document, text: str, level: int = 1):
    """添加自动编号的多级标题。
    一级：黑体三号加粗；二级：黑体四号加粗；三级：黑体小四加粗。
    使用 HeadingTracker 生成编号 '1' / '1.1' / '1.1.1' 与书签。
    """
    # 延迟导入避免循环依赖
    from toc_builder import add_bookmark_to_heading

    # 通过全局 tracker 生成编号与书签
    bookmark = _heading_tracker.add(level, text)
    number = _heading_tracker.headings[-1]['number']

    # 标题段落
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    _set_line_spacing_15(p)
    pf.first_line_indent = Pt(0)
    _clear_first_line_indent(p)

    # 段前段后（按"行"换算为 pt：1.5 行=18pt, 1 行=12pt, 0.5 行=6pt, 0.25 行=3pt）
    if level == 1:
        size_pt = SIZE_H1
        pf.space_before = Pt(18)
        pf.space_after = Pt(12)
    elif level == 2:
        size_pt = SIZE_H2
        pf.space_before = Pt(12)
        pf.space_after = Pt(6)
    elif level == 3:
        size_pt = SIZE_H3
        pf.space_before = Pt(6)
        pf.space_after = Pt(3)
    else:
        size_pt = SIZE_BODY
        pf.space_before = Pt(6)
        pf.space_after = Pt(6)

    _disable_snap_to_grid(p)

    # 显示文本：编号 + 双空格 + 标题文本
    display_text = f"{number}  {text}"
    run = p.add_run(display_text)
    _set_run_font(run, cn_font=FONT_HEI, en_font=FONT_EN, size_pt=size_pt, bold=True)

    # 给标题段落添加书签（供 PAGEREF 引用）
    add_bookmark_to_heading(p, bookmark)
    return p


def add_body_text(doc: Document, text: str, bold: bool = False, indent: bool = True):
    """添加正文段落：宋体/TNR 小四，1.5 倍行距，首行缩进 2 字符，两端对齐。"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    _set_line_spacing_15(p)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    if indent:
        _set_first_line_indent_chars(p, 2)
    _disable_snap_to_grid(p)

    run = p.add_run(text)
    _set_run_font(run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_BODY, bold=bold)
    return p


def add_bullet(doc: Document, text: str, level: int = 0):
    """添加项目符号段落（"• "前缀 + 缩进悬挂）。"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    _set_line_spacing_15(p)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.left_indent = Cm(0.74)
    pf.first_line_indent = Cm(-0.37)
    _disable_snap_to_grid(p)

    bullet_run = p.add_run('• ')
    _set_run_font(bullet_run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_BODY)

    run = p.add_run(text)
    _set_run_font(run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_BODY)
    return p


def add_image_with_caption(doc: Document, image_path: str, caption: str, width: float = 5.5):
    """添加居中图片 + 图题（宋体五号，位于图片下方，段前 0.5 行段后 0.5 行）。"""
    # 图片段落
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    _set_line_spacing_15(p)
    pf.space_before = Pt(6)
    pf.space_after = Pt(3)
    _disable_snap_to_grid(p)

    run = p.add_run()
    run.add_picture(image_path, width=Inches(width))

    # 图题段落
    cap_p = doc.add_paragraph()
    cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_pf = cap_p.paragraph_format
    _set_line_spacing_15(cap_p)
    cap_pf.space_before = Pt(3)
    cap_pf.space_after = Pt(6)
    _disable_snap_to_grid(cap_p)

    cap_run = cap_p.add_run(caption)
    _set_run_font(cap_run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_CAPTION, bold=False)
    return cap_p


def add_styled_table(doc: Document, headers: list, rows: list, col_widths=None):
    """添加三线表：顶线 1.5pt，表头下线 0.75pt，底线 1.5pt，无竖线。
    表头与表内：宋体五号；表头加粗。
    """
    n_cols = len(headers)
    n_rows = 1 + len(rows)
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _remove_table_default_borders(table)

    # 边框值（sz 单位为 1/8 pt：12=1.5pt, 6=0.75pt）
    border_thick = {'val': 'single', 'sz': '12', 'color': '000000'}
    border_thin = {'val': 'single', 'sz': '6', 'color': '000000'}

    # 表头行
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ''
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = p.paragraph_format
        _set_line_spacing_15(p)
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        _disable_snap_to_grid(p)

        run = p.add_run(str(header))
        _set_run_font(run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_TABLE, bold=True)

        # 表头：上边框 1.5pt，下边框 0.75pt
        _set_cell_border(cell, top=border_thick, bottom=border_thin)

    # 数据行
    for r_idx, row_data in enumerate(rows):
        is_last = (r_idx == len(rows) - 1)
        for c_idx, cell_text in enumerate(row_data):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ''
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx == 0 else WD_ALIGN_PARAGRAPH.LEFT
            pf = p.paragraph_format
            _set_line_spacing_15(p)
            pf.space_before = Pt(0)
            pf.space_after = Pt(0)
            _disable_snap_to_grid(p)

            run = p.add_run(str(cell_text))
            _set_run_font(run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_TABLE)

            if is_last:
                _set_cell_border(cell, bottom=border_thick)

    # 列宽
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)

    # 表格后空段落
    after_p = doc.add_paragraph()
    after_pf = after_p.paragraph_format
    after_pf.space_before = Pt(0)
    after_pf.space_after = Pt(0)
    return table


def add_cover_page(doc: Document, title: str, subtitle: str, version: str, date: str):
    """添加学术封面页：项目名黑体二号、文档名黑体三号、信息宋体小三，均居中。
    封面位于第一节，无页眉无页码（默认 section 1 即为空页眉页脚）。
    """
    # 顶部留白
    for _ in range(6):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)

    # 项目名称：黑体二号(22pt)加粗居中
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(24)
    _disable_snap_to_grid(p)
    run = p.add_run('格至智能协同教育系统')
    _set_run_font(run, cn_font=FONT_HEI, en_font=FONT_EN, size_pt=SIZE_COVER_TITLE, bold=True)

    # 文档名称：黑体三号(16pt)居中
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(48)
    _disable_snap_to_grid(p)
    run = p.add_run(title)
    _set_run_font(run, cn_font=FONT_HEI, en_font=FONT_EN, size_pt=SIZE_COVER_DOC, bold=False)

    # 中间留白
    for _ in range(4):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)

    # 参赛单位、作者信息、日期：宋体小三(15pt)居中
    info_lines = [
        subtitle,
        f'版本号：{version}',
        f'日期：{date}',
        '编制单位：格至智能协同教育系统参赛团队',
    ]
    for info in info_lines:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(12)
        _disable_snap_to_grid(p)
        run = p.add_run(info)
        _set_run_font(run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_COVER_INFO)


def add_toc(doc: Document):
    """兼容旧 API：添加 TOC 域（需在 Word 中按 F9 更新）。
    新代码请使用 toc_builder.build_toc 生成静态目录条目。
    """
    # 目录标题
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    _set_line_spacing_15(p)
    pf.space_before = Pt(18)
    pf.space_after = Pt(12)
    _clear_first_line_indent(p)
    _disable_snap_to_grid(p)
    run = p.add_run('目  录')
    _set_run_font(run, cn_font=FONT_HEI, en_font=FONT_EN, size_pt=SIZE_H1, bold=True)

    # 插入 TOC 域
    paragraph = doc.add_paragraph()
    run = paragraph.add_run()
    fldChar = OxmlElement('w:fldChar')
    fldChar.set(qn('w:fldCharType'), 'begin')
    run._element.append(fldChar)

    run2 = paragraph.add_run()
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = ' TOC \\o "1-3" \\h \\z \\u '
    run2._element.append(instrText)

    run3 = paragraph.add_run()
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'separate')
    run3._element.append(fldChar2)

    run4 = paragraph.add_run('（请在 Word 中按 F9 更新目录）')
    _set_run_font(run4, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_BODY)

    run5 = paragraph.add_run()
    fldChar3 = OxmlElement('w:fldChar')
    fldChar3.set(qn('w:fldCharType'), 'end')
    run5._element.append(fldChar3)

    doc.add_page_break()


def _add_unnumbered_h1(doc: Document, title_text: str):
    """添加不编号的一级标题（用于摘要/参考文献等前置或后置部分）。"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    _set_line_spacing_15(p)
    pf.space_before = Pt(18)
    pf.space_after = Pt(12)
    _clear_first_line_indent(p)
    _disable_snap_to_grid(p)
    run = p.add_run(title_text)
    _set_run_font(run, cn_font=FONT_HEI, en_font=FONT_EN, size_pt=SIZE_H1, bold=True)
    return p


def add_abstract(doc: Document, abstract_text: str, keywords):
    """添加中文摘要：'摘要' 一级标题（不编号）+ 摘要正文 + 关键词。
    '摘要：' 黑体小四加粗，内容宋体小四；'关键词：' 同。
    """
    _add_unnumbered_h1(doc, '摘  要')

    # 摘要正文
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    _set_line_spacing_15(p)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    _set_first_line_indent_chars(p, 2)
    _disable_snap_to_grid(p)

    label_run = p.add_run('摘要：')
    _set_run_font(label_run, cn_font=FONT_HEI, en_font=FONT_EN, size_pt=SIZE_BODY, bold=True)
    body_run = p.add_run(abstract_text)
    _set_run_font(body_run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_BODY)

    # 关键词
    if isinstance(keywords, (list, tuple)):
        kw_text = '；'.join(keywords)
    else:
        kw_text = str(keywords)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    _set_line_spacing_15(p)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    _set_first_line_indent_chars(p, 2)
    _disable_snap_to_grid(p)

    label_run = p.add_run('关键词：')
    _set_run_font(label_run, cn_font=FONT_HEI, en_font=FONT_EN, size_pt=SIZE_BODY, bold=True)
    body_run = p.add_run(kw_text)
    _set_run_font(body_run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_BODY)


def add_english_abstract(doc: Document, abstract_text: str, keywords):
    """添加英文摘要：'Abstract' 一级标题（不编号）+ 摘要正文 + 关键词。
    'Abstract:' / 'Keywords:' TNR 小四加粗，内容 TNR 小四。
    """
    _add_unnumbered_h1(doc, 'Abstract')

    # 摘要正文
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    _set_line_spacing_15(p)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    _set_first_line_indent_chars(p, 2)
    _disable_snap_to_grid(p)

    label_run = p.add_run('Abstract: ')
    _set_run_font(label_run, cn_font=FONT_HEI, en_font=FONT_EN, size_pt=SIZE_BODY, bold=True)
    body_run = p.add_run(abstract_text)
    _set_run_font(body_run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_BODY)

    # 关键词
    if isinstance(keywords, (list, tuple)):
        kw_text = '; '.join(keywords)
    else:
        kw_text = str(keywords)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    _set_line_spacing_15(p)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    _set_first_line_indent_chars(p, 2)
    _disable_snap_to_grid(p)

    label_run = p.add_run('Keywords: ')
    _set_run_font(label_run, cn_font=FONT_HEI, en_font=FONT_EN, size_pt=SIZE_BODY, bold=True)
    body_run = p.add_run(kw_text)
    _set_run_font(body_run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_BODY)


def add_references(doc: Document, references):
    """添加参考文献：'参考文献' 一级标题 + 编号条目（宋体五号，悬挂缩进 2 字符）。"""
    _add_unnumbered_h1(doc, '参考文献')

    for i, ref in enumerate(references, 1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf = p.paragraph_format
        _set_line_spacing_15(p)
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)

        # 悬挂缩进 2 字符
        pPr = p._element.get_or_add_pPr()
        ind = pPr.find(qn('w:ind'))
        if ind is None:
            ind = OxmlElement('w:ind')
            pPr.append(ind)
        ind.set(qn('w:left'), '420')
        ind.set(qn('w:leftChars'), '200')
        ind.set(qn('w:hanging'), '420')
        ind.set(qn('w:hangingChars'), '200')
        _disable_snap_to_grid(p)

        run = p.add_run(f'[{i}] {ref}')
        _set_run_font(run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_TABLE)


def add_section_break(doc: Document, section_type: str):
    """添加分节符并配置页眉页脚。
    section_type:
    - 'cover': 无页眉，无页码
    - 'front': 无页眉，页脚罗马数字页码（从 1 开始）
    - 'body':  页眉"格至智能协同教育系统参赛论文"宋体五号居中，页脚阿拉伯数字页码（从 1 开始）
    """
    new_section = doc.add_section(WD_SECTION.NEW_PAGE)
    _apply_page_layout(new_section)

    # 断开与上一节的页眉页脚链接
    new_section.header.is_linked_to_previous = False
    new_section.footer.is_linked_to_previous = False
    _clear_header_footer_content(new_section)

    if section_type == 'cover':
        _set_pgnum_type(new_section, numfmt=None, start=None)

    elif section_type == 'front':
        # 页脚罗马数字页码
        footer_p = new_section.footer.paragraphs[0]
        footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_page_number(doc, footer_p, numfmt='upperRoman', start=1)
        _set_pgnum_type(new_section, numfmt='upperRoman', start=1)

    elif section_type == 'body':
        # 页眉文字
        add_header_text(new_section, '格至智能协同教育系统参赛论文')
        # 页脚阿拉伯数字页码从 1 开始
        footer_p = new_section.footer.paragraphs[0]
        footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_page_number(doc, footer_p, numfmt='decimal', start=1)
        _set_pgnum_type(new_section, numfmt='decimal', start=1)

    return new_section


def add_page_number(doc: Document, paragraph, numfmt: str = 'decimal', start=None):
    """在段落中插入 PAGE 域。
    numfmt 与 start 由调用方（如 add_section_break）通过 _set_pgnum_type 配置 section 的 pgNumType。
    本函数仅插入 PAGE 域。
    """
    fldSimple = OxmlElement('w:fldSimple')
    fldSimple.set(qn('w:instr'), ' PAGE \\* MERGEFORMAT ')

    # 域内默认显示文本
    inner_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), FONT_EN)
    rFonts.set(qn('w:hAnsi'), FONT_EN)
    rFonts.set(qn('w:eastAsia'), FONT_SONG)
    rPr.append(rFonts)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), str(int(SIZE_TABLE * 2)))
    rPr.append(sz)
    inner_run.append(rPr)

    t = OxmlElement('w:t')
    t.text = '1'
    inner_run.append(t)
    fldSimple.append(inner_run)

    # 直接将 fldSimple 添加到段落（fldSimple 是段落级元素，不能放在 w:r 内）
    paragraph._element.append(fldSimple)


def add_header_text(section, text: str):
    """设置 section 的页眉文字：宋体五号居中。"""
    header_p = section.header.paragraphs[0]
    header_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # 清除已有 runs
    for run in list(header_p.runs):
        run._element.getparent().remove(run._element)
    run = header_p.add_run(text)
    _set_run_font(run, cn_font=FONT_SONG, en_font=FONT_EN, size_pt=SIZE_TABLE)


def get_heading_tracker():
    """返回全局 HeadingTracker 实例（供 build_toc 使用）。"""
    return _heading_tracker


# ════════════════════════════════════════════════════════
#  自测：生成包含全部组件的测试文档
# ════════════════════════════════════════════════════════

if __name__ == '__main__':
    import os
    import sys

    # 确保能导入同目录模块
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from docx import Document
    from toc_builder import (HeadingTracker, build_toc, add_hidden_toc_field,
                             reset_bookmark_counter)

    # 准备图片路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(base_dir, 'output', 'images')
    sample_image = os.path.join(images_dir, 'system_overview.png')

    # 预先定义所有标题（用于两遍式构建：先收集→生成目录→再实际添加）
    heading_specs = [
        (1, '项目概述'),
        (2, '项目背景'),
        (2, '需求分析'),
        (3, 'Git痛点细分'),
        (1, '系统总体架构'),
        (2, '系统全景架构'),
        (2, '技术栈选型'),
        (1, '智能体系统设计'),
    ]

    # 第一遍：用临时 tracker 预生成编号与书签，供 build_toc 使用
    pre_tracker = HeadingTracker()
    for lvl, txt in heading_specs:
        pre_tracker.add(lvl, txt)

    # 创建文档
    doc = Document()
    setup_document_styles(doc)
    reset_bookmark_counter()

    # ─── 第一节：封面（无页眉无页码） ───
    add_cover_page(doc, '系统开发说明书',
                   'Gezhi Intelligent Collaborative Education System',
                   'V3.0', '2026年7月')

    # ─── 第二节：前置部分（无页眉，罗马数字页码） ───
    add_section_break(doc, 'front')
    add_abstract(
        doc,
        '本文介绍格至智能协同教育系统的设计与实现。系统融合多智能体协同教学、'
        'Git 协作实训与 RAG 知识检索三大核心能力，为高校计算机/软件工程专业学生'
        '提供从知识学习、代码实践到团队协作的一站式智能教育服务。',
        ['智能教育', '多智能体协同', '检索增强生成', 'Git 协作实训']
    )
    add_english_abstract(
        doc,
        'This paper presents the design and implementation of the Gezhi Intelligent '
        'Collaborative Education System. The system integrates multi-agent collaborative '
        'teaching, Git collaboration training, and RAG knowledge retrieval to provide '
        'one-stop intelligent education services for college CS/SE students.',
        ['Intelligent Education', 'Multi-Agent Collaboration', 'RAG', 'Git Training']
    )

    # ─── 第三节：正文（页眉 + 阿拉伯数字页码从 1 开始） ───
    add_section_break(doc, 'body')

    # 静态目录（使用预 tracker 的 headings，书签名与后续实际添加的标题一致）
    build_toc(doc, pre_tracker.headings)
    # 隐藏 TOC 域，供 Word 中右键更新
    add_hidden_toc_field(doc)
    doc.add_page_break()

    # ─── 正文：3 个一级标题 + 若干二三级标题 + 表格 + 图片 ───
    for idx, (lvl, txt) in enumerate(heading_specs):
        add_heading_styled(doc, txt, level=lvl)

        if lvl == 1:
            add_body_text(doc,
                f'本章介绍{txt}的相关内容。系统采用前后端分离架构，'
                f'后端基于 FastAPI 异步框架，前端采用 Vue 3 ESM 单页应用，'
                f'配合多智能体协同工作流，构建完整的智能教育平台。')
        elif lvl == 2:
            add_body_text(doc,
                f'本节详细阐述{txt}的设计思路与实现细节，'
                f'结合实际应用场景说明技术方案的合理性。')
        else:
            add_body_text(doc,
                f'本小节针对{txt}进行更细粒度的分析，'
                f'通过具体数据与案例验证设计决策的有效性。')

        # 在第一个二级标题下添加图片
        if txt == '项目背景' and os.path.exists(sample_image):
            add_image_with_caption(doc, sample_image, '图1-1 系统全景架构图')

        # 在第二个一级标题下添加三线表
        if txt == '系统总体架构':
            add_styled_table(
                doc,
                headers=['层次', '技术选型', '说明'],
                rows=[
                    ['后端框架', 'FastAPI + Uvicorn', '异步高性能'],
                    ['AI框架', 'LangGraph + LangChain', '多智能体编排'],
                    ['数据库', 'MySQL + SQLAlchemy', '连接池管理'],
                    ['前端框架', 'Vue 3 ESM + Tailwind', '无构建SPA'],
                ],
                col_widths=[3.0, 5.0, 6.0]
            )

        # 在"需求分析"下添加项目符号
        if txt == '需求分析':
            add_bullet(doc, '痛点一：Git 使用率低，团队协作能力缺失。')
            add_bullet(doc, '痛点二：个性化学习指导不足，难以因材施教。')
            add_bullet(doc, '痛点三：知识检索效率低，缺乏语义化检索能力。')

    # ─── 参考文献 ───
    add_references(doc, [
        '王某某, 李某某. 基于大语言模型的智能教育系统研究[J]. 计算机科学, 2024, 51(3): 1-10.',
        'Smith J, Doe A. Multi-agent systems for education[C]//Proceedings of AAAI 2024: 100-110.',
        'OpenAI. GPT-4 Technical Report[R]. 2023.',
        'LangChain. LangGraph: Building Stateful Multi-Actor Applications[EB/OL]. 2024.',
        '中华人民共和国国家质量监督检验检疫总局. GB/T 7714-2015 信息与文献 参考文献著录规则[S]. 2015.',
    ])

    # ─── 保存 ───
    out_path = os.path.join(base_dir, 'test_theme.docx')
    doc.save(out_path)
    print(f'测试文档已生成：{out_path}')
    print(f'文件大小：{os.path.getsize(out_path) / 1024:.1f} KB')
    print(f'已收集标题数：{len(pre_tracker.headings)}')
    print(f'全局 tracker 标题数：{len(_heading_tracker.headings)}')
    print('包含组件：封面、中文摘要、英文摘要、静态目录、'
          '多级标题（1/2/3级）、正文、项目符号、三线表、图片题注、参考文献、'
          '三节分页（封面/前置罗马页码/正文阿拉伯页码）')
