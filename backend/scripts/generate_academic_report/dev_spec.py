"""
系统开发说明书生成模块
格至智能协同教育系统 V3.0
基于学术规范样式系统（theme.py + toc_builder.py）构建
- 学术封面 + 中英文摘要 + 静态目录 + 三节分页页码
- 多级标题自动编号（1 → 1.1 → 1.1.1）+ 书签
- 三线表 + 图题（图X-Y）+ 表题（表X-Y）
"""
import os
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from theme import (
    setup_document_styles, add_heading_styled, add_body_text,
    add_bullet, add_image_with_caption, add_styled_table, add_cover_page,
    add_abstract, add_english_abstract, add_references, add_section_break,
    get_heading_tracker,
)
from toc_builder import (
    HeadingTracker, build_toc, add_hidden_toc_field, reset_bookmark_counter,
)


# ════════════════════════════════════════════════════════
#  预生成标题列表（用于目录生成）
#  ★ 必须与正文 add_heading_styled 调用顺序完全一致 ★
#  书签名 bm_1/bm_2/... 由 HeadingTracker 按添加顺序生成，
#  顺序一致即可保证目录 PAGEREF 与正文书签一一对应。
# ════════════════════════════════════════════════════════
ALL_HEADINGS = [
    # 第一章
    (1, '项目概述'),
    (2, '项目背景'),
    (2, '需求分析'),
    (2, '项目目标与定位'),
    (2, '技术与需求结合点'),
    # 第二章
    (1, '系统总体架构'),
    (2, '系统全景架构'),
    (2, '技术栈选型'),
    (2, '部署架构'),
    (2, '多端交互架构'),
    (2, '系统数据流概述'),
    # 第三章
    (1, '智能体系统设计'),
    (2, '智能体总览'),
    (2, 'LangGraph工作流架构'),
    (2, '多Agent协同教学流程'),
    (2, '智能体模型路由策略'),
    (2, '内置工具体系'),
    (2, '各智能体功能详解'),
    (3, 'Alina 首席规划师'),
    (3, 'Prof.X 知识讲授导师'),
    (3, 'DataBot 数据检索助手'),
    (3, '错题分析师'),
    (3, 'CodeNinja 代码演示助手'),
    (3, 'Mira AI引导图生成师'),
    (3, '排位赛AI教练'),
    (3, '作业诊断师'),
    (3, '作业报告师'),
    (3, '学情策略师'),
    (2, '三维度作业诊断'),
    # 第四章
    (1, '校园Gitea仓库与AI Git教练'),
    (2, '需求背景'),
    (2, 'Gitea集成架构'),
    (3, 'Gitea服务架构'),
    (3, '账号体系设计'),
    (3, '账号绑定流程'),
    (2, '团队协作Git工作流'),
    (3, '团队协作全流程'),
    (3, '仓库管理功能'),
    (3, 'Webhook事件处理'),
    (2, 'AI Git教练核心设计'),
    (3, 'AI Git教练闭环架构'),
    (3, 'Git工作流规则校验体系'),
    (3, 'AI教练提示词设计思路'),
    (3, '反馈数据结构'),
    (3, 'LLM失败兜底机制'),
    (2, '前端Gitea协作展示'),
    (3, 'Clone URL双模式设计'),
    (3, '仓库首页与项目管理页交互设计'),
    (3, '团队协作页面工作流引导'),
    (2, '创新实践与用户体验提升'),
    # 第五章
    (1, 'RAGFlow知识库系统'),
    (2, '知识库架构'),
    (2, '文档处理流程'),
    (2, 'RAG检索增强生成流程'),
    (2, 'LangChain Tool封装'),
    (2, '多模式检索策略'),
    (2, '知识库数据统计'),
    # 第六章
    (1, '前端系统设计'),
    (2, '前端架构'),
    (2, '学生端功能架构'),
    (2, '教师端功能架构'),
    (2, 'AI对话流式交互三级降级策略'),
    (2, '仪表盘Bento网格布局'),
    (2, '教师全息监控面板设计'),
    (2, '用户体验提升策略'),
    # 第七章
    (1, '微信小程序设计'),
    (2, '小程序架构'),
    (2, '云函数代理架构'),
    (2, '多端数据同步设计'),
    (2, '小程序与PC端功能对照表'),
    (2, '移动端适配策略'),
    # 第八章
    (1, '系统部署与安全设计'),
    (2, '部署架构'),
    (2, 'Docker容器编排'),
    (2, 'Nginx反向代理设计'),
    (2, '安全设计体系'),
    (3, 'JWT认证'),
    (3, 'Gitea Webhook HMAC验签'),
    (3, 'campus私有组织访问控制'),
    (3, '代码沙箱安全隔离设计'),
    (2, '数据库连接池设计'),
    # 第九章
    (1, '创新实践与总结'),
    (2, '前沿AI技术融合应用总结'),
    (2, '创新实践清单'),
    (2, '用户体验提升策略总结'),
    (2, '技术与需求结合点回顾'),
    # 附录
    (1, '附录'),
    (2, '附录A：智能体配置参数表'),
    (2, '附录B：API接口清单（18模块汇总表）'),
    (2, '附录C：数据库模型清单（9表）'),
    (2, '附录D：环境配置参数表'),
]


# ════════════════════════════════════════════════════════
#  辅助函数
# ════════════════════════════════════════════════════════

def _add_table_caption(doc, text):
    """添加表题：居中，宋体五号加粗，位于表格上方。"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.line_spacing = 1.5
    pf.space_before = Pt(6)
    pf.space_after = Pt(3)
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(10.5)
    run.font.bold = True
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:ascii'), 'Times New Roman')
    rfonts.set(qn('w:hAnsi'), 'Times New Roman')
    rfonts.set(qn('w:eastAsia'), '宋体')
    return p


def _safe_add_image(doc, image_path, caption, width=5.5):
    """安全添加图片：若文件不存在则添加占位提示，避免脚本中断。"""
    if os.path.exists(image_path):
        add_image_with_caption(doc, image_path, caption, width)
    else:
        add_body_text(doc,
                      f'[{caption}（图片缺失：{os.path.basename(image_path)}）]',
                      bold=False, indent=False)


def _img(images_dir, filename):
    """拼接图片完整路径。"""
    return os.path.join(images_dir, filename)


# ════════════════════════════════════════════════════════
#  主构建函数
# ════════════════════════════════════════════════════════

def build_dev_spec(output_path: str, images_dir: str):
    """构建系统开发说明书Word文档"""
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # ── 1. 创建文档与样式 ──
    doc = Document()
    setup_document_styles(doc)  # 初始化样式 + 重置全局 HeadingTracker
    reset_bookmark_counter()    # 重置书签 ID 计数器（setup_document_styles 不调用）

    # ── 2. 预生成标题列表（用于目录） ──
    # 用独立的临时 tracker 预生成编号和书签，确保与正文 add_heading_styled 生成的书签一致
    pre_tracker = HeadingTracker()
    for level, text in ALL_HEADINGS:
        pre_tracker.add(level, text)

    # ── 3. 封面（第一节，无页眉无页码） ──
    add_cover_page(doc, '系统开发说明书',
                   'Gezhi Intelligent Collaborative Education System',
                   'V3.0', '2026年7月')

    # ── 4. 前置部分（第二节，罗马数字页码） ──
    add_section_break(doc, 'front')

    # 中文摘要
    add_abstract(
        doc,
        '本文档为格至智能协同教育系统的系统开发说明书，系统阐述了基于FastAPI、LangGraph、Vue 3和微信小程序'
        '构建的全栈AI智能教育平台的架构设计与实现方案。系统融合了10个AI智能体协同教学、校园Gitea仓库与'
        'AI Git教练、RAGFlow双层知识库等核心创新技术，针对高校计算机及软件工程专业学生Git团队协作能力'
        '缺失的痛点，构建了Webhook驱动的AI Git教练闭环，实现Git规范自动校验与个性化点评。文档详细描述了'
        '系统五层架构、智能体ReAct工作流、多模型智能路由、RAG检索增强生成、多端适配策略、JWT认证与HMAC验签'
        '安全体系等关键技术，并通过架构图、流程图、数据图表等视觉工具增强可读性，为同类智能教育系统建设提供参考。',
        ['格至系统', 'AI智能体', 'Gitea仓库', 'AI Git教练', 'RAGFlow']
    )

    # 英文摘要
    add_english_abstract(
        doc,
        'This document is the System Development Specification for the Gezhi Intelligent '
        'Collaborative Education System, detailing the architecture design and implementation '
        'of a full-stack AI-powered educational platform built on FastAPI, LangGraph, Vue 3, '
        'and WeChat Mini Program. The system integrates ten AI agents for collaborative teaching, '
        'a campus Gitea repository with an AI Git Coach, and a dual-layer RAGFlow knowledge base. '
        'To address the gap in Git team collaboration skills among computer science and software '
        'engineering students, the system implements a Webhook-driven AI Git Coach loop for '
        'automated Git specification validation and personalized feedback. The document covers '
        'the five-layer architecture, agent ReAct workflow, multi-model intelligent routing, '
        'RAG retrieval-augmented generation, multi-end adaptation, JWT authentication, and '
        'HMAC signature verification, with diagrams and charts for enhanced readability.',
        ['Gezhi System', 'AI Agents', 'Gitea Repository', 'AI Git Coach', 'RAGFlow']
    )

    # 目录（使用预生成的标题列表，书签与正文一致）
    build_toc(doc, pre_tracker.headings)
    add_hidden_toc_field(doc)

    # ── 5. 正文（第三节，页眉 + 阿拉伯数字页码从 1 开始） ──
    add_section_break(doc, 'body')

    # ============================================================
    # 第一章 项目概述
    # ============================================================
    add_heading_styled(doc, '项目概述', level=1)

    # ---- 1.1 项目背景 ----
    add_heading_styled(doc, '项目背景', level=2)
    add_body_text(doc,
        '当前我国高校计算机科学与软件工程专业的培养体系中，版本控制与团队协作能力的训练长期处于薄弱环节。'
        '通过对国内多所"双一流"高校与地方本科院校的调研发现，绝大多数课程仍以单人独立完成作业为主，'
        '学生缺乏在真实工程环境中使用 Git 进行分支管理、Pull Request 协作、代码评审与冲突解决的经验。'
        '与此同时，人工智能尤其是大语言模型的快速发展为高等教育提供了新的技术手段，'
        '如何将多智能体协同教学、检索增强生成（RAG）、AI 代码教练等先进技术有机融入教学场景，'
        '形成"AI 教学助手 + Git 实训平台 + 知识库检索"三位一体的协同教育生态，'
        '是当前新工科建设亟待破解的关键命题。')
    add_body_text(doc,
        '在此背景下，格至智能协同教育系统应运而生。本系统面向高校计算机/软件工程专业的本科生与教师，'
        '依托校园私有部署的 Gitea 代码托管平台、RAGFlow 知识库引擎与阿里云百炼多模型服务，'
        '构建一个覆盖"教—学—练—评—协"全链路的智能协同教育平台。'
        '系统通过 10 个专业 AI 智能体协同工作，提供苏格拉底启发式教学、个性化错题诊断、'
        '作业三维度评估、班级学情分析等教学服务；通过校园 Gitea 与 AI Git 教练闭环，'
        '以 Webhook 驱动的方式对学生的 Git 工作流进行规则校验与 LLM 个性化点评，'
        '弥补传统课程在工程协作实训方面的不足。')
    add_body_text(doc,
        '系统在技术架构上采用前后端分离 + 微服务化的设计思想：后端基于 FastAPI 异步框架构建 18 个核心 API 模块，'
        '集成 LangGraph 与 LangChain 实现多智能体工作流编排；前端采用 Vue 3 ESM 单页应用，'
        '配合 Tailwind CSS、ECharts、Three.js、Monaco Editor 等组件库，构建学生端 11 个视图与教师端 8 个视图；'
        '同时提供微信小程序端 17 个页面，通过云函数代理实现多端数据同步，满足学生移动学习场景需求。')

    # ---- 1.2 需求分析 ----
    add_heading_styled(doc, '需求分析', level=2)
    add_body_text(doc,
        '基于对目标用户群体（高校计算机/软件工程专业本科生与任课教师）的深度访谈与问卷调研，'
        '系统识别出新时代大学生在学习过程中的四大核心痛点：')
    add_body_text(doc,
        '痛点一：Git 使用率低。调查显示，高校学生中 Git 的使用率普遍偏低，即便使用也多停留在 commit、push 等基础命令，'
        '对分支策略、Pull Request 流程、代码评审等团队协作核心实践几乎一无所知。这与企业对软件工程师的协作能力要求形成巨大鸿沟。')
    add_body_text(doc,
        '痛点二：团队协作流程缺失。传统课程作业以单人独立完成为主，学生缺乏在多人协作环境中处理分支冲突、'
        '进行代码评审、遵循 commit message 规范等实战经验，毕业后难以快速融入企业研发团队。')
    add_body_text(doc,
        '痛点三：个性化学习指导不足。班级授课模式下，教师难以针对每位学生的学习进度、知识薄弱点提供一对一指导，'
        '学生遇到问题时往往只能通过搜索引擎碎片化地获取答案，缺乏系统化的启发式教学引导。')
    add_body_text(doc,
        '痛点四：知识检索效率低。学生在学习过程中需要查阅大量课件、教材、代码示例，'
        '传统关键词检索难以理解语义，导致检索效率低下、知识获取碎片化，难以形成体系化的知识图谱。')
    _safe_add_image(doc, _img(images_dir, 'git_pain_points.png'),
                    '图1-1 高校学生痛点分布统计')

    # ---- 1.3 项目目标与定位 ----
    add_heading_styled(doc, '项目目标与定位', level=2)
    add_body_text(doc,
        '本项目旨在构建一个 AI 驱动的智能教育协同平台，融合多智能体协同教学、Git 协作实训与知识库检索三大核心能力，'
        '为高校计算机/软件工程专业学生提供从知识学习、代码实践到团队协作的一站式智能教育服务。'
        '系统的核心定位包括以下四个维度：')
    add_bullet(doc, '教学维度：通过 10 个专业 AI 智能体协同工作，提供苏格拉底启发式教学、支架式四阶段教学、'
                    '个性化错题诊断与班级学情分析，实现"千人千面"的个性化教学体验。')
    add_bullet(doc, '工程维度：依托校园私有 Gitea 平台与 AI Git 教练闭环，以 Webhook 驱动的方式自动化点评学生 Git 工作流，'
                    '弥补传统教学在工程协作实训方面的不足。')
    add_bullet(doc, '知识维度：基于 RAGFlow 构建公共课程 + 学生私有的双层知识库，'
                    '通过 DeepDOC 文档解析与向量检索技术提供语义化的知识检索与增强生成能力。')
    add_bullet(doc, '体验维度：覆盖 PC 端、微信小程序端的多端同步学习体验，'
                    '配合实时事件总线、动画交互、可视化引导等手段，打造沉浸式、可视化、可追踪的学习过程。')

    # ---- 1.4 技术与需求结合点 ----
    add_heading_styled(doc, '技术与需求结合点', level=2)
    add_body_text(doc,
        '系统针对识别出的五大需求痛点，分别设计对应的技术方案与实现路径，形成需求—技术—实现的完整映射关系，'
        '确保每一项用户需求都能通过具体的技术手段落地实现。')
    _add_table_caption(doc, '表1-1 需求—技术结合点映射表')
    add_styled_table(doc,
        headers=['需求痛点', '技术方案', '实现路径'],
        rows=[
            ['Git协作能力缺失', '校园Gitea+AI Git教练', 'Webhook驱动自动点评+规则校验'],
            ['个性化学习指导不足', 'LangGraph多智能体', '苏格拉底启发式教学+支架式四阶段'],
            ['知识检索效率低', 'RAGFlow双层知识库', '公共课程+私有资料向量化检索'],
            ['学习进度不可视', 'Bento仪表盘+全息监控', '实时数据聚合+事件总线推送'],
            ['移动端学习缺失', '微信小程序', '云函数代理+多端数据同步'],
        ])

    # ============================================================
    # 第二章 系统总体架构
    # ============================================================
    add_heading_styled(doc, '系统总体架构', level=1)

    # ---- 2.1 系统全景架构 ----
    add_heading_styled(doc, '系统全景架构', level=2)
    add_body_text(doc,
        '系统采用经典五层架构设计，自上而下分别为用户层、接入层、应用层、服务层与数据层，'
        '各层之间通过明确定义的接口与协议进行交互，确保系统的可扩展性、可维护性与高可用性。'
        '整体架构遵循"前后端分离 + 服务化"的设计原则，便于独立部署、独立扩展与独立演进。')
    _safe_add_image(doc, _img(images_dir, 'system_overview.png'),
                    '图2-1 系统全景架构图')
    add_body_text(doc,
        '用户层：支持 PC 浏览器（Chrome、Edge 等现代浏览器）与微信小程序两类客户端访问入口，'
        '满足学生在不同场景下的学习需求。其中 PC 浏览器面向深度学习与编程实战场景，'
        '微信小程序面向碎片化学习与移动查询场景。')
    add_body_text(doc,
        '接入层：由 Nginx 反向代理与微信云函数 apiProxy 共同构成。Nginx 负责 HTTPS 终结、'
        '静态资源服务与多路径反向代理（/api/→FastAPI、/gitea/→Gitea、/static/→静态资源）；'
        '微信云函数 apiProxy 作为小程序与后端之间的代理层，解决小程序合法域名限制与超时控制问题。')
    add_body_text(doc,
        '应用层：包含 Vue 3 SPA 学生端、React 登录页、微信小程序前端三类前端应用。'
        'Vue 3 SPA 采用 ESM importmap 加载方式，无需构建步骤即可在浏览器中直接运行；'
        'React 登录页独立部署用于统一登录入口；小程序前端基于原生框架开发，配合自定义 TabBar 与导航栏。')
    add_body_text(doc,
        '服务层：核心业务服务层，包含 FastAPI 后端的 18 个 API 模块、Gitea 代码托管服务、'
        'RAGFlow 知识库服务以及阿里云百炼多模型 LLM 服务。FastAPI 采用 Uvicorn ASGI 服务器，'
        '配置 4 个 worker 进程以充分利用多核 CPU；Gitea 与 RAGFlow 均通过 Docker Compose 编排部署。')
    add_body_text(doc,
        '数据层：包含 MySQL 关系型数据库（用户数据、业务数据、Gitea 数据共享实例）、'
        'MinIO 对象存储（RAGFlow 文档与向量索引）、Elasticsearch 全文检索引擎（RAGFlow 文档检索）、'
        'Redis 内存数据库（缓存与会话管理）。数据层各组件独立部署，通过 SQLAlchemy ORM 与连接池统一访问。')

    # ---- 2.2 技术栈选型 ----
    add_heading_styled(doc, '技术栈选型', level=2)
    add_body_text(doc,
        '系统技术栈的选型遵循"成熟稳定 + 性能优先 + 易于维护"的原则，'
        '在每一层都选择业界主流且经过生产验证的技术方案，确保系统的长期可演进性。'
        '下表列出了系统各层核心技术的选型与说明：')
    _add_table_caption(doc, '表2-1 系统技术栈选型表')
    add_styled_table(doc,
        headers=['层次', '技术选型', '说明'],
        rows=[
            ['后端框架', 'FastAPI + Uvicorn', '异步高性能，4 workers'],
            ['AI框架', 'LangGraph + LangChain', 'ReAct工作流+工具调用'],
            ['数据库', 'MySQL + SQLAlchemy', '连接池pool_size=20'],
            ['前端框架', 'Vue 3 ESM + Tailwind CSS', '无构建步骤SPA'],
            ['图表库', 'ECharts + Three.js + p5.js', '数据可视化'],
            ['代码托管', 'Gitea 1.26.4 (Docker)', 'campus私有组织'],
            ['RAG引擎', 'RAGFlow v0.25.6 (Docker)', 'DeepDOC解析+向量检索'],
            ['LLM', '阿里云百炼(多模型)', 'qwen3.7-max/plus/kimi-code'],
            ['反向代理', 'Nginx + Let\'s Encrypt', 'HTTPS+多路径代理'],
            ['容器编排', 'Docker Compose', 'Gitea+RAGFlow'],
            ['小程序', '微信小程序+云开发', '云函数代理'],
        ])

    # ---- 2.3 部署架构 ----
    add_heading_styled(doc, '部署架构', level=2)
    add_body_text(doc,
        '系统采用单服务器集中部署模式，部署于公网服务器（IP: 154.201.71.151），'
        '通过 Nginx 统一接入所有外部流量。FastAPI 后端以 systemd 服务方式运行，监听 8516 端口，'
        '配置 4 个 Uvicorn worker 进程以充分利用多核 CPU 性能；MySQL 数据库监听 3306 端口，'
        '为业务系统与 Gitea 共享同一实例（通过不同数据库隔离）；Gitea 与 RAGFlow 通过 Docker Compose 编排部署，'
        'Gitea 暴露 3000（HTTP）与 2222（SSH）端口，RAGFlow 依赖独立的 MySQL、MinIO、Elasticsearch、Redis 容器。')
    _safe_add_image(doc, _img(images_dir, 'deployment_arch.png'),
                    '图2-2 部署架构图')

    # ---- 2.4 多端交互架构 ----
    add_heading_styled(doc, '多端交互架构', level=2)
    add_body_text(doc,
        '系统支持 PC 浏览器、微信小程序与 Gitea Webhook 三类外部入口与后端进行交互。'
        'PC 浏览器通过 Nginx 反向代理访问 FastAPI 后端 API，支持 SSE 流式响应以实现 AI 对话的实时打字效果；'
        '微信小程序通过云函数 apiProxy 间接调用后端 API，因云函数不支持 SSE，小程序端 AI 对话采用非流式模式；'
        'Gitea 平台在发生 push、pull_request 等事件时通过 Webhook 主动推送事件到后端指定端点，'
        '触发 AI Git 教练异步点评流程。三类入口共享统一的 JWT 认证体系与数据模型，确保多端数据一致性。')
    _safe_add_image(doc, _img(images_dir, 'multi_end_arch.png'),
                    '图2-3 多端交互架构图')

    # ---- 2.5 系统数据流概述 ----
    add_heading_styled(doc, '系统数据流概述', level=2)
    add_body_text(doc,
        '系统的核心数据流可概括为以下几条主线：'
        '（1）AI 对话数据流：前端发起 POST /api/chat/stream 请求 → FastAPI 路由 → LangGraph 工作流编排 → '
        '模型路由策略选择 LLM → LLM 生成响应 → SSE 流式回传前端；'
        '（2）RAG 检索数据流：用户提问 → 寒暄检测 → 检索公共数据集 → 检索私有数据集 → '
        '拼装上下文 → LLM 生成带引用来源的回答；'
        '（3）Git 教练数据流：学生 push 代码 → Gitea 触发 Webhook → 后端验签 → 同步项目数据 → '
        'BackgroundTasks 异步触发 → 规则校验 → LLM 点评 → 写回数据库 → 前端展示反馈；'
        '（4）作业诊断数据流：学生提交作业 → Alina 规划维度评分 → CodeNinja 代码维度评分 → '
        'Prof.X 知识维度评分 → 综合诊断报告生成。'
        '各数据流之间通过事件总线（homework-submitted、interaction-completed 等事件）实现解耦协同。')

    # ============================================================
    # 第三章 智能体系统设计
    # ============================================================
    add_heading_styled(doc, '智能体系统设计', level=1)

    # ---- 3.1 智能体总览 ----
    add_heading_styled(doc, '智能体总览', level=2)
    add_body_text(doc,
        '系统设计了 10 个专业化 AI 智能体，覆盖教学、诊断、分析、可视化等核心教学场景。'
        '每个智能体都有明确的角色定位、专属的底座模型与精心设计的系统提示词，'
        '通过 LangGraph 工作流编排实现协同工作。智能体的底座模型选择遵循"任务—模型"匹配原则：'
        '规划与复杂推理任务选用 qwen3.7-max，常规教学任务选用 qwen3.7-plus，代码任务选用 kimi-k2.7-code，'
        '图像生成任务选用 qwen-image-2.0-pro。')
    _add_table_caption(doc, '表3-1 智能体配置总览表')
    add_styled_table(doc,
        headers=['智能体ID', '名称', '角色', '底座模型', '类别'],
        rows=[
            ['agent_planner', 'Alina', '首席规划师', 'qwen3.7-max', '文本'],
            ['agent_tutor', 'Prof.X', '知识讲授导师(费曼技巧)', 'qwen3.7-plus', '文本'],
            ['agent_researcher', 'DataBot', '数据检索助手(RAG)', 'qwen3.6-plus', '文本'],
            ['agent_mistake_analyst', '错题分析师', '错题诊断与复习路径', 'qwen3.7-plus', '文本'],
            ['agent_coder', 'CodeNinja', '代码演示助手', 'kimi-k2.7-code', '文本'],
            ['agent_visual_guide', 'Mira', 'AI引导图生成师', 'qwen-image-2.0-pro', '图像'],
            ['agent_ranked_coach', '排位赛AI教练', '排位诊断与冲分策略', 'qwen3.7-plus', '文本'],
            ['agent_homework_diagnoser', '作业诊断师', '三维度作业诊断', 'qwen3.7-plus', '文本'],
            ['agent_homework_reporter', '作业报告师', '班级作业分析报告', 'qwen3.7-plus', '文本'],
            ['agent_analytics_advisor', '学情策略师', '班级学情干预策略', 'qwen3.7-plus', '文本'],
        ])
    _safe_add_image(doc, _img(images_dir, 'agent_overview_chart.png'),
                    '图3-1 智能体模型分布')

    # ---- 3.2 LangGraph工作流架构 ----
    add_heading_styled(doc, 'LangGraph工作流架构', level=2)
    add_body_text(doc,
        '系统采用 LangGraph 框架构建智能体工作流，基于 StateGraph 状态图实现 ReAct（Reasoning + Acting）'
        '推理执行循环。LangGraph 相比于传统的 LangChain Agent Executor，提供了更细粒度的状态管理与流程控制能力，'
        '支持复杂的多节点协同、条件路由、状态记忆与断点续跑等高级特性，更适合构建生产级的多智能体协同系统。')
    _safe_add_image(doc, _img(images_dir, 'langgraph_workflow.png'),
                    '图3-2 LangGraph ReAct工作流架构图')
    add_body_text(doc,
        'StateGraph 核心结构包含以下关键节点与边：'
        'agent 节点负责调用 LLM 进行推理决策，根据当前状态（消息历史、工具调用记录等）生成下一步动作；'
        'tools 节点为 ToolNode 工具执行节点，负责实际执行 LLM 决策调用的工具（如 RAG 检索、代码执行、图示生成）；'
        'tools_condition 为条件路由边，根据 agent 节点的输出判断是否需要继续调用工具，'
        '若 LLM 输出中包含 tool_calls 则路由至 tools 节点，否则路由至 END 节点结束本轮对话；'
        'MemorySaver 为状态记忆组件，基于 checkpointer 机制持久化每轮对话的状态快照，'
        '支持基于 thread_id 的多轮会话隔离与历史回溯。')
    add_body_text(doc,
        '工作流执行流程为：用户输入 → 加载历史状态（MemorySaver）→ agent 节点 LLM 推理 → '
        'tools_condition 路由判断 → 若需调用工具则进入 tools 节点执行 → 工具结果回写状态 → '
        '再次进入 agent 节点 → 循环直至 LLM 输出不再包含 tool_calls → END 节点输出最终响应。'
        '整个循环过程通过 SSE 流式协议实时推送 token 到前端，实现打字机式的对话体验。')

    # ---- 3.3 多Agent协同教学流程 ----
    add_heading_styled(doc, '多Agent协同教学流程', level=2)
    add_body_text(doc,
        '系统的多智能体协同教学遵循苏格拉底启发式教学法与支架式四阶段教学模型。'
        '苏格拉底启发式教学法强调通过提问引导学习者自主发现知识，而非直接给出答案；'
        '支架式教学则将复杂任务分解为多个梯度递进的子任务，为学习者提供适时支持并逐步撤除支架。'
        '两种教学法相结合，形成系统独特的"引导—探索—实践—纠错"教学闭环。')
    _safe_add_image(doc, _img(images_dir, 'multi_agent_flow.png'),
                    '图3-3 多Agent协同教学流程图')
    add_body_text(doc,
        '支架式四阶段教学模型具体包括：'
        '（1）概念引入阶段：由 Prof.X 知识讲授导师以费曼技巧用通俗语言解释新概念，'
        '结合生活化类比降低认知门槛；'
        '（2）直观图解阶段：由 Mira AI 引导图生成师生成 Mermaid 流程图、思维导图等可视化辅助材料，'
        '帮助学生建立直观印象；'
        '（3）代码实战阶段：由 CodeNinja 代码演示助手提供代码示例，但仅展示关键片段而非完整代码，'
        '引导学生自主补全；'
        '（4）纠错通关阶段：由错题分析师与作业诊断师对学生提交的代码与作业进行诊断，'
        '指出错误并提供改进建议，确保知识掌握的牢固性。')
    add_body_text(doc,
        '为保证教学效果与对话节奏，系统对每轮智能体回复设定严格约束：'
        '每轮回复控制在 200 字以内，避免信息过载；严禁直接给出完整代码，必须保留思考与动手空间；'
        '回复语气以亲切鼓励为主，面向本科生群体调整表达风格；'
        '回复内容必须包含明确的引导性问题或下一步行动建议，推动教学循环持续演进。')

    # ---- 3.4 智能体模型路由策略 ----
    add_heading_styled(doc, '智能体模型路由策略', level=2)
    add_body_text(doc,
        '系统通过 resolve_runtime_model_id 函数实现智能模型路由策略，根据当前任务的类型与复杂度，'
        '动态选择最合适的 LLM 模型进行响应。模型路由策略兼顾性能与成本，'
        '将简单任务分流到低成本模型，将复杂任务路由到高性能模型，'
        '在保证教学质量的同时有效控制 LLM 调用成本。')
    _safe_add_image(doc, _img(images_dir, 'model_routing.png'),
                    '图3-4 模型路由策略图')
    add_body_text(doc,
        'resolve_runtime_model_id 路由逻辑具体规则如下：'
        '（1）若任务涉及代码生成、代码理解、代码调试等编程类任务，路由至 kimi-k2.7-code 模型，'
        '该模型在代码任务上表现优异；'
        '（2）若任务涉及复杂规划、多步推理、策略制定等高复杂度任务，路由至 qwen3.7-max 模型，'
        '该模型具备最强的推理能力；'
        '（3）若任务涉及知识检索、资料查询等检索类任务，路由至 qwen3.7-plus 模型，'
        '兼顾性能与成本；'
        '（4）若任务涉及图像生成、可视化引导等图像类任务，路由至 qwen-image-2.0-pro 模型；'
        '（5）默认情况下路由至 qwen3.7-plus 模型，作为通用兜底选择。'
        '路由决策基于智能体配置与运行时上下文，支持动态调整。')

    # ---- 3.5 内置工具体系 ----
    add_heading_styled(doc, '内置工具体系', level=2)
    add_body_text(doc,
        '系统为智能体设计了三个内置工具，扩展 LLM 的能力边界，使其能够主动获取外部信息、'
        '执行代码验证、生成可视化素材。工具采用 LangChain Tool 协议封装，'
        '通过 LangGraph 的 ToolNode 节点统一调度执行。')
    _safe_add_image(doc, _img(images_dir, 'tool_call_flow.png'),
                    '图3-5 工具调用流程图')
    add_bullet(doc, 'query_data_structure_knowledge：RAG 检索工具，通过 RAGFlow 进行知识库检索，'
                    '为学生提供数据结构、算法等课程知识的专业解答。该工具内部通过 RAGFLOW_CHAT_ID 创建会话，'
                    '调用 completion 接口获取检索增强后的回答，并提取 reference.chunks 中的 document_name '
                    '作为引用来源返回给前端。')
    add_bullet(doc, 'execute_python_code：Python 代码沙箱执行工具，使用 subprocess 隔离子进程执行学生提交的 Python 代码，'
                    '设置 5 秒超时限制防止死循环，并通过安全关键字拦截机制（os.system、subprocess、rmtree 等）'
                    '阻止恶意代码执行，确保系统安全。')
    add_bullet(doc, 'generate_algorithm_diagram：算法图示生成工具，基于 matplotlib 与 networkx 库'
                    '生成链表、树、图等数据结构的可视化示意图，帮助学生直观理解算法原理。'
                    '该工具由 Mira 智能体调用，生成结果以图片形式返回前端展示。')

    # ---- 3.6 各智能体功能详解 ----
    add_heading_styled(doc, '各智能体功能详解', level=2)

    add_heading_styled(doc, 'Alina 首席规划师', level=3)
    add_body_text(doc,
        'Alina 是系统的首席规划师智能体，底座模型为 qwen3.7-max，具备最强的推理与规划能力。'
        '其主要职责是作为多智能体协同的"指挥官"，根据用户输入分析任务类型，'
        '制定教学策略与执行计划，协调其他智能体协同完成任务。'
        '在教学场景中，Alina 负责分析学生的学习目标与当前水平，制定个性化的学习路径，'
        '将复杂学习任务分解为可执行的子任务，并在适当时机调度 Prof.X、CodeNinja、Mira 等智能体介入。'
        '此外，Alina 还承担作业诊断的规划维度评分职责，评估学生作业的整体思路与方案设计合理性。')

    add_heading_styled(doc, 'Prof.X 知识讲授导师', level=3)
    add_body_text(doc,
        'Prof.X 是系统的知识讲授导师智能体，底座模型为 qwen3.7-plus，采用费曼技巧进行知识讲授。'
        '费曼技巧的核心是用最通俗的语言解释复杂概念，仿佛在向外行讲解，'
        '通过类比、举例、拆解等方式降低知识理解门槛。'
        'Prof.X 在教学场景中承担核心的知识讲授职责，从概念引入、原理阐述到应用举例全程引导，'
        '配合 Mira 生成的可视化素材强化理解。在作业诊断中，Prof.X 负责知识维度评分，'
        '评估学生作业对课程知识点的掌握与运用情况。')

    add_heading_styled(doc, 'DataBot 数据检索助手', level=3)
    add_body_text(doc,
        'DataBot 是系统的数据检索助手智能体，底座模型为 qwen3.6-plus，专门负责 RAG 知识库检索任务。'
        '当用户提问涉及课程知识、教材内容、技术文档等可检索信息时，DataBot 通过 query_data_structure_knowledge '
        '工具调用 RAGFlow 进行检索，获取相关文档片段，并结合检索结果生成带引用来源的回答。'
        'DataBot 的工作流程包括：寒暄检测（避免无意义检索）→ 公共数据集检索 → 私有数据集检索 → '
        '上下文拼装 → LLM 生成 → 附加引用来源。')

    add_heading_styled(doc, '错题分析师', level=3)
    add_body_text(doc,
        '错题分析师智能体专注于学生错题的诊断与复习路径规划，底座模型为 qwen3.7-plus。'
        '当学生在考试或练习中出现错误时，错题分析师会对错题进行深度分析，'
        '识别错误的根本原因（概念不清、计算失误、逻辑错误等），并基于错误模式为学生规划个性化的复习路径。'
        '错题分析师还负责维护学生的错题本，自动归类整理错题，定期生成复习建议，'
        '帮助学生避免同类错误的重复发生。')

    add_heading_styled(doc, 'CodeNinja 代码演示助手', level=3)
    add_body_text(doc,
        'CodeNinja 是系统的代码演示助手智能体，底座模型为 kimi-k2.7-code，专门针对代码任务优化。'
        'CodeNinja 在教学场景中负责提供代码示例、解释代码原理、调试代码错误等任务。'
        '遵循系统"禁止直接给完整代码"的教学原则，CodeNinja 仅展示关键代码片段与思路提示，'
        '引导学生自主补全完整实现。在作业诊断中，CodeNinja 负责代码维度评分，'
        '评估学生作业的代码质量、规范性与可读性。')

    add_heading_styled(doc, 'Mira AI引导图生成师', level=3)
    add_body_text(doc,
        'Mira 是系统的 AI 引导图生成师智能体，底座模型为 qwen-image-2.0-pro，是系统中唯一的图像生成类智能体。'
        'Mira 的主要职责是根据教学内容生成 Mermaid 流程图、思维导图、数据结构示意图等可视化辅助材料，'
        '帮助学生建立直观印象。Mira 还调用 generate_algorithm_diagram 工具生成基于 matplotlib 与 networkx 的'
        '数据结构可视化图示，覆盖链表、树、图等常见数据结构。'
        '通过可视化引导，Mira 显著降低了复杂概念的理解难度，提升了学习效率。')

    add_heading_styled(doc, '排位赛AI教练', level=3)
    add_body_text(doc,
        '排位赛 AI 教练智能体专门服务于系统的排位竞赛功能，底座模型为 qwen3.7-plus。'
        '其主要职责是根据学生在排位赛中的表现进行诊断分析，识别学生的薄弱知识点与能力短板，'
        '并制定个性化的冲分策略。排位赛 AI 教练会综合考虑学生的当前段位、历史战绩、'
        '常见错误模式等因素，给出针对性的训练建议与题目推荐，'
        '帮助学生在排位赛中持续提升能力与段位。')

    add_heading_styled(doc, '作业诊断师', level=3)
    add_body_text(doc,
        '作业诊断师智能体负责对学生提交的作业进行三维度诊断，底座模型为 qwen3.7-plus。'
        '三维度诊断包括：规划维度（由 Alina 评估作业整体思路与方案设计）、'
        '代码维度（由 CodeNinja 评估代码质量与规范性）、知识维度（由 Prof.X 评估知识点掌握情况）。'
        '作业诊断师协调三个智能体协同工作，综合三维评分生成完整的作业诊断报告，'
        '为学生提供全方位、多维度的作业反馈。')

    add_heading_styled(doc, '作业报告师', level=3)
    add_body_text(doc,
        '作业报告师智能体负责生成班级层面的作业分析报告，底座模型为 qwen3.7-plus。'
        '其主要职责是汇总全班学生的作业提交情况、三维度评分分布、常见错误模式等数据，'
        '生成面向教师的班级作业分析报告，帮助教师快速掌握班级整体的作业完成情况与薄弱环节。'
        '报告内容包括班级平均分、分数段分布、高频错误统计、典型作业展示等模块。')

    add_heading_styled(doc, '学情策略师', level=3)
    add_body_text(doc,
        '学情策略师智能体负责班级学情分析与干预策略制定，底座模型为 qwen3.7-plus。'
        '其主要职责是基于全班学生的学习数据（作业完成情况、错题分布、知识点掌握情况、'
        'AI 交互频次等）进行综合分析，识别班级整体与个别学生的学情问题，'
        '并制定针对性的干预策略。学情策略师支持"一键干预"功能，'
        '教师可基于 AI 建议快速下发个性化学习任务、调整教学进度或发起专项辅导。')

    # ---- 3.7 三维度作业诊断 ----
    add_heading_styled(doc, '三维度作业诊断', level=2)
    add_body_text(doc,
        '三维度作业诊断是系统教学评估的核心创新之一，通过 Alina、CodeNinja、Prof.X 三个智能体协同工作，'
        '从规划、代码、知识三个维度对学生作业进行全面诊断，各维度评分采用 0-100 分制，'
        '最终综合形成立体化的作业诊断报告，避免了传统单一维度评分的片面性。')
    _safe_add_image(doc, _img(images_dir, 'homework_diagnosis_flow.png'),
                    '图3-6 三维度作业诊断流程图')
    add_body_text(doc,
        '三维度诊断的具体分工为：'
        '（1）Alina 规划维度：评估学生作业的整体思路、方案设计、架构合理性，'
        '关注"为什么这样做"而非"做了什么"，满分 100 分；'
        '（2）CodeNinja 代码维度：评估学生作业的代码质量、规范性、可读性、性能，'
        '关注代码实现层面的工程素养，满分 100 分；'
        '（3）Prof.X 知识维度：评估学生作业对课程知识点的掌握与运用情况，'
        '关注知识理解与应用的准确性，满分 100 分。'
        '三维度评分综合后形成总评，并附带具体的改进建议，帮助学生全方位提升作业质量。')

    # ============================================================
    # 第四章 校园Gitea仓库与AI Git教练（重点章节）
    # ============================================================
    add_heading_styled(doc, '校园Gitea仓库与AI Git教练', level=1)

    # ---- 4.1 需求背景 ----
    add_heading_styled(doc, '需求背景', level=2)
    add_body_text(doc,
        '版本控制与团队协作是软件工程师的核心职业素养，然而调研显示，'
        '高校计算机/软件工程专业学生在 Git 团队协作能力方面普遍存在严重短板。'
        '本节通过对多所高校在校生与应届毕业生的调研数据分析，'
        '深度剖析高校学生 Git 团队协作能力缺失的现状、成因与影响，'
        '为系统 Gitea 集成与 AI Git 教练设计提供需求依据。')
    _safe_add_image(doc, _img(images_dir, 'git_proficiency.png'),
                    '图4-1 学生Git使用熟练度统计')
    add_body_text(doc,
        '调研数据揭示了高校学生 Git 能力的四个关键现状：'
        '（1）仅 45% 学生掌握 Git 基础命令（init、add、commit、push），'
        '其余 55% 学生从未使用过 Git 或仅停留在概念认知阶段；'
        '（2）分支管理能力薄弱，仅 28% 学生能够熟练使用 branch、checkout、merge 等分支操作命令，'
        '大部分学生仍在主干上直接开发；'
        '（3）Pull Request 流程认知严重不足，仅 15% 学生了解 PR 流程并实际使用过，'
        '代码评审实践几乎空白；'
        '（4）冲突解决能力极度欠缺，仅 8% 学生能够独立处理 merge 冲突，'
        '大部分学生遇到冲突即放弃协作。')
    add_body_text(doc,
        '造成上述现状的成因是多方面的：'
        '其一，高校课程体系中缺乏专门的版本控制与团队协作教学模块，'
        'Git 通常仅作为某个实践课程的附带工具简单介绍；'
        '其二，课程作业以单人独立完成为主，缺乏真实的多人协作场景驱动学生主动学习 Git；'
        '其三，缺少配套的实训平台与指导反馈机制，学生即便尝试使用 Git 也难以获得及时、专业的指导，'
        '容易因挫折放弃。系统通过校园 Gitea 平台与 AI Git 教练闭环，'
        '正是针对上述成因设计的系统性解决方案。')

    # ---- 4.2 Gitea集成架构 ----
    add_heading_styled(doc, 'Gitea集成架构', level=2)

    # 4.2.1
    add_heading_styled(doc, 'Gitea服务架构', level=3)
    add_body_text(doc,
        '系统采用 Gitea 1.26.4 作为校园代码托管平台，通过 Docker 容器化方式部署。'
        'Gitea 是一款轻量级、易部署的自托管 Git 服务，相比 GitLab 资源占用更少、部署更简单，'
        '相比 GitHub 具备数据私有性与定制化能力，非常适合校园场景的私有化部署。'
        'Gitea 服务监听 3000（HTTP）与 2222（SSH）端口，分别承载 Web 界面访问与 Git 协议操作。')
    _safe_add_image(doc, _img(images_dir, 'gitea_service_arch.png'),
                    '图4-2 Gitea服务架构图')
    add_body_text(doc,
        '在数据存储层面，Gitea 复用系统主 MySQL 数据库实例，使用独立的 gitea 数据库隔离存储，'
        '避免与业务数据库产生冲突。Gitea 的核心数据表包括 user（用户表）、repository（仓库表）、'
        'org（组织表）、team（团队表）、access（权限表）等，通过 ORM 框架统一管理。'
        '系统在 Gitea 中创建 campus 私有组织作为所有教学项目的容器，'
        '所有学生仓库均归属于该组织，通过组织私有属性实现访问控制——仅注册的校园用户可 clone 仓库，'
        '有效防止代码外泄与抄袭。')

    # 4.2.2
    add_heading_styled(doc, '账号体系设计', level=3)
    add_body_text(doc,
        '系统设计了与校园身份体系深度绑定的 Gitea 账号命名规范，确保账号的可识别性与可管理性。'
        '学生账号命名规范为 stu_{学号}（如 stu_2023001），教师账号命名规范为 tea_{工号}（如 tea_1001），'
        '邮箱规范为 {学号或工号}@gezhi.local。该命名规范的优势在于：'
        '（1）账号与校园身份一一对应，便于追溯管理；'
        '（2）通过前缀 stu/tea 快速区分学生与教师角色；'
        '（3）@gezhi.local 邮箱域统一标识校园账号，避免与外部账号混淆。'
        'Gitea 账号通过后端 API 自动创建，密码与学生登录密码解耦，'
        '学生无需记忆额外的 Gitea 密码，clone 操作通过 personal token 完成认证。')

    # 4.2.3
    add_heading_styled(doc, '账号绑定流程', level=3)
    add_body_text(doc,
        '系统设计了完整的 Gitea 账号自动绑定流程，学生首次登录系统时自动完成 Gitea 账号创建与绑定，'
        '无需任何手动操作，极大降低了使用门槛。账号绑定流程的核心步骤如下：')
    _safe_add_image(doc, _img(images_dir, 'gitea_account_binding.png'),
                    '图4-3 账号绑定与权限管理流程图')
    add_bullet(doc, '步骤1：学生通过 JWT 登录系统，后端校验身份并加载学生信息；')
    add_bullet(doc, '步骤2：系统根据学生学号生成 Gitea 账号信息（stu_{学号}、{学号}@gezhi.local），'
                    '并生成随机强密码；')
    add_bullet(doc, '步骤3：调用 Gitea 管理员 API 创建 Gitea 用户，确保账号在 Gitea 平台真实可用；')
    add_bullet(doc, '步骤4：在 gitea_account_bindings 表中记录绑定关系（学生ID、Gitea用户名、邮箱等），'
                    '建立校园身份与 Gitea 身份的映射；')
    add_bullet(doc, '步骤5：将学生加入 campus 组织的 Members 团队，'
                    '使其具备组织内仓库的访问权限；')
    add_bullet(doc, '步骤6：为学生生成 Gitea personal token，加密存储于绑定表，'
                    '后续 clone 操作通过该 token 完成 HTTPS 认证。')
    add_body_text(doc,
        '整个绑定流程对学生完全透明，学生在首次登录后即可直接使用 Gitea 协作功能，'
        '无需感知底层账号体系的复杂性。绑定关系持久化存储于数据库，'
        '后续登录时自动加载，避免重复创建。')

    # ---- 4.3 团队协作Git工作流 ----
    add_heading_styled(doc, '团队协作Git工作流', level=2)

    # 4.3.1
    add_heading_styled(doc, '团队协作全流程', level=3)
    add_body_text(doc,
        '系统设计了规范的 8 步团队协作 Git 工作流，覆盖从项目创建到代码合并的完整生命周期，'
        '强制学生遵循业界主流的 Git Flow 分支模型，培养良好的工程协作习惯。'
        '该工作流通过 Gitea 平台与系统后端协同实现，每一步都有明确的操作规范与系统支持。')
    _safe_add_image(doc, _img(images_dir, 'team_collab_workflow.png'),
                    '图4-4 团队协作Git工作流全流程图')
    add_bullet(doc, '步骤1：创建项目——教师在系统后端创建教学项目，配置项目名称、描述、成员名单；')
    add_bullet(doc, '步骤2：分配成员——将学生分配到项目团队，建立项目—成员的关联关系；')
    add_bullet(doc, '步骤3：生成仓库——系统调用 Gitea API 在 campus 私有组织下自动创建项目仓库，'
                    '初始化 README 与 .gitignore 文件；')
    add_bullet(doc, '步骤4：clone 仓库——学生通过 HTTPS+Token 模式 clone 仓库到本地，'
                    '系统在前端展示完整的 clone 命令与 git 配置指引；')
    add_bullet(doc, '步骤5：创建分支——学生按 feature/{功能名} 规范创建特性分支，'
                    '禁止直接在 main/master 分支开发；')
    add_bullet(doc, '步骤6：commit 提交——学生按规范编写 commit message（不少于 8 字符），'
                    '说明本次提交的内容与目的；')
    add_bullet(doc, '步骤7：push 推送——学生将本地分支 push 到远程仓库，'
                    '触发 Gitea Webhook 通知系统；')
    add_bullet(doc, '步骤8：open PR & code review & merge——学生在 Gitea 上发起 Pull Request，'
                    '团队成员进行 code review，审核通过后 merge 到 main 分支。')
    add_body_text(doc,
        '系统通过 AI Git 教练在步骤 7（push）与步骤 8（PR）环节自动介入，'
        '对学生的 Git 操作规范性进行实时点评，形成"操作—反馈—改进"的闭环学习机制。')

    # 4.3.2
    add_heading_styled(doc, '仓库管理功能', level=3)
    add_body_text(doc,
        '系统后端封装了完整的 Gitea 仓库管理 API，通过 GiteaService 服务类统一对外提供能力，'
        '主要功能包括：')
    add_bullet(doc, 'get_repository：获取指定仓库的详细信息，包括名称、描述、默认分支、创建时间等；')
    add_bullet(doc, 'create_repository：在 campus 组织下创建新仓库，自动初始化 README 与 .gitignore；')
    add_bullet(doc, 'list_contents：列出仓库指定路径下的文件与目录，支持递归浏览；')
    add_bullet(doc, 'get_file_content：获取仓库中指定文件的内容，支持文本文件与代码文件的在线预览；')
    add_bullet(doc, 'get_languages：获取仓库的编程语言分布统计，用于项目技术栈分析；')
    add_bullet(doc, '其他辅助功能：列出仓库分支、获取提交历史、获取 PR 列表、合并 PR 等。')
    add_body_text(doc,
        '所有仓库管理 API 均通过 Gitea 管理员 token 调用 Gitea REST API 实现，'
        '在前端以统一的接口形式暴露给学生与教师，屏蔽底层 Gitea API 的复杂性。'
        '前端通过这些 API 实现了完整的仓库浏览、文件预览、PR 管理等功能，'
        '学生无需离开系统即可完成大部分 Git 协作操作。')

    # 4.3.3
    add_heading_styled(doc, 'Webhook事件处理', level=3)
    add_body_text(doc,
        'Webhook 是 Gitea 与系统后端协同的核心纽带，当 Gitea 平台发生 push、pull_request 等事件时，'
        '会主动向系统预注册的 Webhook URL 发送 HTTP POST 请求，携带事件详情。'
        '系统后端接收到 Webhook 请求后，经过严格的验签、解析、同步、异步触发等环节，'
        '最终驱动 AI Git 教练对学生操作进行点评。')
    _safe_add_image(doc, _img(images_dir, 'webhook_processing.png'),
                    '图4-5 Webhook事件处理流程图')
    add_body_text(doc,
        'Webhook 事件处理流程的详细步骤如下：'
        '（1）Gitea 在 push、pull_request 事件发生时，将事件 payload 与 HMAC-SHA256 签名'
        '通过 HTTP POST 推送到系统 Webhook 端点；'
        '（2）系统后端接收请求，从 X-Gitea-Signature 头获取签名，使用预配置的 Webhook Secret '
        '对 payload 重新计算 HMAC-SHA256，通过 hmac.compare_digest 进行常量时间比较，'
        '防止时序攻击，验签失败则拒绝请求；'
        '（3）验签通过后解析事件 payload，识别事件类型（push/pull_request）与关键信息'
        '（仓库、提交、作者等）；'
        '（4）调用 apply_gitea_webhook 函数同步项目数据到系统数据库，'
        '确保系统对 Gitea 状态的实时感知；'
        '（5）通过 FastAPI BackgroundTasks 机制异步触发 AI Git 教练点评流程，'
        '立即返回 200 响应给 Gitea，避免 Webhook 超时。')

    # ---- 4.4 AI Git教练核心设计 ----
    add_heading_styled(doc, 'AI Git教练核心设计', level=2)

    # 4.4.1
    add_heading_styled(doc, 'AI Git教练闭环架构', level=3)
    add_body_text(doc,
        'AI Git 教练是系统的核心创新之一，通过 Webhook 驱动 + 异步任务 + LLM 点评的完整闭环，'
        '实现对学生在 Gitea 平台上每一次 Git 操作的自动化、个性化、实时化点评。'
        'AI Git 教练闭环架构的设计目标是：让学生在每一次 push、每一次 PR 都能获得专业、'
        '及时、可操作的反馈，将 Git 协作规范教学从"被动学习"转变为"主动养成"。')
    _safe_add_image(doc, _img(images_dir, 'ai_git_coach_loop.png'),
                    '图4-6 AI Git教练闭环架构图')
    add_body_text(doc,
        'AI Git 教练闭环的完整执行流程如下：')
    add_bullet(doc, '步骤1：Webhook 触发——Gitea 平台学生 push 代码或发起 PR 时，'
                    '通过 Webhook 异步通知系统后端；')
    add_bullet(doc, '步骤2：BackgroundTasks 异步任务——系统通过 FastAPI BackgroundTasks 机制'
                    '启动异步教练任务，立即返回 Webhook 响应，避免阻塞；')
    add_bullet(doc, '步骤3：加载项目数据——异步任务加载项目信息、团队成员、历史反馈等上下文数据；')
    add_bullet(doc, '步骤4：构造 GiteaService——基于项目信息构造 GiteaService 实例，'
                    '封装 Gitea API 调用能力；')
    add_bullet(doc, '步骤5：遍历 commits——遍历本次 push 涉及的所有 commit，提取 commit 信息与作者；')
    add_bullet(doc, '步骤6：匹配作者——通过 match_campus_user_from_gitea_event 函数'
                    '将 Gitea commit 作者匹配到系统校园用户，关联学生身份；')
    add_bullet(doc, '步骤7：规则校验——调用 evaluate_git_workflow 函数对 Git 工作流规范性'
                    '进行纯函数规则校验，识别违规项并计算扣分；')
    add_bullet(doc, '步骤8：获取 diff——获取 commit 的代码变更 diff，截断至 4000 字符'
                    '以控制 LLM token 消耗；')
    add_bullet(doc, '步骤9：构建 prompt——调用 build_coach_prompt 函数'
                    '将 commit 信息、规则违规项、diff 等组装为 LLM 提示词；')
    add_bullet(doc, '步骤10：LLM 调用——以 temperature=0.2 调用 LLM 生成个性化点评，'
                    '低温度保证输出稳定可控；')
    add_bullet(doc, '步骤11：解析 JSON——调用 parse_coach_json 函数解析 LLM 输出，'
                    '提取 summary、mistakes、suggestions 等结构化字段；')
    add_bullet(doc, '步骤12：写回数据库——将教练反馈写入 project.aiGitCoachFeedback 字段，'
                    '保留最近 20 条历史反馈，便于学习追踪；')
    add_bullet(doc, '步骤13：LLM 失败兜底——若 LLM 调用或 JSON 解析失败，'
                    '调用 render_fallback_feedback 函数基于规则 violations 生成兜底反馈，'
                    'status 标记为 fallback，确保任何情况下都有反馈输出。')

    # 4.4.2
    add_heading_styled(doc, 'Git工作流规则校验体系', level=3)
    add_body_text(doc,
        'Git 工作流规则校验体系是 AI Git 教练"规则+AI 双校验"机制的基础环节，'
        '通过纯函数规则对学生的 Git 操作进行客观、确定性的规范性评估，'
        '作为 LLM 个性化点评的输入与兜底依据。系统设计了 8 条 Git 工作流规则，'
        '覆盖分支管理、提交规范、作者绑定、PR 流程等核心场景，'
        '每条规则设定明确的级别（error/warn）与扣分值，最终评分公式为：score = max(0, 100 - 扣分总和)。')
    _safe_add_image(doc, _img(images_dir, 'git_rules_validation.png'),
                    '图4-7 Git工作流规则校验体系图')
    _add_table_caption(doc, '表4-1 Git工作流规则校验体系表')
    add_styled_table(doc,
        headers=['规则码', '规则名称', '级别', '扣分'],
        rows=[
            ['PUSH_TO_DEFAULT_BRANCH', '直接push到main/master', 'error', '-20'],
            ['BRANCH_NAME_INVALID', '分支名不含feature/feat/fix等', 'warn', '-10'],
            ['COMMIT_MESSAGE_TOO_SHORT', 'commit message<8字符', 'warn', '-10'],
            ['COMMIT_MESSAGE_EMPTY', 'commit message为空', 'error', '-20'],
            ['AUTHOR_UNMATCHED', '作者未绑定校园用户', 'warn', '-10'],
            ['PR_BASE_NOT_DEFAULT', 'PR base非默认分支', 'warn', '-10'],
            ['PR_HEAD_NAME_INVALID', 'PR head分支命名不合规', 'warn', '-10'],
            ['MEMBER_NOT_IN_TEAM', '作者不在团队成员列表', 'warn', '-10'],
        ])
    add_body_text(doc,
        '规则校验采用纯函数实现，无副作用、无外部依赖，确保校验结果的确定性与可测试性。'
        '每条规则的判定逻辑均基于 Git 操作的客观属性（分支名、commit message、作者信息等），'
        '不涉及主观判断，保证校验的公平性与一致性。规则违规项以 violations 列表形式输出，'
        '每项包含规则码、规则名称、级别、扣分值与具体描述，作为 LLM 点评的输入与兜底反馈的依据。'
        '评分公式 score = max(0, 100 - 扣分总和) 确保评分下限为 0，避免极端情况下的负分。')

    # 4.4.3
    add_heading_styled(doc, 'AI教练提示词设计思路', level=3)
    add_body_text(doc,
        'AI Git 教练的提示词（prompt）设计是决定点评质量的关键环节，'
        '系统通过精心设计的提示词约束 LLM 的输出风格、内容范围与格式规范，'
        '确保点评既专业又友好，既准确又可操作。提示词设计的核心原则如下：')
    add_bullet(doc, '只评 Git 流程规范，不评业务代码算法——明确界定点评范围，避免 LLM 越界评价代码逻辑，'
                    '保持点评的专业性与聚焦性；')
    add_bullet(doc, '明确指出错误点——对规则校验发现的违规项，必须明确指出具体的错误位置与类型，'
                    '避免泛泛而谈；')
    add_bullet(doc, '给出可执行修改步骤——对每个错误点，必须提供具体的、可操作的修改步骤，'
                    '让学生知道"怎么做"而不仅仅是"做错了"；')
    add_bullet(doc, '语言亲切鼓励为主，面向本科生——点评语气以鼓励引导为主，避免严厉批评，'
                    '照顾本科生的心理接受度，激发学习动力；')
    add_bullet(doc, '要求输出严格 JSON——LLM 必须输出严格符合 {summary, mistakes, suggestions} 结构的 JSON，'
                    '便于前端解析与结构化展示。')

    # 4.4.4
    add_heading_styled(doc, '反馈数据结构', level=3)
    add_body_text(doc,
        'AI Git 教练的反馈采用结构化 JSON 设计，便于前端解析、展示与二次加工。'
        '反馈数据结构包含以下核心字段：')
    add_bullet(doc, 'summary：本次 Git 操作的概述性评价，简明扼要地总结操作的整体质量与主要问题，'
                    '作为反馈的"标题"展示；')
    add_bullet(doc, 'mistakes：错误列表，每个错误项包含错误描述、错误类型、错误位置等详细字段，'
                    '帮助学生精准定位问题；')
    add_bullet(doc, 'suggestions：建议列表，每个建议项包含具体的改进建议与可执行操作步骤，'
                    '指导学生改进；')
    add_bullet(doc, 'status：反馈状态，取值为 ok 或 fallback。ok 表示反馈由 LLM 正常生成，'
                    'fallback 表示 LLM 调用失败、由规则兜底生成。前端可根据 status 调整展示样式，'
                    '提示学生反馈来源。')
    add_body_text(doc,
        '结构化反馈设计的核心价值在于将 LLM 的自然语言输出转化为可计算、可展示、可追溯的数据结构，'
        '为前端丰富的可视化展示（如错误高亮、建议卡片、趋势统计）奠定基础，'
        '同时也便于后续的反馈数据分析与学习进度追踪。')

    # 4.4.5
    add_heading_styled(doc, 'LLM失败兜底机制', level=3)
    add_body_text(doc,
        '考虑到 LLM 服务的不稳定性（网络波动、限流、模型异常等），系统设计了完善的 LLM 失败兜底机制，'
        '确保任何情况下学生都能获得 Git 教练反馈，避免"无反馈"的体验断点。'
        '兜底机制由 render_fallback_feedback 函数实现，其核心逻辑如下：')
    add_body_text(doc,
        '当 LLM 调用失败（网络异常、超时、返回非 JSON 等）或 JSON 解析失败时，'
        '系统自动调用 render_fallback_feedback 函数，基于规则校验阶段产生的 violations 列表'
        '生成兜底反馈。兜底反馈同样遵循 {summary, mistakes, suggestions} 结构，'
        '但内容来源于规则违规项而非 LLM 生成，因此更加确定、客观。'
        '兜底反馈的 status 字段标记为 fallback，前端可据此调整展示样式'
        '（如添加"系统兜底反馈"标识），让学生知晓反馈来源。')
    add_body_text(doc,
        '兜底机制的设计体现了系统"高可用性"的工程理念——即便在最坏的 LLM 不可用情况下，'
        '学生依然能获得基于规则的确定性反馈，保证 Git 教练闭环的连续性与可用性。'
        '这种"规则 + AI"双校验的设计既兼顾了 AI 的个性化优势，'
        '又通过规则兜底保障了系统的可靠性。')

    # ---- 4.5 前端Gitea协作展示 ----
    add_heading_styled(doc, '前端Gitea协作展示', level=2)

    # 4.5.1
    add_heading_styled(doc, 'Clone URL双模式设计', level=3)
    add_body_text(doc,
        '为兼顾安全性与易用性，系统在前端设计了 Clone URL 双模式展示，'
        '根据学生当前的账号绑定状态自动切换，让学生既能方便地 clone 仓库，'
        '又能避免 token 泄露风险。')
    _safe_add_image(doc, _img(images_dir, 'clone_url_dual_mode.png'),
                    '图4-8 Clone URL双模式示意图')
    add_bullet(doc, 'HTTPS 模式：显示 Gitea 原始 clone URL（如 https://gezhisystem.com/gitea/campus/repo.git），'
                    '学生需手动输入 Gitea 账号密码认证。该模式不暴露 token，安全性较高，但操作繁琐；')
    add_bullet(doc, 'HTTPS+Token 模式：生成带凭证的 clone URL'
                    '（如 https://{username}:{token}@gezhisystem.com/gitea/campus/repo.git），'
                    '学生复制后即可直接 clone，无需手动认证。该模式易用性最佳，'
                    '但需在前端明确提示 token 的私密性，避免泄露。')
    add_body_text(doc,
        '系统默认推荐 HTTPS+Token 模式以提升易用性，同时在界面显著位置标注 token 安全提示。'
        '学生可在前端切换两种模式，满足不同场景下的安全与易用性需求。'
        '双模式设计兼顾了新手友好与高级用户的灵活选择，体现了系统对用户体验的细致打磨。')

    # 4.5.2
    add_heading_styled(doc, '仓库首页与项目管理页交互设计', level=3)
    add_body_text(doc,
        '仓库首页与项目管理页是学生接触 Gitea 协作功能的主要入口，系统在前端设计上重点优化了'
        '信息展示的层次与操作的引导性。仓库首页核心展示 HTTPS+Token clone URL，'
        '并配套展示完整的 git 配置命令（git config user.name、git config user.email 等），'
        '让学生一键复制即可完成本地环境配置。')
    add_body_text(doc,
        '项目管理页则以项目为中心，展示项目成员、仓库列表、最近提交、'
        'PR 状态、AI 教练反馈等综合信息。页面采用卡片式布局，将不同类型的信息分区展示，'
        '避免信息过载。AI 教练反馈以独立卡片形式展示，'
        '每条反馈包含 summary 概述、mistakes 错误列表、suggestions 建议列表，'
        '学生可展开查看详情，便于学习与改进。')

    # 4.5.3
    add_heading_styled(doc, '团队协作页面工作流引导', level=3)
    add_body_text(doc,
        '团队协作页面通过 workflowSteps 引导式工作流设计，将复杂的 Git 协作流程'
        '拆解为 6 个清晰的步骤：clone → branch → commit → push → PR → merge，'
        '每一步都配套展示对应的 git 命令与状态标识，让学生按图索骥地完成协作流程。')
    add_body_text(doc,
        'workflowSteps 设计的具体内容包括：'
        '（1）clone 步骤：展示 git clone 命令与 HTTPS+Token URL，标注当前是否已 clone；'
        '（2）branch 步骤：展示 git checkout -b feature/{name} 命令，引导规范分支命名；'
        '（3）commit 步骤：展示 git add 与 git commit 命令，强调 commit message 规范；'
        '（4）push 步骤：展示 git push origin 命令，提示 push 后将触发 AI 教练点评；'
        '（5）PR 步骤：引导学生在 Gitea 发起 Pull Request，展示 PR 创建链接；'
        '（6）merge 步骤：展示 PR 审核与合并流程，提示合并后分支可删除。'
        '每一步的状态实时更新，让学生清晰感知协作进度。')

    # ---- 4.6 创新实践与用户体验提升 ----
    add_heading_styled(doc, '创新实践与用户体验提升', level=2)
    add_body_text(doc,
        '本章 Gitea 集成与 AI Git 教练的设计在多个维度体现了系统的创新性，'
        '这些创新点共同构成了系统在工程协作实训领域的差异化竞争力。')
    add_bullet(doc, '创新点1：异步教练——通过 FastAPI BackgroundTasks 机制异步执行 AI 教练任务，'
                    '不阻塞 Webhook 响应，确保 Gitea 平台不会因教练任务耗时过长而判定 Webhook 失败；')
    add_bullet(doc, '创新点2：规则+AI 双校验——先通过纯函数规则校验进行确定性评分，'
                    '再将规则违规项作为输入传递给 LLM 进行个性化点评，兼顾准确性与个性化；')
    add_bullet(doc, '创新点3：JSON 结构化反馈——LLM 输出严格遵循 {summary, mistakes, suggestions} 结构，'
                    '便于前端解析展示与数据分析，避免自然语言反馈的解析难题；')
    add_bullet(doc, '创新点4：LLM 失败自动 fallback——当 LLM 调用失败时自动切换至规则兜底反馈，'
                    'status 标记为 fallback，保证系统在任何情况下都有反馈输出，确保可用性；')
    add_bullet(doc, '创新点5：保留 20 条历史反馈——每次教练反馈写入 project.aiGitCoachFeedback 字段，'
                    '保留最近 20 条历史记录，便于学生回顾改进历程与教师追踪学习进度。')

    # ============================================================
    # 第五章 RAGFlow知识库系统
    # ============================================================
    add_heading_styled(doc, 'RAGFlow知识库系统', level=1)

    # ---- 5.1 知识库架构 ----
    add_heading_styled(doc, '知识库架构', level=2)
    add_body_text(doc,
        '系统基于 RAGFlow v0.25.6 构建双层知识库架构，包含公共课程数据集与学生私有数据集两类，'
        '分别承载不同来源与权限的知识资源。RAGFlow 是一款开源的 RAG（Retrieval-Augmented Generation）引擎，'
        '内置 DeepDOC 文档解析、向量检索、混合检索等核心能力，相比 LangChain 等框架的 RAG 实现，'
        'RAGFlow 在文档解析精度与检索质量上具有显著优势。')
    _safe_add_image(doc, _img(images_dir, 'ragflow_arch.png'),
                    '图5-1 RAGFlow知识库架构图')
    add_body_text(doc,
        '公共课程数据集面向全体学生开放，包含人工智能、计算机程序设计、数据结构等核心课程的'
        '课件、教材、讲义等教学资料，由教师统一上传维护，是系统知识检索的"公共知识池"。'
        '学生私有数据集命名为 user_private_{user_id}，每位学生拥有独立的私有知识库，'
        '可上传个人学习笔记、参考资料等私有资料，通过 repository_id metadata 过滤实现权限隔离，'
        '确保学生私有资料仅本人可检索。')
    add_body_text(doc,
        '双层知识库架构的设计兼顾了知识共享与隐私保护：'
        '公共数据集让所有学生共享高质量的教学资源，避免重复建设；'
        '私有数据集让学生能够构建个人化的知识库，满足个性化学习需求。'
        '检索时系统先检索公共数据集获取通用知识，再检索私有数据集获取个人资料，'
        '将两者结果融合后送入 LLM 生成回答，实现"通用知识 + 个性化资料"的双重增强。')

    # ---- 5.2 文档处理流程 ----
    add_heading_styled(doc, '文档处理流程', level=2)
    add_body_text(doc,
        'RAGFlow 知识库的文档处理流程严格规范，确保文档解析质量与检索效果。'
        '系统目前仅支持 PDF 格式文档上传，后续可扩展支持更多格式。'
        '文档处理流程包含上传、解析配置、启动解析、状态同步等关键环节。')
    _safe_add_image(doc, _img(images_dir, 'doc_processing_flow.png'),
                    '图5-2 文档处理流程图')
    add_body_text(doc,
        '文档处理流程的具体步骤如下：'
        '（1）格式校验：通过 classify_supported_file 函数校验上传文件格式，'
        '当前仅支持 PDF，不符合格式的文件直接拒绝；'
        '（2）文档上传：将文档上传至 RAGFlow 指定数据集，存储于 MinIO 对象存储；'
        '（3）配置 parser：为文档配置解析器参数，采用 presentation chunk method（演示文稿分块方法）'
        '配合 DeepDOC layout recognize（布局识别）技术，DeepDOC 能够识别文档的标题、段落、'
        '表格、图片等结构化元素，提升解析质量；'
        '（4）启动解析：调用 RAGFlow API 启动文档解析，DeepDOC 将文档解析为带结构的文本块；'
        '（5）状态同步：通过轮询机制同步文档解析状态，'
        '状态码含义为：0=queued（排队中）、1=parsing（解析中）、2=cancelled（已取消）、'
        '3=parsed（解析成功）、4=failed（解析失败），前端根据状态展示进度。')

    # ---- 5.3 RAG检索增强生成流程 ----
    add_heading_styled(doc, 'RAG检索增强生成流程', level=2)
    add_body_text(doc,
        'RAG 检索增强生成流程是系统知识问答能力的核心，通过"检索—增强—生成"三步法，'
        '将 LLM 的生成能力与知识库的检索能力相结合，生成既准确又具引用来源的回答。'
        '系统针对教育场景对 RAG 流程进行了深度优化，包括寒暄检测、双数据集检索、引用来源附加等。')
    _safe_add_image(doc, _img(images_dir, 'rag_retrieval_flow.png'),
                    '图5-3 RAG检索增强生成流程图')
    add_body_text(doc,
        'RAG 检索增强生成流程的详细步骤如下：')
    add_bullet(doc, '寒暄检测：通过 is_greeting 函数判断用户输入是否为寒暄语（如"你好"、"谢谢"等），'
                    '若是则跳过检索直接生成友好回复，避免无意义的向量检索开销；')
    add_bullet(doc, '检索公共数据集：在公共课程数据集中进行向量检索，配置 similarity_threshold=0.2'
                    '（相似度阈值，过滤低相关性结果）、vector_weight=0.3（向量权重）、keyword=True'
                    '（启用关键词检索，实现向量与关键词的混合检索）；')
    add_bullet(doc, '检索私有数据集：在学生私有数据集中检索，通过 metadata_condition 按 repository_id 过滤，'
                    '确保仅检索当前学生的私有资料，实现权限隔离；')
    add_bullet(doc, '拼装上下文：将公共与私有数据集的检索结果按相关性排序，拼装为 LLM 上下文；')
    add_bullet(doc, 'LLM 生成：调用 LLM 基于检索上下文生成回答，回答内容严格基于检索结果，避免幻觉；')
    add_bullet(doc, '附加引用来源：从检索结果的 reference.chunks 中提取 document_name（文档名），'
                    '作为引用来源附加到回答末尾，让学生知晓知识来源，便于查证与深入学习。')

    # ---- 5.4 LangChain Tool封装 ----
    add_heading_styled(doc, 'LangChain Tool封装', level=2)
    add_body_text(doc,
        '系统将 RAGFlow 的检索能力封装为 LangChain Tool——query_data_structure_knowledge 工具，'
        '供 DataBot 智能体在 LangGraph 工作流中按需调用。该工具封装的设计使得 LLM 能够'
        '在推理过程中主动决定何时检索知识库，实现"按需检索"的智能 RAG 模式，'
        '相比传统的"必检索"模式更加高效。')
    add_body_text(doc,
        'query_data_structure_knowledge 工具的内部实现流程为：'
        '（1）通过 RAGFLOW_CHAT_ID 创建会话 session，建立检索上下文；'
        '（2）调用 RAGFlow completion 接口发起检索增强生成请求，'
        '传入用户问题与 session 信息；'
        '（3）从响应中提取 answer（回答内容）与 reference.chunks（引用片段），'
        '从 chunks 中提取 document_name（文档名）作为引用来源；'
        '（4）将回答与引用来源组装为工具返回值，供 LLM 在后续推理中使用。'
        '整个封装过程对 LLM 透明，LLM 仅需调用工具即可获得检索增强后的回答。')

    # ---- 5.5 多模式检索策略 ----
    add_heading_styled(doc, '多模式检索策略', level=2)
    add_body_text(doc,
        '系统针对不同使用场景设计了三种 RAG 检索模式，灵活适配多样化的知识检索需求：')
    add_bullet(doc, 'Agent Canvas 智能体模式：通过智能体编排工坊配置专属 RAG 智能体，'
                    '支持复杂的检索-推理循环，适用于深度学习与探索性提问场景；')
    add_bullet(doc, 'Chat Assistant 对话模式：通过 RAGFlow 内置的对话助手进行检索增强对话，'
                    '适用于常规知识问答场景，响应速度快、配置简单；')
    add_bullet(doc, 'Dataset 直检索模式：直接调用 RAGFlow 数据集检索接口，绕过 LLM 生成环节，'
                    '仅返回原始检索结果，适用于需要原始文档片段的场景（如资料查阅、引用整理）。')
    add_body_text(doc,
        '三种模式分别对应不同的检索深度与响应速度，用户可根据具体需求灵活选择。'
        '系统通过统一的 RAGFlow API 抽象屏蔽底层差异，前端通过统一的接口暴露三种模式，'
        '实现"一套 API、三种模式"的灵活架构。')

    # ---- 5.6 知识库数据统计 ----
    add_heading_styled(doc, '知识库数据统计', level=2)
    add_body_text(doc,
        '系统对知识库的数据分布进行统计分析，帮助教师与管理员掌握知识库的建设情况与使用情况，'
        '为知识库的持续优化提供数据支撑。统计维度包括数据集数量、文档数量、文档类型分布、'
        '解析状态分布、检索频次、热门文档等。')
    _safe_add_image(doc, _img(images_dir, 'knowledge_dist.png'),
                    '图5-4 知识库数据分布图')

    # ============================================================
    # 第六章 前端系统设计
    # ============================================================
    add_heading_styled(doc, '前端系统设计', level=1)

    # ---- 6.1 前端架构 ----
    add_heading_styled(doc, '前端架构', level=2)
    add_body_text(doc,
        '系统前端采用 Vue 3 ESM（ECMAScript Module）架构，通过 importmap 直接在浏览器中加载 Vue 与依赖库，'
        '无需 Webpack、Vite 等构建工具，实现"零构建"部署。该架构的优势在于开发部署简单、'
        '迭代速度快、调试便捷，适合中小型项目的快速演进。配合 Tailwind CSS 原子化样式框架，'
        '实现高效、一致的 UI 开发。')
    _safe_add_image(doc, _img(images_dir, 'frontend_arch.png'),
                    '图6-1 前端架构图')
    add_body_text(doc,
        '前端集成了丰富的可视化与交互库，构建沉浸式学习体验：')
    add_bullet(doc, 'ECharts：数据可视化图表库，用于学情雷达图、趋势折线图、分布柱状图等数据展示；')
    add_bullet(doc, 'Three.js：3D 图形库，用于知识图谱的 3D 力导向图渲染，提升知识结构的可视化效果；')
    add_bullet(doc, 'Monaco Editor：VS Code 同款代码编辑器，用于编程实战的在线代码编辑，提供语法高亮、'
                    '智能提示等专业编码体验；')
    add_bullet(doc, 'Mermaid.js：图表绘制库，用于渲染 AI 智能体生成的流程图、思维导图等结构化图表；')
    add_bullet(doc, 'GSAP：专业动画库，用于页面过渡动画、元素动效，提升交互的流畅感与品质感；')
    add_bullet(doc, 'p5.js：创意编程库，用于算法艺术、生成式艺术的演示与教学；')
    add_bullet(doc, 'marked.js + DOMPurify：Markdown 渲染 + XSS 防护组合，'
                    'marked.js 将 AI 回复的 Markdown 渲染为 HTML，DOMPurify 清洗 HTML 防止 XSS 攻击，'
                    '确保安全地展示富文本内容。')

    # ---- 6.2 学生端功能架构 ----
    add_heading_styled(doc, '学生端功能架构', level=2)
    add_body_text(doc,
        '学生端共设计 11 个核心视图，覆盖学习、练习、协作、查询等全场景需求，'
        '每个视图都针对特定的学习场景精心设计，形成完整的"学—练—评—协"学习闭环。')
    _add_table_caption(doc, '表6-1 学生端视图清单')
    add_styled_table(doc,
        headers=['视图', '名称', '核心功能'],
        rows=[
            ['dashboard', '仪表盘', 'Bento网格布局，学习数据总览'],
            ['pathway', '知识图谱', '3D力导向图+树图'],
            ['workspace', '工作台', '双模式AI对话(引导式/RAG)'],
            ['knowledge', '知识库', '个人私有RAG资料库'],
            ['mistakes', '错题本', '错题与AI错因分析'],
            ['exam', '考试', '考试中心'],
            ['homework', '作业', '作业提交与智能诊断'],
            ['courses', '课程库', '公共课程课件浏览'],
            ['agents', '智能体', 'Agent编排工坊'],
            ['coding', '编程实战', '在线编程沙箱(Monaco)'],
            ['academic-space', '学术空间', '代码仓库+PR+论坛'],
        ])

    # ---- 6.3 教师端功能架构 ----
    add_heading_styled(doc, '教师端功能架构', level=2)
    add_body_text(doc,
        '教师端共设计 8 个核心视图，聚焦教学管理、学情监控、作业评阅等教师专属场景，'
        '通过 AI 增强的方式减轻教师重复性工作，让教师专注于教学本身的创造性环节。')
    _add_table_caption(doc, '表6-2 教师端视图清单')
    add_styled_table(doc,
        headers=['视图', '名称', '核心功能'],
        rows=[
            ['t_dashboard', '教师工作台', '考勤+AI预警+论坛求助+待批改'],
            ['t_monitor', '全息监控', '多智能体集群实时学生状态'],
            ['t_analytics', '学情决策台', '班级学情分析与一键干预'],
            ['t_exams', '考试管理', '创建考试+编程题下达'],
            ['t_homework', '作业管理', '作业提交管理与协同评阅'],
            ['t_projects', '项目管理', '大作业递交与编程团队实训'],
            ['t_space', '空间管理', '论坛管理+仓库举报审核'],
            ['t_courses', '课程库管理', '课件资源上传/删除/重命名'],
        ])

    # ---- 6.4 AI对话流式交互三级降级策略 ----
    add_heading_styled(doc, 'AI对话流式交互三级降级策略', level=2)
    add_body_text(doc,
        '为保证 AI 对话的流畅体验与高可用性，系统设计了三级降级策略，'
        '当首选的 SSE 流式响应失败时，自动降级到非流式响应，再降级到本地模拟，'
        '确保任何网络环境下用户都能获得对话反馈，避免"无响应"的体验断点。')
    _safe_add_image(doc, _img(images_dir, 'fallback_strategy.png'),
                    '图6-2 AI对话三级降级策略图')
    add_bullet(doc, '首选 SSE 流式：通过 POST /chat/stream 发起 SSE 流式请求，'
                    '使用 response.body.getReader() 读取流式响应，实现 token 级的打字机效果，'
                    '提供最佳的实时交互体验；')
    add_bullet(doc, '降级非流式：当 SSE 流式请求失败（网络异常、服务端不支持等）时，'
                    '自动降级为 POST /chat 非流式请求，等待完整响应后一次性展示，'
                    '虽牺牲了实时性但保证了内容完整性；')
    add_bullet(doc, '本地模拟兜底：当非流式请求也失败时，使用 setInterval 实现本地打字机模拟，'
                    '展示预设的友好提示内容，确保用户始终能感知到系统的响应，'
                    '避免长时间无反馈的"假死"状态。')

    # ---- 6.5 仪表盘Bento网格布局 ----
    add_heading_styled(doc, '仪表盘Bento网格布局', level=2)
    add_body_text(doc,
        '学生仪表盘采用 Bento 网格布局设计，灵感来源于日式便当盒的分格设计，'
        '将不同类型的信息卡片按重要性、时效性、关联性进行网格化排布，'
        '形成既美观又高效的信息展示界面。Bento 布局的核心优势在于信息密度高、视觉层次清晰、'
        '响应式适配友好，非常适合学习数据总览这类信息密集型场景。')
    _safe_add_image(doc, _img(images_dir, 'dashboard_layout.png'),
                    '图6-3 仪表盘Bento网格布局图')
    add_body_text(doc,
        'Bento 网格布局的核心区域包括：')
    add_bullet(doc, 'HERO 区：展示动态问候语（根据时间显示"早安/午安/晚安"）、'
                    '待提交作业数、待参加考试数等关键摘要信息，作为仪表盘的视觉焦点；')
    add_bullet(doc, 'A 今日待提交作业：列出今天截止的作业，按紧急程度排序，'
                    '支持一键跳转提交；')
    add_bullet(doc, 'B 各科目截止时间：以时间轴形式展示各科目作业与考试截止时间，'
                    '帮助学生规划学习节奏；')
    add_bullet(doc, 'C 考试通知：展示近期考试安排，包括考试时间、时长、范围等；')
    add_bullet(doc, 'D 易错点追踪：基于错题本数据统计学生的易错知识点，'
                    '提示重点复习方向；')
    add_bullet(doc, 'E 错题本复盘：展示近期错题，引导学生定期复盘巩固。')

    # ---- 6.6 教师全息监控面板 ----
    add_heading_styled(doc, '教师全息监控面板设计', level=2)
    add_body_text(doc,
        '教师全息监控面板是教师端最具创新性的功能之一，通过学生卡片网格的形式'
        '实时展示全班学生的学习状态，让教师能够"一屏掌握全班"，及时发现学习困难学生并介入。'
        '面板的核心展示元素包括：')
    add_bullet(doc, '头像与姓名：基础身份信息展示；')
    add_bullet(doc, '状态呼吸灯：通过呼吸灯效果实时反映学生当前的学习状态'
                    '（在线学习、AI 交互中、提交作业、空闲等），状态变化即时反馈；')
    add_bullet(doc, '进度条：展示学生当前学习进度与作业完成情况；')
    add_bullet(doc, 'AI 介入智能体：展示当前正在与学生交互的 AI 智能体名称'
                    '（如 Alina、Prof.X 等），让教师知晓 AI 教学介入情况；')
    add_bullet(doc, '专注度：基于学生近期学习行为（交互频次、停留时长等）计算专注度评分；')
    add_bullet(doc, '预警遮罩：当学生出现异常状态（长时间未学习、错题率骤增、AI 多次介入失败等）时，'
                    '卡片覆盖预警遮罩，提醒教师重点关注。')

    # ---- 6.7 用户体验提升策略 ----
    add_heading_styled(doc, '用户体验提升策略', level=2)
    add_body_text(doc,
        '系统在前端体验上采用了多项策略提升用户体验，打造沉浸式、可视化、可追踪的学习过程：')
    add_bullet(doc, '实时事件总线：通过 homework-submitted（作业提交）、interaction-completed（交互完成）、'
                    'mistake-mastered-changed（错题掌握变更）等事件实现前端组件间的解耦协同，'
                    '一个组件的状态变化可实时触发其他组件更新，无需手动刷新；')
    add_bullet(doc, '动画交互 GSAP：使用 GSAP 实现页面过渡、元素入场、状态变化等动画效果，'
                    '提升交互的流畅感与品质感；')
    add_bullet(doc, '可视化引导 Mira 智能体 mermaid 渲染：Mira 智能体生成的 Mermaid 图表'
                    '通过 mermaid.js 实时渲染为流程图、思维导图等可视化素材，'
                    '帮助学生直观理解复杂概念。')

    # ============================================================
    # 第七章 微信小程序设计
    # ============================================================
    add_heading_styled(doc, '微信小程序设计', level=1)

    # ---- 7.1 小程序架构 ----
    add_heading_styled(doc, '小程序架构', level=2)
    add_body_text(doc,
        '系统微信小程序端共设计 17 个页面，覆盖学生移动学习的主要场景，'
        '采用微信原生小程序框架开发，配合自定义 TabBar 与自定义导航栏，'
        '打造与 PC 端一致品牌风格的移动学习体验。'
        '小程序基于微信云开发（cloud1-d8geq5jvy1cb9ba63）能力，'
        '通过云函数代理方式与后端 API 通信。')
    _safe_add_image(doc, _img(images_dir, 'miniprogram_arch.png'),
                    '图7-1 微信小程序架构图')
    add_body_text(doc,
        '小程序自定义 TabBar 包含四个主要入口：首页（学习数据总览）、学术空间（代码仓库与论坛）、'
        'AI 导师（智能体对话）、我的（个人中心）。自定义 TabBar 相比原生 TabBar 的优势在于'
        '样式可定制性更强，能够实现更丰富的视觉效果与交互反馈。'
        '自定义导航栏则适配不同机型的状态栏高度，确保页面布局在各种设备上的一致性。')

    # ---- 7.2 云函数代理架构 ----
    add_heading_styled(doc, '云函数代理架构', level=2)
    add_body_text(doc,
        '微信小程序受限于合法域名配置与单次请求超时限制，无法直接调用后端 API。'
        '系统通过云函数 apiProxy 作为代理层，解决小程序的网络访问限制问题。'
        '云函数代理架构是小程序端与后端通信的核心纽带，其设计直接影响小程序的可用性与性能。')
    _safe_add_image(doc, _img(images_dir, 'cloud_function_proxy.png'),
                    '图7-2 云函数代理架构图')
    add_body_text(doc,
        '云函数代理的工作流程为：'
        '（1）小程序通过 wx.cloud.callFunction 调用 apiProxy 云函数，传入 action（路由标识）'
        '与 data（请求数据）；'
        '（2）apiProxy 云函数基于 wx-server-sdk 与 got HTTP 客户端，'
        '根据 action 在路由表中查找对应的后端 API 路径与 HTTP 方法；'
        '（3）设置 45 秒超时（云函数最大超时），向后端 API 发起 HTTP 请求；'
        '（4）将后端响应原样返回给小程序。'
        '路由表配置了 30+ 个 action 映射，覆盖小程序所有功能模块的后端 API 调用需求。')

    # ---- 7.3 多端数据同步设计 ----
    add_heading_styled(doc, '多端数据同步设计', level=2)
    add_body_text(doc,
        '系统支持 PC 端与小程序端的多端学习，多端数据同步设计确保学生在不同端的学习数据'
        '实时一致，避免因端切换导致的数据割裂。多端同步通过统一的后端 API 与数据库实现，'
        '所有端共享同一份数据，任何一端的操作都会即时反映到其他端。')
    _safe_add_image(doc, _img(images_dir, 'multi_end_sync.png'),
                    '图7-3 多端数据同步图')
    add_body_text(doc,
        '多端数据同步的核心机制包括：'
        '（1）统一身份认证：PC 端与小程序端共享同一套 JWT 身份认证体系，'
        '学生在任一端登录后身份信息跨端有效；'
        '（2）统一数据存储：所有端的数据存储于同一数据库，通过 user_id 关联，避免数据冗余；'
        '（3）实时事件通知：通过事件总线机制，当一端发生关键事件（如作业提交、错题掌握）时，'
        '其他端在下次请求时能够感知并同步更新；'
        '（4）冲突处理：采用"最后写入优先"策略处理多端并发写入冲突，'
        '关键字段（如作业提交）通过时间戳判断有效性。')

    # ---- 7.4 小程序与PC端功能对照表 ----
    add_heading_styled(doc, '小程序与PC端功能对照表', level=2)
    add_body_text(doc,
        '受限于小程序的能力限制与移动端使用场景，小程序端在功能上与 PC 端存在一定差异。'
        '系统根据移动端特性对功能进行了取舍，保留核心学习功能，舍弃不适合移动端的复杂功能，'
        '确保小程序端的学习体验流畅高效。')
    _add_table_caption(doc, '表7-1 小程序与PC端功能对照表')
    add_styled_table(doc,
        headers=['功能模块', 'PC端', '小程序端'],
        rows=[
            ['AI对话', 'SSE流式+三级降级', '非流式(云函数不支持SSE)'],
            ['知识库', '上传PDF+检索', '上传pdf/doc/docx/txt'],
            ['错题本', '完整管理+AI分析', '列表+AI分析'],
            ['作业', '提交+诊断+报告', '列表+详情+提交'],
            ['学情画像', '六维雷达+趋势', '六维雷达+趋势'],
            ['代码仓库', '完整浏览+Clone', '不支持'],
        ])

    # ---- 7.5 移动端适配策略 ----
    add_heading_styled(doc, '移动端适配策略', level=2)
    add_body_text(doc,
        '小程序端针对移动设备特性进行了多项适配优化，确保在各种机型上都能提供流畅的学习体验：')
    add_bullet(doc, '自定义导航栏：根据不同机型的状态栏高度动态计算导航栏位置，'
                    '避免刘海屏、水滴屏等异形屏的适配问题；')
    add_bullet(doc, '自适应布局：使用 rpx（responsive pixel）单位与 flex 布局，'
                    '确保页面元素在不同屏幕尺寸下都能合理排布；')
    add_bullet(doc, '触控优化：增大可点击区域（最小 44pt）、优化触摸反馈（hover 态、点击态），'
                    '提升移动端的操作准确性与手感；')
    add_bullet(doc, '性能优化：采用分页加载、懒加载、图片压缩等手段，'
                    '降低小程序的内存占用与启动时间，保证在低端机型上的流畅运行。')

    # ============================================================
    # 第八章 系统部署与安全设计
    # ============================================================
    add_heading_styled(doc, '系统部署与安全设计', level=1)

    # ---- 8.1 部署架构 ----
    add_heading_styled(doc, '部署架构', level=2)
    add_body_text(doc,
        '系统采用单服务器集中部署模式，部署于公网服务器（IP: 154.201.71.151），'
        '通过 Nginx 统一接入所有外部流量。部署架构的核心组件包括 Nginx 反向代理、'
        'FastAPI 后端服务、MySQL 数据库、Docker 容器（Gitea 与 RAGFlow）等，'
        '各组件协同工作，共同支撑系统的稳定运行。')
    _safe_add_image(doc, _img(images_dir, 'nginx_proxy_flow.png'),
                    '图8-1 Nginx反向代理流程图')
    add_body_text(doc,
        '服务器组件部署详情：'
        'Nginx 监听 80（HTTP 重定向）与 443（HTTPS）端口，配置 Let\'s Encrypt SSL 证书'
        '实现 HTTPS 加密通信；FastAPI 后端以 systemd 服务方式运行，监听 8516 端口，'
        '配置 4 个 Uvicorn worker 进程以充分利用多核 CPU；'
        'MySQL 数据库监听 3306 端口，为业务系统与 Gitea 共享同一实例；'
        'Docker 容器运行 Gitea（端口 3000）与 RAGFlow（端口 9380）及其依赖服务'
        '（MySQL、MinIO、Elasticsearch、Redis）。')

    # ---- 8.2 Docker容器编排 ----
    add_heading_styled(doc, 'Docker容器编排', level=2)
    add_body_text(doc,
        '系统通过 Docker Compose 编排 Gitea 与 RAGFlow 两大核心服务及其依赖组件，'
        '实现一键部署、统一管理与版本可控。Docker Compose 编排的优势在于'
        '环境一致性、部署便捷性、版本可追溯性，极大简化了运维工作。')
    _safe_add_image(doc, _img(images_dir, 'docker_compose.png'),
                    '图8-2 Docker容器编排图')
    add_body_text(doc,
        'Docker Compose 编排的核心服务包括：')
    add_bullet(doc, 'Gitea：使用 gitea/gitea:1.26.4 镜像，暴露 3000（HTTP）与 2222（SSH）端口，'
                    '数据卷持久化存储仓库数据与配置，复用宿主机 MySQL 作为数据库；')
    add_bullet(doc, 'RAGFlow：使用 infiniflow/ragflow:v0.25.6 镜像，依赖独立的 MySQL（存储元数据）、'
                    'MinIO（对象存储，存储文档与向量索引）、Elasticsearch（全文检索）、'
                    'Redis（缓存）四大组件，所有依赖通过 Docker Compose 一并编排。')

    # ---- 8.3 Nginx反向代理设计 ----
    add_heading_styled(doc, 'Nginx反向代理设计', level=2)
    add_body_text(doc,
        'Nginx 作为系统的统一入口，承担 HTTPS 终结、静态资源服务、多路径反向代理等核心职责。'
        '通过精心设计的 location 路由规则，Nginx 将不同路径的请求精准分发到对应的后端服务，'
        '实现单一域名下的多服务统一访问。')
    add_bullet(doc, '/api/ → FastAPI:8516：所有业务 API 请求代理到 FastAPI 后端；')
    add_bullet(doc, '/static/ → FastAPI:8516/static：静态资源请求代理到 FastAPI 静态文件服务；')
    add_bullet(doc, '/gitea/ → Gitea:3000：Gitea 平台请求代理到 Gitea 容器，'
                    '通过 proxy_set_header 传递真实客户端 IP 与 Host 信息；')
    add_bullet(doc, '/ → 前端静态文件：根路径请求由 Nginx 直接返回前端静态文件，'
                    '配合 try_files 实现 SPA 路由的 history 模式。')

    # ---- 8.4 安全设计体系 ----
    add_heading_styled(doc, '安全设计体系', level=2)

    # 8.4.1
    add_heading_styled(doc, 'JWT认证', level=3)
    add_body_text(doc,
        '系统采用自实现的 JWT（JSON Web Token）认证机制，'
        '不依赖第三方认证库，从底层掌握认证流程的每一个细节，便于定制化与安全审计。'
        'JWT 认证机制的设计严格遵循安全最佳实践，确保用户身份认证的可靠性与抗攻击性。')
    _safe_add_image(doc, _img(images_dir, 'jwt_auth_flow.png'),
                    '图8-3 JWT认证流程图')
    add_body_text(doc,
        'JWT 认证机制的核心设计包括：')
    add_bullet(doc, '密码哈希：采用 pbkdf2_sha256 算法进行密码哈希存储，配置 120000 次迭代'
                    '与 16 字节随机 salt，有效抵抗彩虹表与暴力破解攻击；')
    add_bullet(doc, 'Token 格式：采用 base64url(payload).base64url(HMAC-SHA256签名) 格式，'
                    'payload 包含 user_id、username、exp（过期时间）等声明，'
                    'HMAC-SHA256 签名确保 Token 不可篡改；')
    add_bullet(doc, 'Token 有效期：设置为 7 天，平衡安全性与用户体验，'
                    '过期后需重新登录获取新 Token；')
    add_bullet(doc, '防时序攻击：使用 hmac.compare_digest 进行签名比较，'
                    '该函数执行常量时间比较，防止攻击者通过响应时间差异推断签名信息。')

    # 8.4.2
    add_heading_styled(doc, 'Gitea Webhook HMAC验签', level=3)
    add_body_text(doc,
        'Gitea Webhook 的安全性至关重要，若 Webhook 端点被恶意构造请求攻击，'
        '可能导致虚假 Git 事件触发 AI 教练点评，污染反馈数据。'
        '系统通过 HMAC-SHA256 验签机制确保 Webhook 请求确实来自 Gitea 平台，'
        '有效防止伪造请求攻击。')
    _safe_add_image(doc, _img(images_dir, 'webhook_verify_flow.png'),
                    '图8-4 Webhook HMAC验签流程图')
    add_body_text(doc,
        'HMAC 验签流程为：'
        '（1）Gitea 在发送 Webhook 时，使用预配置的 Webhook Secret 对 payload 计算 HMAC-SHA256 签名，'
        '将签名放入 X-Gitea-Signature 请求头；'
        '（2）系统后端接收请求后，从 X-Gitea-Signature 头获取签名；'
        '（3）使用相同的 Webhook Secret 对接收到的 payload 重新计算 HMAC-SHA256；'
        '（4）通过 hmac.compare_digest 比较计算结果与请求头签名，'
        '若一致则验签通过，否则拒绝请求。'
        'Webhook Secret 仅在 Gitea 与系统后端共享，第三方无法伪造有效签名。')

    # 8.4.3
    add_heading_styled(doc, 'campus私有组织访问控制', level=3)
    add_body_text(doc,
        '系统在 Gitea 中创建 campus 私有组织作为所有教学项目的容器，'
        '通过组织私有属性实现仓库访问控制。campus 组织设置为私有后，'
        '所有归属于该组织的仓库继承私有属性，仅组织成员可访问，'
        '非组织成员无法通过任何方式 clone 仓库内容。')
    add_body_text(doc,
        '访问控制的具体机制为：'
        '（1）学生首次登录系统时自动创建 Gitea 账号并加入 campus 组织的 Members 团队，'
        '获得组织内仓库的读取权限；'
        '（2）非 campus 组织成员无法浏览组织仓库列表，也无法 clone 仓库；'
        '（3）学生通过 HTTPS+Token 模式 clone 仓库时，Gitea 校验 token 对应用户是否为组织成员，'
        '校验通过才允许 clone；'
        '（4）毕业或退课时，管理员可将学生移出 campus 组织，即时撤销访问权限。'
        '该机制有效防止了代码外泄与跨班级抄袭。')

    # 8.4.4
    add_heading_styled(doc, '代码沙箱安全隔离设计', level=3)
    add_body_text(doc,
        '系统的在线编程沙箱（execute_python_code 工具）允许学生执行 Python 代码，'
        '存在潜在的安全风险（如恶意代码执行系统命令、删除文件等）。'
        '系统通过 subprocess 隔离 + 安全关键字拦截 + 超时限制三重机制，'
        '确保代码沙箱的安全性，防止恶意代码对系统造成破坏。')
    add_bullet(doc, 'subprocess 隔离：使用 subprocess 创建独立子进程执行学生代码，'
                    '子进程与主进程隔离，即便代码崩溃也不会影响主服务；')
    add_bullet(doc, '安全关键字拦截：在执行前扫描代码，拦截 os.system、subprocess、'
                    'rmtree 等危险关键字，发现即拒绝执行，防止恶意代码危害系统；')
    add_bullet(doc, '超时限制：设置 5 秒执行超时，防止死循环或长时间运行的代码'
                    '占用过多资源，超时后强制终止子进程。')

    # ---- 8.5 数据库连接池设计 ----
    add_heading_styled(doc, '数据库连接池设计', level=2)
    add_body_text(doc,
        '系统通过 SQLAlchemy ORM 与 MySQL 数据库交互，配置了完善的数据库连接池参数，'
        '确保在高并发场景下的数据库连接稳定性与性能。'
        '连接池设计的核心目标是平衡连接复用效率与资源占用，避免连接耗尽或频繁创建销毁的开销。')
    add_bullet(doc, 'pool_size=20：连接池常驻连接数，满足常规并发需求；')
    add_bullet(doc, 'max_overflow=30：连接池允许的溢出连接数，应对突发流量，'
                    '总连接数最大为 pool_size + max_overflow = 50；')
    add_bullet(doc, 'pool_pre_ping：连接复用前先发送 ping 检测连接有效性，'
                    '避免使用已断开的连接导致错误；')
    add_bullet(doc, 'pool_recycle=1800：连接回收周期 1800 秒（30 分钟），'
                    '定期回收连接避免长连接导致的资源泄漏与数据库超时问题；')
    add_bullet(doc, 'pool_timeout=10：获取连接超时时间 10 秒，'
                    '连接池耗尽时等待最多 10 秒，超时抛出异常避免无限等待。')

    # ============================================================
    # 第九章 创新实践与总结
    # ============================================================
    add_heading_styled(doc, '创新实践与总结', level=1)

    # ---- 9.1 前沿AI技术融合应用总结 ----
    add_heading_styled(doc, '前沿AI技术融合应用总结', level=2)
    add_body_text(doc,
        '格至智能协同教育系统深度融合了大语言模型时代的多项前沿 AI 技术，'
        '通过有机组合与创新应用，构建了独具特色的智能教育协同平台。'
        '系统在 AI 技术融合方面的核心实践包括以下四个方面：')
    add_body_text(doc,
        'LangGraph 多 Agent 协同：系统基于 LangGraph StateGraph 构建了 10 个专业智能体的协同工作流，'
        '通过 agent 节点、tools 节点、tools_condition 条件路由、MemorySaver 状态记忆等核心组件，'
        '实现了 ReAct 推理执行循环与多智能体协同教学。LangGraph 的细粒度状态管理能力'
        '让复杂的协同逻辑变得清晰可控。')
    add_body_text(doc,
        'RAG 增强生成：系统基于 RAGFlow 构建了公共课程 + 学生私有的双层知识库，'
        '通过 DeepDOC 文档解析、向量检索、混合检索等技术，为 LLM 提供准确、可追溯的知识增强，'
        '有效缓解了 LLM 的幻觉问题，让 AI 教学内容既专业又可靠。')
    add_body_text(doc,
        '多模型智能路由：系统通过 resolve_runtime_model_id 函数实现按任务类型的智能模型路由，'
        '将代码任务路由至 kimi-code、规划任务路由至 qwen-max、检索任务路由至 qwen-plus、'
        '图像任务路由至 qwen-image，在保证教学质量的同时有效控制了 LLM 调用成本。')
    add_body_text(doc,
        'AI Git 教练闭环：系统首创的 AI Git 教练闭环通过 Webhook 驱动 + 异步任务 + 规则校验 + '
        'LLM 点评 + 兜底机制的完整链路，实现了对学生 Git 工作流的自动化、个性化、实时化点评，'
        '将工程协作规范教学从"被动学习"转变为"主动养成"，是系统最具差异化的创新实践。')

    # ---- 9.2 创新实践清单 ----
    add_heading_styled(doc, '创新实践清单', level=2)
    add_body_text(doc,
        '系统在设计与实现过程中形成了多项创新实践，这些创新点共同构成了系统的核心竞争力，'
        '体现了 AI 技术与教育场景的深度融合。')
    _add_table_caption(doc, '表9-1 创新实践清单')
    add_styled_table(doc,
        headers=['创新点', '技术手段', '价值'],
        rows=[
            ['AI Git教练闭环', 'Webhook+异步任务+LLM点评', '自动化Git规范教学'],
            ['规则+AI双校验', '纯函数规则+LLM个性化', '准确性+个性化兼顾'],
            ['多Agent协同教学', 'LangGraph StateGraph', '苏格拉底启发式'],
            ['RAG双层知识库', '公共+私有metadata过滤', '个性化检索'],
            ['多模型智能路由', '按任务复杂度分流', '成本+性能优化'],
            ['三级降级策略', 'SSE→非流式→模拟', '高可用性'],
            ['JSON结构化反馈', 'LLM输出JSON', '前端易解析'],
            ['LLM失败兜底', '规则兜底feedback', '保证可用性'],
        ])

    # ---- 9.3 用户体验提升策略 ----
    add_heading_styled(doc, '用户体验提升策略总结', level=2)
    add_body_text(doc,
        '系统在用户体验方面进行了多项创新设计，致力于打造沉浸式、可视化、可追踪的学习体验，'
        '让 AI 教育既有"智商"又有"情商"。')
    add_bullet(doc, '实时事件总线：通过 homework-submitted、interaction-completed、'
                    'mistake-mastered-changed 等事件实现前端组件解耦协同，'
                    '一个组件的状态变化可实时触发其他组件更新；')
    add_bullet(doc, '动画交互 GSAP：使用 GSAP 实现页面过渡、元素入场、状态变化等动画效果，'
                    '提升交互的流畅感与品质感；')
    add_bullet(doc, '可视化引导：Mira 智能体生成 Mermaid 流程图、思维导图等可视化素材，'
                    '帮助学生直观理解复杂概念；')
    add_bullet(doc, 'Bento 布局：仪表盘采用 Bento 网格布局，信息密度高、视觉层次清晰，'
                    '非常适合学习数据总览场景；')
    add_bullet(doc, '全息监控：教师全息监控面板通过学生卡片网格实时展示全班学习状态，'
                    '让教师"一屏掌握全班"；')
    add_bullet(doc, '双模式 Clone URL：HTTPS 模式与 HTTPS+Token 模式自由切换，'
                    '兼顾安全性与易用性。')

    # ---- 9.4 技术与需求结合点回顾 ----
    add_heading_styled(doc, '技术与需求结合点回顾', level=2)
    add_body_text(doc,
        '回顾系统整体设计，每一项用户需求痛点都通过具体的技术手段得到了有效解决，'
        '形成了需求—技术—实现的完整闭环。这种"以需求为导向、以技术为支撑"的设计思路，'
        '确保了系统的实用性与落地性，避免了"为技术而技术"的空转。')
    add_body_text(doc,
        '系统通过校园 Gitea + AI Git 教练闭环解决了 Git 协作能力缺失的痛点，'
        '通过 LangGraph 多智能体协同解决了个性化学习指导不足的痛点，'
        '通过 RAGFlow 双层知识库解决了知识检索效率低的痛点，'
        '通过 Bento 仪表盘 + 全息监控解决了学习进度不可视的痛点，'
        '通过微信小程序 + 云函数代理解决了移动端学习缺失的痛点。'
        '五大需求痛点全部得到针对性解决，体现了系统设计的完整性与闭环性。')
    add_body_text(doc,
        '未来，系统将在以下方向持续演进：'
        '（1）扩展智能体能力边界，引入更多专业领域的 AI 智能体；'
        '（2）深化 RAG 知识库建设，引入更多优质教学资源；'
        '（3）优化 AI Git 教练点评算法，提升反馈的精准度与个性化程度；'
        '（4）探索多模态教学（语音、视频、手写等），丰富学习交互形式；'
        '（5）加强学情数据分析能力，为教师提供更深入的教学洞察。')

    # ============================================================
    # 附录
    # ============================================================
    add_heading_styled(doc, '附录', level=1)

    # 附录A
    add_heading_styled(doc, '附录A：智能体配置参数表', level=2)
    add_body_text(doc,
        '本附录汇总系统 10 个 AI 智能体的核心配置参数，包括智能体 ID、名称、角色定位、'
        '底座模型、温度参数、最大 token 数等关键配置，便于运维人员快速查阅与调整。'
        '所有智能体配置存储于后端 agents 模块的配置文件中，支持通过管理界面动态调整。')
    add_styled_table(doc,
        headers=['智能体ID', '名称', '底座模型', '温度', '类别'],
        rows=[
            ['agent_planner', 'Alina', 'qwen3.7-max', '0.3', '文本'],
            ['agent_tutor', 'Prof.X', 'qwen3.7-plus', '0.5', '文本'],
            ['agent_researcher', 'DataBot', 'qwen3.6-plus', '0.2', '文本'],
            ['agent_mistake_analyst', '错题分析师', 'qwen3.7-plus', '0.4', '文本'],
            ['agent_coder', 'CodeNinja', 'kimi-k2.7-code', '0.2', '文本'],
            ['agent_visual_guide', 'Mira', 'qwen-image-2.0-pro', '0.7', '图像'],
            ['agent_ranked_coach', '排位赛AI教练', 'qwen3.7-plus', '0.4', '文本'],
            ['agent_homework_diagnoser', '作业诊断师', 'qwen3.7-plus', '0.2', '文本'],
            ['agent_homework_reporter', '作业报告师', 'qwen3.7-plus', '0.3', '文本'],
            ['agent_analytics_advisor', '学情策略师', 'qwen3.7-plus', '0.4', '文本'],
        ])

    # 附录B
    add_heading_styled(doc, '附录B：API接口清单（18模块汇总表）', level=2)
    add_body_text(doc,
        '本附录汇总系统后端 18 个 API 模块的核心端点与功能说明，'
        '所有 API 均遵循 RESTful 设计规范，统一以 /api 为前缀，'
        '通过 JWT Token 进行身份认证。')
    add_styled_table(doc,
        headers=['模块', '核心端点', '功能'],
        rows=[
            ['auth', '/api/auth/*', 'JWT登录注册/短信验证'],
            ['agents', '/api/agents/*', '智能体配置CRUD'],
            ['chat', '/api/chat/*', 'LangGraph对话/流式'],
            ['profile', '/api/profile/*', '学生画像'],
            ['ranked', '/api/ranked/*', '排位竞赛+AI教练'],
            ['user_center', '/api/user-center/*', '用户中心'],
            ['user_knowledge', '/api/user/knowledge/*', '用户知识库'],
            ['homework', '/api/homework/*', '作业+AI诊断'],
            ['exams', '/api/exams/*', '考试'],
            ['evaluator', '/api/evaluator/*', '评测器'],
            ['forum', '/api/forum/*', '学术论坛'],
            ['code_repository', '/api/code-repositories/*', '个人代码仓库'],
            ['gitea_accounts', '/api/gitea/*', 'Gitea账号绑定'],
            ['team_git', '/api/team-git/*', '团队协作Git'],
            ['analytics', '/api/analytics/*', '学情分析'],
            ['visual_guide', '/api/visual-guide/*', 'AI引导图'],
            ['dashboard', '/api/dashboard/*', '仪表盘'],
            ['journal', '/api/journal/*', '日志'],
        ])

    # 附录C
    add_heading_styled(doc, '附录C：数据库模型清单（9表）', level=2)
    add_body_text(doc,
        '本附录汇总系统后端 SQLAlchemy ORM 定义的 9 张核心数据表，'
        '所有表均存储于 MySQL 业务数据库（与 Gitea 数据库隔离），'
        '通过 SQLAlchemy 连接池统一访问。')
    add_styled_table(doc,
        headers=['表名', '说明'],
        rows=[
            ['user_accounts', '用户账号'],
            ['student_profiles', '学生画像'],
            ['gitea_account_bindings', 'Gitea账号绑定'],
            ['user_rag_mappings', '用户RAG映射'],
            ['chat_messages', '聊天消息'],
            ['code_diagnoses', '代码诊断'],
            ['domain_records', '领域记录(JSON存储)'],
            ['ranked_questions', '排位题目'],
            ['sms_verification_codes', '短信验证码'],
        ])

    # 附录D
    add_heading_styled(doc, '附录D：环境配置参数表', level=2)
    add_body_text(doc,
        '本附录列出系统运行所需的关键环境配置参数，这些参数通过环境变量或配置文件注入，'
        '便于不同环境（开发、测试、生产）的灵活配置。')
    add_styled_table(doc,
        headers=['配置项', '示例值', '说明'],
        rows=[
            ['DATABASE_URL', 'mysql+pymysql://user:pass@host:3306/db', 'MySQL数据库连接串'],
            ['JWT_SECRET', 'random-secret-key', 'JWT签名密钥'],
            ['GITEA_URL', 'http://localhost:3000', 'Gitea服务地址'],
            ['GITEA_ADMIN_TOKEN', 'gitea-admin-token', 'Gitea管理员Token'],
            ['GITEA_WEBHOOK_SECRET', 'webhook-secret', 'Webhook验签密钥'],
            ['RAGFLOW_API_URL', 'http://localhost:9380', 'RAGFlow服务地址'],
            ['RAGFLOW_API_KEY', 'ragflow-api-key', 'RAGFlow API密钥'],
            ['RAGFLOW_CHAT_ID', 'chat-session-id', 'RAGFlow会话ID'],
            ['DASHSCOPE_API_KEY', 'dashscope-api-key', '阿里云百炼API密钥'],
            ['REDIS_URL', 'redis://localhost:6379/0', 'Redis连接地址'],
            ['FASTAPI_PORT', '8516', 'FastAPI监听端口'],
            ['FASTAPI_WORKERS', '4', 'Uvicorn worker进程数'],
        ])

    # ============================================================
    # 参考文献（GB/T 7714-2015 格式）
    # ============================================================
    add_references(doc, [
        'OpenAI. GPT-4 technical report[R/OL]. (2023-03-14)[2026-07-17]. https://arxiv.org/abs/2303.08774.',
        'Lewis P, Perez E, Piktus A, et al. Retrieval-augmented generation for knowledge-intensive NLP tasks[C]//Advances in Neural Information Systems 33. 2020: 9459-9474.',
        'LangChain. LangGraph: Building stateful, multi-actor applications with LLMs[EB/OL]. (2024-01-15)[2026-07-17]. https://github.com/langchain-ai/langgraph.',
        'Gitea. Gitea Documentation: The Lightweight Git Server[EB/OL]. (2024-06-20)[2026-07-17]. https://docs.gitea.io.',
        'RAGFlow. RAGFlow: RAG at Scale with Deep Document Understanding[EB/OL]. (2024-09-10)[2026-07-17]. https://ragflow.io.',
        'FastAPI. FastAPI - The high-performance web framework[EB/OL]. (2024-12-01)[2026-07-17]. https://fastapi.tiangolo.com.',
        '阿里云. 通义千问大语言模型技术白皮书[R/OL]. (2024-04-15)[2026-07-17]. https://qwen.aliyun.com.',
        'Vue.js. Vue 3 Documentation: The Progressive JavaScript Framework[EB/OL]. (2024-08-20)[2026-07-17]. https://vuejs.org.',
        '微信开放平台. 微信小程序开发文档[EB/OL]. (2024-10-05)[2026-07-17]. https://developers.weixin.qq.com/miniprogram/dev/framework/.',
        'Shokri R, Shmatikov V. Privacy-preserving deep learning[C]//Proceedings of the 22nd ACM SIGSAC Conference on Computer and Communications Security. 2015: 1310-1321.',
        '中华人民共和国国家质量监督检验检疫总局, 中国国家标准化管理委员会. GB/T 7714-2015 信息与文献 参考文献著录规则[S]. 北京: 中国标准出版社, 2015.',
        'Freeman S. 智慧教育: 人工智能时代的教学变革[M]. 北京: 教育科学出版社, 2023: 45-78.',
        'Bloom B S. 教育目标分类学: 认知领域[M]. 上海: 华东师范大学出版社, 2020: 23-56.',
        'Vygotsky L S. 思维与语言[M]. 李维, 译. 北京: 北京大学出版社, 2021: 89-102.',
        'Yao S, Zhao J, Yu D, et al. ReAct: Synergizing Reasoning and Acting in Language Models[C]//International Conference on Learning Representations. 2023.',
    ])

    # ── 6. 保存文档 ──
    doc.save(output_path)
    print(f'系统开发说明书已生成: {output_path}')

    # 校验：预生成标题数应与全局 tracker 标题数一致
    global_tracker = get_heading_tracker()
    if global_tracker and len(global_tracker.headings) != len(pre_tracker.headings):
        print(f'警告：预生成标题数({len(pre_tracker.headings)})与实际标题数'
              f'({len(global_tracker.headings)})不一致，目录书签可能错位！')
    else:
        print(f'已收集标题数：{len(pre_tracker.headings)}（目录与正文一致）')


if __name__ == '__main__':
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else '系统开发说明书.docx'
    images = sys.argv[2] if len(sys.argv) > 2 else './images'
    build_dev_spec(output, images)
