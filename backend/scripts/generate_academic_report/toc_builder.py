"""
静态目录构建模块
- 通过书签（bookmarkStart/bookmarkEnd）+ PAGEREF 域生成静态目录条目
- 确保文档打开即显示目录（无需用户手动 F9 更新）
- 同时提供标准 TOC 域（隐藏），供 Word 中右键"更新域"使用
- HeadingTracker 跟踪所有标题，生成编号 '1' / '1.1' / '1.1.1' 与书签名
"""
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# 全局书签 ID 计数器（Word 要求每个书签 id 唯一）
_bookmark_id_counter = [0]


def _next_bookmark_id():
    """返回递增的书签 id。"""
    _bookmark_id_counter[0] += 1
    return _bookmark_id_counter[0]


def reset_bookmark_counter():
    """重置书签 id 计数器（在生成新文档时调用）。"""
    _bookmark_id_counter[0] = 0


# ════════════════════════════════════════════════════════
#  HeadingTracker：跟踪所有标题，生成编号与书签名
# ════════════════════════════════════════════════════════

class HeadingTracker:
    """跟踪所有标题，用于后续生成目录。
    每次 add(level, text) 返回书签名，并将编号/书签存入 headings 列表。
    """

    def __init__(self):
        self.headings = []
        self.counter = {1: 0, 2: 0, 3: 0}

    def add(self, level, text):
        """注册一个标题，返回书签名。"""
        if level not in (1, 2, 3):
            level = 1
        self.counter[level] += 1
        # 重置下级计数器
        for l in range(level + 1, 4):
            self.counter[l] = 0
        number = '.'.join(str(self.counter[l]) for l in range(1, level + 1))
        bookmark = f"bm_{len(self.headings) + 1}"
        self.headings.append({
            'level': level,
            'text': text,
            'number': number,
            'bookmark': bookmark,
        })
        return bookmark

    def reset(self):
        """重置跟踪器。"""
        self.headings = []
        self.counter = {1: 0, 2: 0, 3: 0}


# ════════════════════════════════════════════════════════
#  书签：在标题段落添加 bookmarkStart/bookmarkEnd
# ════════════════════════════════════════════════════════

def add_bookmark_to_heading(paragraph, bookmark_name):
    """在段落开头添加书签，包裹段落内容。
    生成的 XML：
      <w:bookmarkStart w:id="N" w:name="bm_N"/>
      ... 段落 runs ...
      <w:bookmarkEnd w:id="N"/>
    """
    bid = _next_bookmark_id()

    start = OxmlElement('w:bookmarkStart')
    start.set(qn('w:id'), str(bid))
    start.set(qn('w:name'), bookmark_name)

    end = OxmlElement('w:bookmarkEnd')
    end.set(qn('w:id'), str(bid))

    p_elem = paragraph._element
    # bookmarkStart 插入到 pPr 之后（即段落内容的最前面）
    pPr = p_elem.find(qn('w:pPr'))
    if pPr is not None:
        pPr.addnext(start)
    else:
        p_elem.insert(0, start)
    # bookmarkEnd 追加到段落末尾
    p_elem.append(end)


# ════════════════════════════════════════════════════════
#  制表位与 PAGEREF 域
# ════════════════════════════════════════════════════════

def _add_tab_stop(paragraph, position_cm, alignment='right', leader='dot'):
    """添加制表位：右对齐 + 点引导线，位置约 14.5cm。"""
    pPr = paragraph._element.get_or_add_pPr()
    tabs = pPr.find(qn('w:tabs'))
    if tabs is None:
        tabs = OxmlElement('w:tabs')
        pPr.append(tabs)
    tab = OxmlElement('w:tab')
    tab.set(qn('w:val'), alignment)
    tab.set(qn('w:leader'), leader)
    # 1 cm ≈ 567 twips
    pos_twips = int(position_cm * 567)
    tab.set(qn('w:pos'), str(pos_twips))
    tabs.append(tab)


def _add_pageref_field(paragraph, bookmark_name, cn_font='宋体',
                       en_font='Times New Roman', size_pt=12):
    """在段落中插入 PAGEREF 域，引用指定书签。
    生成的 XML：
      <w:fldSimple w:instr=" PAGEREF bm_1 \\h \\* MERGEFORMAT ">
        <w:r><w:t>1</w:t></w:r>
      </w:fldSimple>
    fldSimple 是段落级元素，必须直接挂在 <w:p> 下，不能放在 <w:r> 内。
    """
    fldSimple = OxmlElement('w:fldSimple')
    fldSimple.set(qn('w:instr'),
                  f' PAGEREF {bookmark_name} \\h \\* MERGEFORMAT ')

    # 域内默认显示文本（用户在 Word 中按 F9 更新后会被真实页码替换）
    inner_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), en_font)
    rFonts.set(qn('w:hAnsi'), en_font)
    rFonts.set(qn('w:eastAsia'), cn_font)
    rPr.append(rFonts)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), str(int(size_pt * 2)))
    rPr.append(sz)
    inner_run.append(rPr)

    t = OxmlElement('w:t')
    t.text = '1'
    inner_run.append(t)
    fldSimple.append(inner_run)

    # 直接将 fldSimple 添加到段落
    paragraph._element.append(fldSimple)


# ════════════════════════════════════════════════════════
#  静态目录构建
# ════════════════════════════════════════════════════════

def build_toc(doc, headings, cn_font='宋体', en_font='Times New Roman'):
    """根据 headings 列表生成静态目录。
    headings: list of dict，每项：
        {'level': 1/2/3, 'text': '标题文本', 'bookmark': 'bm_1', 'number': '1' or '1.1'}
    生成内容：
      - "目  录" 一级标题样式（黑体三号加粗居中）
      - 每行：编号+标题文本 + 制表符（右对齐+点引导线） + PAGEREF 域
      - 一级标题不缩进且加粗，二级标题缩进 2 字符
    """
    # 延迟导入避免循环依赖
    from theme import (_disable_snap_to_grid, _set_run_font, _clear_first_line_indent,
                       _set_line_spacing_15, SIZE_H1, SIZE_BODY, FONT_HEI)

    # 目录标题 "目  录"
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = title_p.paragraph_format
    _set_line_spacing_15(title_p)
    pf.space_before = Pt(18)
    pf.space_after = Pt(12)
    _clear_first_line_indent(title_p)
    _disable_snap_to_grid(title_p)
    title_run = title_p.add_run('目  录')
    _set_run_font(title_run, cn_font=FONT_HEI, en_font=en_font,
                  size_pt=SIZE_H1, bold=True)

    # 制表位位置（约 14.5cm，留少量右边距）
    tab_pos_cm = 14.5

    for h in headings:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf = p.paragraph_format
        _set_line_spacing_15(p)
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        _disable_snap_to_grid(p)

        # 缩进：一级不缩进，二级缩进 2 字符
        pPr = p._element.get_or_add_pPr()
        ind = pPr.find(qn('w:ind'))
        if ind is None:
            ind = OxmlElement('w:ind')
            pPr.append(ind)
        ind.set(qn('w:firstLine'), '0')
        ind.set(qn('w:firstLineChars'), '0')
        if h['level'] == 1:
            ind.set(qn('w:left'), '0')
            ind.set(qn('w:leftChars'), '0')
        else:
            ind.set(qn('w:left'), '420')
            ind.set(qn('w:leftChars'), '200')

        # 右对齐 + 点引导线的制表位
        _add_tab_stop(p, tab_pos_cm, alignment='right', leader='dot')

        # 编号 + 双空格 + 标题文本
        entry_text = f"{h['number']}  {h['text']}"
        run = p.add_run(entry_text)
        if h['level'] == 1:
            _set_run_font(run, cn_font=cn_font, en_font=en_font,
                          size_pt=SIZE_BODY, bold=True)
        else:
            _set_run_font(run, cn_font=cn_font, en_font=en_font,
                          size_pt=SIZE_BODY, bold=False)

        # 制表符
        tab_run = p.add_run('\t')
        _set_run_font(tab_run, cn_font=cn_font, en_font=en_font, size_pt=SIZE_BODY)

        # PAGEREF 域（引用书签）
        _add_pageref_field(p, h['bookmark'], cn_font=cn_font,
                           en_font=en_font, size_pt=SIZE_BODY)


def add_hidden_toc_field(doc, cn_font='宋体', en_font='Times New Roman'):
    """添加标准 TOC 域（隐藏，供 Word 中右键"更新域"使用）。
    与 build_toc 配合使用：build_toc 生成静态目录条目确保打开即显示，
    本函数添加隐藏的 TOC 域，用户在 Word 中右键"更新域"可重新生成。
    """
    # 延迟导入避免循环依赖
    from theme import _set_run_font, SIZE_BODY

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

    run4 = paragraph.add_run('（可在 Word 中右键"更新域"重新生成目录）')
    _set_run_font(run4, cn_font=cn_font, en_font=en_font, size_pt=SIZE_BODY)

    run5 = paragraph.add_run()
    fldChar3 = OxmlElement('w:fldChar')
    fldChar3.set(qn('w:fldCharType'), 'end')
    run5._element.append(fldChar3)
