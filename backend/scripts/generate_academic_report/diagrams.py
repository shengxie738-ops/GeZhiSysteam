"""
diagrams.py - 生成学术报告图表（Modern Minimalist 黑白灰极简学术风格）

提供 42 张图表（架构图、流程图、数据图表）的生成函数，
统一使用灰阶配色，输出 PNG（DPI=200）。
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Rectangle
import numpy as np

# ── 颜色配置 ──
C_PRIMARY = '#1A1A1A'   # 近黑（主色）
C_DARK = '#2C2C2C'      # 深灰
C_MED = '#4A4A4A'       # 中深灰
C_GRAY = '#8C8C8C'      # 中灰
C_LIGHT = '#D9D9D9'     # 浅灰
C_ZEBRA = '#F5F5F5'     # 极浅灰
C_WHITE = '#FFFFFF'
GRAY_PALETTE = ['#1A1A1A', '#4A4A4A', '#8C8C8C', '#BFBFBF', '#D9D9D9']

# ── 字体配置 ──
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False


# ════════════════════════════════════════════════
#  辅助绘图函数
# ════════════════════════════════════════════════

def new_fig(w, h):
    """创建新画布，使用英寸坐标系，y 轴向下递增（便于自上而下布局）。"""
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    fig.patch.set_facecolor(C_WHITE)
    ax.set_facecolor(C_WHITE)
    ax.axis('off')
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.set_aspect('equal')
    ax.invert_yaxis()  # y 向下递增
    return fig, ax


def draw_box(ax, x, y, w, h, text, fill=C_WHITE, edge=C_MED,
             text_color=C_PRIMARY, fontsize=9, bold=False, rounded=True):
    """绘制圆角矩形框，内居中文字。"""
    style = "round,pad=0.02,rounding_size=0.12" if rounded else "square,pad=0.0"
    box = FancyBboxPatch((x, y), w, h, boxstyle=style,
                         linewidth=1.2, edgecolor=edge, facecolor=fill)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
            fontsize=fontsize, color=text_color, weight=weight, zorder=5)


def draw_arrow(ax, x1, y1, x2, y2, color=C_MED, style='->', text=''):
    """绘制箭头，可选标注文字（放在箭头中点，带白底避免压线）。"""
    arrow = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                            mutation_scale=14, color=color, linewidth=1.2,
                            zorder=3)
    ax.add_patch(arrow)
    if text:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my, text, fontsize=7, color=color, ha='center', va='center',
                zorder=6, bbox=dict(boxstyle='round,pad=0.15',
                                    facecolor=C_WHITE, edgecolor='none'))


def draw_diamond(ax, x, y, w, h, text, fill=C_WHITE, edge=C_MED, fontsize=8):
    """绘制菱形（决策节点），内居中文字。"""
    cx, cy = x + w / 2, y + h / 2
    pts = [(cx, y), (x + w, cy), (cx, y + h), (x, cy)]
    diamond = Polygon(pts, closed=True, linewidth=1.2,
                      edgecolor=edge, facecolor=fill, zorder=2)
    ax.add_patch(diamond)
    ax.text(cx, cy, text, ha='center', va='center',
            fontsize=fontsize, color=C_PRIMARY, zorder=5)


def save_fig(fig, path):
    """保存为 PNG，DPI=200，白色背景，紧致边距。"""
    fig.savefig(path, dpi=200, bbox_inches='tight',
                facecolor=C_WHITE, edgecolor='none', pad_inches=0.12)
    plt.close(fig)


# ── 内部布局小工具 ──

def _title(ax, text, y=0.45, fontsize=13):
    xlim = ax.get_xlim()
    cx = (xlim[0] + xlim[1]) / 2
    ax.text(cx, y, text, ha='center', va='center',
            fontsize=fontsize, color=C_PRIMARY, weight='bold', zorder=5)


def _place_row(ax, items, x_start, x_end, y_center, box_h=0.75,
               max_w=3.6, fontsize=9, fill=C_WHITE, edge=C_MED,
               text_color=C_PRIMARY, bold=False):
    """在 x_start..x_end 区间内居中排布一行方框。"""
    n = len(items)
    gap = 0.3
    avail = x_end - x_start
    bw = min((avail - gap * (n - 1)) / n, max_w) if n > 0 else max_w
    total = n * bw + gap * (n - 1)
    start = x_start + (avail - total) / 2
    for i, it in enumerate(items):
        cx = start + i * (bw + gap)
        draw_box(ax, cx, y_center - box_h / 2, bw, box_h, it,
                 fill=fill, edge=edge, text_color=text_color,
                 fontsize=fontsize, bold=bold)


def _layer_tag(ax, x, y, h, label):
    """层级标签（深色小标签）。返回标签右边界。"""
    tag_w = 1.35
    draw_box(ax, x, y + (h - 0.6) / 2, tag_w, 0.6, label,
             fill=C_DARK, edge=C_DARK, text_color=C_WHITE,
             fontsize=9, bold=True)
    return x + tag_w


def _band(ax, x, y, w, h, fill=C_ZEBRA, edge=C_LIGHT):
    bg = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                        linewidth=0.8, edgecolor=edge, facecolor=fill, zorder=1)
    ax.add_patch(bg)


def _vflow(ax, steps, x, y_start, dy=0.95, box_w=3.4, box_h=0.6):
    """纵向线性流程：steps 为字符串列表。返回 (中心列表, 末尾 y)。"""
    y = y_start
    centers = []
    for i, step in enumerate(steps):
        draw_box(ax, x - box_w / 2, y, box_w, box_h, step)
        centers.append((x, y + box_h / 2, y, y + box_h))
        if i > 0:
            _, _, _, prev_bot = centers[i - 1]
            draw_arrow(ax, x, prev_bot, x, y)
        y += dy
    return centers, y


# ════════════════════════════════════════════════
#  架构图（1-12）
# ════════════════════════════════════════════════

def gen_system_overview(output_dir):
    """1. 系统全景架构图：五层。"""
    path = os.path.join(output_dir, 'system_overview.png')
    fig, ax = new_fig(14, 9.2)
    _title(ax, '系统全景架构图')

    layers = [
        ('用户层', ['PC 浏览器', '微信小程序']),
        ('接入层', ['Nginx 反向代理\n(HTTPS)', '微信云函数\napiProxy']),
        ('应用层', ['Vue3 前端 SPA', 'React 登录页', '小程序前端']),
        ('服务层', ['FastAPI 后端\n(18 模块)', 'Gitea 服务', 'RAGFlow 服务', '阿里云 LLM\n(多模型)']),
        ('数据层', ['MySQL', 'MinIO', 'Elasticsearch', 'Redis']),
    ]
    band_x, band_w = 0.4, 13.2
    comp_x0, comp_x1 = 2.1, 13.4
    y = 1.1
    bh = 1.05
    gap = 0.35
    layer_centers = []
    for label, comps in layers:
        _band(ax, band_x, y, band_w, bh)
        _layer_tag(ax, band_x + 0.2, y, bh, label)
        _place_row(ax, comps, comp_x0, comp_x1, y + bh / 2,
                   box_h=0.75, max_w=2.8, fontsize=8.5)
        layer_centers.append(y + bh / 2)
        y += bh + gap
    # 层间中央向下箭头
    for i in range(len(layers) - 1):
        ay1 = (i + 1) * (bh + gap) + 1.1 - gap + 0.0  # bottom of layer i band approx
    # 用更简单方式：在每两个相邻层之间画中央箭头
    for i in range(len(layer_centers) - 1):
        y_top = layer_centers[i] + bh / 2 - 0.02
        y_bot = layer_centers[i + 1] - bh / 2 + 0.02
        draw_arrow(ax, 7.0, y_top, 7.0, y_bot)
    save_fig(fig, path)
    return path


def gen_deployment_arch(output_dir):
    """2. 部署架构图。"""
    path = os.path.join(output_dir, 'deployment_arch.png')
    fig, ax = new_fig(13, 9)
    _title(ax, '部署架构图（服务器 154.201.71.151）')

    # 服务器外框
    _band(ax, 0.5, 1.1, 12, 5.6, fill=C_WHITE, edge=C_MED)
    ax.text(0.7, 1.35, '服务器 154.201.71.151 (Ubuntu / systemd)',
            fontsize=10, color=C_DARK, weight='bold', ha='left', va='center')

    # Nginx
    draw_box(ax, 1.2, 2.1, 2.6, 0.9, 'Nginx\n:80 / :443', fill=C_ZEBRA, bold=True)
    # FastAPI
    draw_box(ax, 5.0, 2.1, 2.8, 0.9, 'FastAPI\n:8516 (systemd)', fill=C_ZEBRA, bold=True)
    # 前端静态
    draw_box(ax, 9.0, 2.1, 3.0, 0.9, '前端静态文件\n/opt/gezhisystem/frontend', fill=C_ZEBRA, fontsize=8)
    # MySQL
    draw_box(ax, 5.0, 3.7, 2.8, 0.8, 'MySQL\n:3306', fill=C_ZEBRA)
    # Docker 区
    _band(ax, 1.2, 4.9, 10.8, 1.5, fill=C_ZEBRA, edge=C_LIGHT)
    ax.text(1.4, 5.12, 'Docker', fontsize=9, color=C_DARK, weight='bold', ha='left', va='center')
    draw_box(ax, 1.6, 5.35, 2.4, 0.8, 'Gitea\n:3000 / :2222', fontsize=8)
    draw_box(ax, 4.4, 5.35, 2.4, 0.8, 'RAGFlow\n:80 / :9380', fontsize=8)

    # 箭头
    draw_arrow(ax, 2.5, 3.0, 2.5, 3.0)  # placeholder no-op
    draw_arrow(ax, 3.8, 2.55, 5.0, 2.55)
    draw_arrow(ax, 7.8, 2.55, 9.0, 2.55)
    draw_arrow(ax, 6.4, 3.0, 6.4, 3.7)

    # 外部服务
    draw_box(ax, 1.2, 7.1, 3.2, 0.9, '阿里云 LLM\n(多模型)', fill=C_WHITE, edge=C_GRAY, fontsize=8.5)
    draw_box(ax, 8.6, 7.1, 3.2, 0.9, '阿里云短信\n服务', fill=C_WHITE, edge=C_GRAY, fontsize=8.5)
    draw_arrow(ax, 6.4, 3.0 + 0.0, 2.8, 7.1, color=C_GRAY)
    draw_arrow(ax, 6.4, 3.0, 10.0, 7.1, color=C_GRAY)

    save_fig(fig, path)
    return path


def gen_multi_end_arch(output_dir):
    """3. 多端交互架构图。"""
    path = os.path.join(output_dir, 'multi_end_arch.png')
    fig, ax = new_fig(13, 8)
    _title(ax, '多端交互架构图')

    # PC Web 端
    draw_box(ax, 0.6, 1.4, 2.6, 0.9, 'PC Web 端\n(浏览器)', fontsize=9)
    draw_arrow(ax, 1.9, 2.3, 1.9, 3.2)
    draw_box(ax, 0.6, 3.2, 2.6, 0.9, 'Nginx\n(HTTPS)', fontsize=9)
    draw_arrow(ax, 1.9, 4.1, 1.9, 5.0)
    draw_box(ax, 0.4, 5.0, 3.0, 0.9, 'FastAPI 后端\n:8516', fontsize=9, fill=C_ZEBRA, bold=True)

    # 小程序端
    draw_box(ax, 9.8, 1.4, 2.6, 0.9, '微信小程序端', fontsize=9)
    draw_arrow(ax, 11.1, 2.3, 11.1, 3.2)
    draw_box(ax, 9.8, 3.2, 2.6, 0.9, '云函数 apiProxy', fontsize=9)
    draw_arrow(ax, 11.1, 4.1, 11.1, 5.0)
    draw_box(ax, 9.6, 5.0, 3.0, 0.9, 'FastAPI 后端\n:8516', fontsize=9, fill=C_ZEBRA, bold=True)

    # 共享数据层
    draw_arrow(ax, 1.9, 5.9, 1.9, 6.6)
    draw_arrow(ax, 11.1, 5.9, 11.1, 6.6)
    draw_box(ax, 4.0, 6.6, 5.0, 0.9, '共享数据层 (MySQL / MinIO / Redis / ES)',
             fill=C_DARK, edge=C_DARK, text_color=C_WHITE, bold=True, fontsize=9)
    draw_arrow(ax, 3.4, 7.05, 4.0, 7.05)
    draw_arrow(ax, 9.6, 7.05, 9.0, 7.05)

    save_fig(fig, path)
    return path


def gen_gitea_service_arch(output_dir):
    """4. Gitea 服务架构。"""
    path = os.path.join(output_dir, 'gitea_service_arch.png')
    fig, ax = new_fig(12, 7.5)
    _title(ax, 'Gitea 服务架构')

    draw_box(ax, 4.2, 1.2, 3.6, 0.9, 'Gitea Docker 容器\n:3000 / :2222', fill=C_ZEBRA, bold=True)
    draw_arrow(ax, 6.0, 2.1, 6.0, 2.9)

    draw_box(ax, 4.2, 2.9, 3.6, 0.8, 'campus 私有组织', fill=C_WHITE, bold=True)
    draw_arrow(ax, 6.0, 3.7, 6.0, 4.5)

    draw_box(ax, 4.2, 4.5, 3.6, 0.8, '学生私有仓库\n(stu_学号/*)')

    # 左：MySQL gitea 库
    draw_box(ax, 0.6, 2.9, 2.6, 0.8, 'MySQL\ngitea 库', fill=C_ZEBRA)
    draw_arrow(ax, 4.2, 3.3, 3.2, 3.3, text='读写')

    # 右：Webhook 回调
    draw_box(ax, 8.8, 2.9, 2.6, 0.8, 'Webhook\n回调', fill=C_ZEBRA)
    draw_arrow(ax, 7.8, 3.3, 8.8, 3.3, text='事件')
    draw_arrow(ax, 10.1, 3.7, 10.1, 5.3)
    draw_box(ax, 8.8, 5.3, 2.6, 0.8, 'FastAPI 后端\n(Webhook 接收)', fontsize=8.5)

    save_fig(fig, path)
    return path


def gen_ragflow_arch(output_dir):
    """5. RAGFlow 知识库架构。"""
    path = os.path.join(output_dir, 'ragflow_arch.png')
    fig, ax = new_fig(13, 8)
    _title(ax, 'RAGFlow 知识库架构')

    # 顶部数据集
    _band(ax, 0.5, 1.1, 12, 2.4, fill=C_ZEBRA, edge=C_LIGHT)
    ax.text(0.7, 1.3, 'RAGFlow 数据集', fontsize=10, color=C_DARK, weight='bold', ha='left', va='center')

    # 公共课程数据集
    _band(ax, 0.9, 1.6, 5.6, 1.7, fill=C_WHITE, edge=C_LIGHT)
    ax.text(1.1, 1.8, '公共课程数据集 (3 个)', fontsize=9, color=C_MED, weight='bold', ha='left', va='center')
    _place_row(ax, ['人工智能', '程序设计', '数据结构'], 1.1, 6.3, 2.7,
               box_h=0.55, max_w=1.7, fontsize=8)

    # 学生私有数据集
    _band(ax, 6.8, 1.6, 5.5, 1.7, fill=C_WHITE, edge=C_LIGHT)
    ax.text(7.0, 1.8, '学生私有数据集 (按用户)', fontsize=9, color=C_MED, weight='bold', ha='left', va='center')
    _place_row(ax, ['user_001', 'user_002', '...'], 7.0, 12.1, 2.7,
               box_h=0.55, max_w=1.7, fontsize=8)

    # 中部 RAGFlow 服务
    draw_box(ax, 4.5, 4.0, 4.0, 0.9, 'RAGFlow 服务\n(解析 / 检索)', fill=C_DARK,
             edge=C_DARK, text_color=C_WHITE, bold=True)
    draw_arrow(ax, 3.7, 3.3, 5.0, 4.0)
    draw_arrow(ax, 9.5, 3.3, 8.0, 4.0)

    # 底部存储
    _place_row(ax, ['MinIO\n(对象存储)', 'Elasticsearch\n(向量/全文)', 'Redis\n(缓存)'],
               1.0, 12.0, 6.0, box_h=0.9, max_w=3.2, fontsize=8.5, fill=C_ZEBRA)
    draw_arrow(ax, 5.5, 4.9, 3.0, 5.55)
    draw_arrow(ax, 6.5, 4.9, 6.5, 5.55)
    draw_arrow(ax, 7.5, 4.9, 10.0, 5.55)

    save_fig(fig, path)
    return path


def gen_frontend_arch(output_dir):
    """6. 前端架构。"""
    path = os.path.join(output_dir, 'frontend_arch.png')
    fig, ax = new_fig(12, 8)
    _title(ax, '前端架构（Vue3 ESM 核心）')

    # 核心
    draw_box(ax, 4.0, 3.3, 4.0, 1.2, 'Vue3 ESM 核心\n(Vite / Pinia / Vue Router)',
             fill=C_DARK, edge=C_DARK, text_color=C_WHITE, bold=True, fontsize=10)

    # 外围库（环绕）
    libs = [
        ('Tailwind\nCSS', 1.0, 1.4),
        ('ECharts', 4.5, 1.4),
        ('Three.js', 8.0, 1.4),
        ('Monaco\nEditor', 0.6, 5.0),
        ('Mermaid', 8.6, 5.0),
        ('GSAP', 1.0, 6.6),
        ('p5.js', 4.5, 6.6),
        ('Axios', 8.0, 6.6),
    ]
    for name, x, y in libs:
        draw_box(ax, x, y, 2.4, 0.9, name, fontsize=8.5, fill=C_ZEBRA)
        # 连线到核心
        cx, cy = 6.0, 3.9
        bx, by = x + 1.2, y + 0.45
        draw_arrow(ax, bx, by, cx, cy, color=C_GRAY)

    save_fig(fig, path)
    return path


def gen_miniprogram_arch(output_dir):
    """7. 小程序架构。"""
    path = os.path.join(output_dir, 'miniprogram_arch.png')
    fig, ax = new_fig(13, 8)
    _title(ax, '微信小程序架构')

    # 页面层
    _band(ax, 0.5, 1.1, 12, 1.6, fill=C_ZEBRA, edge=C_LIGHT)
    ax.text(0.7, 1.3, '页面层 (17 页面)', fontsize=9, color=C_DARK, weight='bold', ha='left', va='center')
    pages = ['首页', '课程', '作业', '考试', '错题本', '论坛', '我的', '...']
    _place_row(ax, pages, 1.0, 12.4, 2.15, box_h=0.6, max_w=1.5, fontsize=8)

    # 自定义 TabBar
    draw_box(ax, 4.5, 3.1, 4.0, 0.8, '自定义 TabBar', fill=C_WHITE, bold=True, fontsize=9)
    draw_arrow(ax, 6.5, 2.75, 6.5, 3.1)

    # 云开发
    draw_box(ax, 4.5, 4.4, 4.0, 0.8, '微信云开发\n(云函数 / 云数据库)', fill=C_ZEBRA, fontsize=8.5)
    draw_arrow(ax, 6.5, 3.9, 6.5, 4.4)

    # 云函数 apiProxy
    draw_box(ax, 4.5, 5.7, 4.0, 0.8, '云函数 apiProxy', fill=C_WHITE, bold=True, fontsize=9)
    draw_arrow(ax, 6.5, 5.2, 6.5, 5.7)

    # 后端
    draw_box(ax, 4.5, 6.9, 4.0, 0.8, 'FastAPI 后端 :8516', fill=C_DARK,
             edge=C_DARK, text_color=C_WHITE, bold=True, fontsize=9)
    draw_arrow(ax, 6.5, 6.5, 6.5, 6.9)

    save_fig(fig, path)
    return path


def gen_cloud_function_proxy(output_dir):
    """8. 云函数代理流程。"""
    path = os.path.join(output_dir, 'cloud_function_proxy.png')
    fig, ax = new_fig(13, 5)
    _title(ax, '云函数 apiProxy 代理机制')

    steps = ['小程序', 'wx.cloud\n.callFunction', '云函数\napiProxy', 'HTTP 请求\n(HTTPS)', '后端 API\nFastAPI']
    n = len(steps)
    bw, bh = 2.1, 1.0
    gap = 0.5
    total = n * bw + (n - 1) * gap
    x0 = (13 - total) / 2
    y = 2.2
    for i, s in enumerate(steps):
        x = x0 + i * (bw + gap)
        fill = C_DARK if i == n - 1 else (C_ZEBRA if i % 2 == 0 else C_WHITE)
        tc = C_WHITE if i == n - 1 else C_PRIMARY
        draw_box(ax, x, y, bw, bh, s, fill=fill, text_color=tc, fontsize=8.5, bold=(i == 0 or i == n - 1))
        if i > 0:
            px = x0 + (i - 1) * (bw + gap) + bw
            draw_arrow(ax, px, y + bh / 2, x, y + bh / 2)
    save_fig(fig, path)
    return path


def gen_langgraph_workflow(output_dir):
    """9. LangGraph 工作流。"""
    path = os.path.join(output_dir, 'langgraph_workflow.png')
    fig, ax = new_fig(11, 8)
    _title(ax, 'LangGraph 工作流')

    # START
    draw_box(ax, 4.2, 1.2, 2.6, 0.7, 'START', fill=C_DARK, edge=C_DARK,
             text_color=C_WHITE, bold=True)
    draw_arrow(ax, 5.5, 1.9, 5.5, 2.5)

    # agent 节点
    draw_box(ax, 4.0, 2.5, 3.0, 0.8, 'agent 节点', fill=C_ZEBRA, bold=True)
    draw_arrow(ax, 5.5, 3.3, 5.5, 4.0)

    # tools_condition 菱形
    draw_diamond(ax, 4.2, 4.0, 2.6, 1.2, 'tools_condition', fontsize=8)

    # 左：tools 节点（循环回 agent）
    draw_box(ax, 0.6, 4.2, 2.4, 0.8, 'tools 节点', fill=C_WHITE, fontsize=9)
    draw_arrow(ax, 4.2, 4.6, 3.0, 4.6, text='需要工具')
    draw_arrow(ax, 1.8, 4.2, 1.8, 3.3)
    draw_arrow(ax, 1.8, 3.3, 4.0, 2.9, text='返回结果')

    # 右：END
    draw_box(ax, 8.0, 4.2, 2.4, 0.8, 'END', fill=C_DARK, edge=C_DARK,
             text_color=C_WHITE, bold=True)
    draw_arrow(ax, 6.8, 4.6, 8.0, 4.6, text='无需工具')

    save_fig(fig, path)
    return path


def gen_docker_compose(output_dir):
    """10. Docker 编排。"""
    path = os.path.join(output_dir, 'docker_compose.png')
    fig, ax = new_fig(13, 8)
    _title(ax, 'Docker Compose 编排')

    # Gitea 容器
    _band(ax, 0.5, 1.2, 5.2, 1.6, fill=C_ZEBRA, edge=C_LIGHT)
    ax.text(0.7, 1.4, 'Gitea 容器', fontsize=10, color=C_DARK, weight='bold', ha='left', va='center')
    draw_box(ax, 0.8, 1.8, 4.6, 0.8, 'Gitea\n:3000 / :2222', fontsize=8.5)

    # RAGFlow Compose
    _band(ax, 6.0, 1.2, 6.5, 6.2, fill=C_ZEBRA, edge=C_LIGHT)
    ax.text(6.2, 1.4, 'RAGFlow Compose', fontsize=10, color=C_DARK, weight='bold', ha='left', va='center')

    # base 服务
    _band(ax, 6.3, 1.8, 5.9, 2.6, fill=C_WHITE, edge=C_LIGHT)
    ax.text(6.5, 2.0, 'base 服务', fontsize=9, color=C_MED, weight='bold', ha='left', va='center')
    _place_row(ax, ['MySQL', 'MinIO', 'Elasticsearch', 'Redis'],
               6.5, 12.0, 3.0, box_h=0.7, max_w=1.3, fontsize=8)

    # main 服务
    _band(ax, 6.3, 4.7, 5.9, 2.4, fill=C_WHITE, edge=C_LIGHT)
    ax.text(6.5, 4.9, 'main 服务', fontsize=9, color=C_MED, weight='bold', ha='left', va='center')
    draw_box(ax, 7.5, 5.3, 3.5, 1.2, 'ragflow-main\n:80 / :9380', fill=C_DARK,
             edge=C_DARK, text_color=C_WHITE, bold=True, fontsize=9)
    draw_arrow(ax, 9.2, 3.7, 9.2, 5.3, text='依赖')

    save_fig(fig, path)
    return path


def gen_security_system(output_dir):
    """11. 安全体系。"""
    path = os.path.join(output_dir, 'security_system.png')
    fig, ax = new_fig(13, 7)
    _title(ax, '系统安全体系')

    # 中心
    draw_box(ax, 4.8, 3.0, 3.4, 1.1, '安全中枢', fill=C_DARK, edge=C_DARK,
             text_color=C_WHITE, bold=True, fontsize=11)

    items = [
        ('JWT 认证', 1.0, 1.3),
        ('HMAC 验签', 5.0, 1.3),
        ('campus 私有组织', 9.2, 1.3),
        ('代码沙箱隔离', 1.0, 5.0),
        ('CORS 策略', 5.0, 5.0),
        ('HTTPS / TLS', 9.2, 5.0),
    ]
    for name, x, y in items:
        draw_box(ax, x, y, 2.8, 0.9, name, fill=C_ZEBRA, fontsize=9)
        draw_arrow(ax, x + 1.4, y + 0.45, 6.5, 3.55, color=C_GRAY)

    save_fig(fig, path)
    return path


def gen_test_layer_arch(output_dir):
    """12. 测试分层架构。"""
    path = os.path.join(output_dir, 'test_layer_arch.png')
    fig, ax = new_fig(13, 6)
    _title(ax, '测试分层架构')

    layers = [
        ('单元测试', 'pytest / Node\n(函数级)', C_DARK),
        ('集成测试', 'API 集成\n(模块间)', C_MED),
        ('E2E 测试', 'Playwright\n(端到端)', C_GRAY),
        ('性能测试', '并发 / 响应时间', C_LIGHT),
    ]
    n = len(layers)
    bw, bh = 2.6, 1.4
    gap = 0.6
    total = n * bw + (n - 1) * gap
    x0 = (13 - total) / 2
    y = 2.2
    for i, (name, desc, color) in enumerate(layers):
        x = x0 + i * (bw + gap)
        tc = C_WHITE if color in (C_DARK, C_MED) else C_PRIMARY
        draw_box(ax, x, y, bw, bh, f'{name}\n\n{desc}', fill=color, edge=color,
                 text_color=tc, fontsize=9, bold=True)
        if i > 0:
            px = x0 + (i - 1) * (bw + gap) + bw
            draw_arrow(ax, px, y + bh / 2, x, y + bh / 2)

    save_fig(fig, path)
    return path


# ════════════════════════════════════════════════
#  流程图（13-30）
# ════════════════════════════════════════════════

def gen_multi_agent_flow(output_dir):
    """13. 多 Agent 协同教学流程。"""
    path = os.path.join(output_dir, 'multi_agent_flow.png')
    fig, ax = new_fig(13, 6.5)
    _title(ax, '多 Agent 协同教学流程（四阶段）')

    stages = [
        ('概念引入', 'Prof.X'),
        ('直观图解', 'Mentor'),
        ('代码实战', 'CodeNinja'),
        ('纠错通关', 'Alina'),
    ]
    n = len(stages)
    bw, bh = 2.6, 1.5
    gap = 0.6
    total = n * bw + (n - 1) * gap
    x0 = (13 - total) / 2
    y = 2.5
    for i, (stage, agent) in enumerate(stages):
        x = x0 + i * (bw + gap)
        draw_box(ax, x, y, bw, bh, f'{stage}\n\nAgent: {agent}',
                 fill=C_ZEBRA, fontsize=9, bold=True)
        if i > 0:
            px = x0 + (i - 1) * (bw + gap) + bw
            draw_arrow(ax, px, y + bh / 2, x, y + bh / 2)

    save_fig(fig, path)
    return path


def gen_model_routing(output_dir):
    """14. 模型路由策略。"""
    path = os.path.join(output_dir, 'model_routing.png')
    fig, ax = new_fig(13, 8)
    _title(ax, '模型路由策略')

    # 输入
    draw_box(ax, 5.2, 1.2, 2.6, 0.8, '输入消息', fill=C_DARK, edge=C_DARK,
             text_color=C_WHITE, bold=True)
    draw_arrow(ax, 6.5, 2.0, 6.5, 2.7)

    # 判断菱形
    draw_diamond(ax, 4.8, 2.7, 3.4, 1.3, '路由判断', fontsize=9)

    # 四个分支
    branches = [
        ('含代码?', 'agent_coder\n/ kimi-code', 0.4, 4.8),
        ('需规划?', 'qwen-max', 3.4, 4.8),
        ('需检索?', 'qwen-plus', 6.4, 4.8),
        ('需图像?', 'qwen-image', 9.4, 4.8),
    ]
    for cond, model, x, y in branches:
        draw_box(ax, x, y, 2.6, 1.0, model, fill=C_ZEBRA, fontsize=8.5)
        # 从菱形右/左拉出
        draw_arrow(ax, 6.5, 4.0, x + 1.3, y, text=cond)

    # 默认
    draw_box(ax, 5.2, 6.4, 2.6, 0.9, '默认\nqwen-plus', fill=C_WHITE, bold=True, fontsize=9)
    draw_arrow(ax, 6.5, 4.0, 6.5, 6.4, text='默认')

    save_fig(fig, path)
    return path


def gen_tool_call_flow(output_dir):
    """15. 工具调用流程。"""
    path = os.path.join(output_dir, 'tool_call_flow.png')
    fig, ax = new_fig(12, 8)
    _title(ax, '工具调用流程')

    centers, _ = _vflow(ax, ['agent 节点'], x=6.0, y_start=1.3, dy=1.0, box_w=3.0, box_h=0.7)
    # tools_condition 菱形
    dy_after = 1.3
    dia_y = 1.3 + 1.0
    draw_diamond(ax, 4.6, dia_y, 2.8, 1.1, 'tools_condition', fontsize=8)
    draw_arrow(ax, 6.0, 1.3 + 0.7, 6.0, dia_y)

    # 工具执行（三个并列）
    tools_y = dia_y + 1.6
    _place_row(ax, ['RAG 检索', 'Python 沙箱', '算法图解'],
               1.0, 11.0, tools_y + 0.4, box_h=0.8, max_w=2.6, fontsize=9, fill=C_ZEBRA)
    draw_arrow(ax, 5.0, dia_y + 1.1, 2.3, tools_y)
    draw_arrow(ax, 6.0, dia_y + 1.1, 6.0, tools_y)
    draw_arrow(ax, 7.0, dia_y + 1.1, 9.7, tools_y)

    # 返回结果
    ret_y = tools_y + 1.5
    draw_box(ax, 4.5, ret_y, 3.0, 0.7, '返回结果', fill=C_WHITE, bold=True)
    draw_arrow(ax, 2.3, tools_y + 0.8, 5.0, ret_y)
    draw_arrow(ax, 6.0, tools_y + 0.8, 6.0, ret_y)
    draw_arrow(ax, 9.7, tools_y + 0.8, 7.0, ret_y)

    # 回到 agent
    draw_box(ax, 4.5, ret_y + 1.0, 3.0, 0.7, 'agent 节点', fill=C_DARK,
             edge=C_DARK, text_color=C_WHITE, bold=True)
    draw_arrow(ax, 6.0, ret_y + 0.7, 6.0, ret_y + 1.0, text='循环')

    save_fig(fig, path)
    return path


def gen_homework_diagnosis_flow(output_dir):
    """16. 三维度作业诊断。"""
    path = os.path.join(output_dir, 'homework_diagnosis_flow.png')
    fig, ax = new_fig(13, 7)
    _title(ax, '三维度作业诊断流程')

    # 三个 Agent 并列
    agents = [
        ('Alina', '规划维度'),
        ('CodeNinja', '代码维度'),
        ('Prof.X', '知识维度'),
    ]
    _place_row(ax, [f'{a}\n{d}' for a, d in agents],
               1.0, 12.0, 2.2, box_h=1.1, max_w=3.0, fontsize=9.5, fill=C_ZEBRA, bold=True)

    # 汇总
    draw_box(ax, 4.8, 4.2, 3.4, 1.0, '汇总评分', fill=C_DARK, edge=C_DARK,
             text_color=C_WHITE, bold=True, fontsize=10)
    for x in [2.5, 6.0, 9.5]:
        draw_arrow(ax, x, 2.75, 6.5, 4.2)

    # 输出
    draw_box(ax, 4.8, 5.8, 3.4, 0.8, '诊断报告 + 反馈', fill=C_WHITE, bold=True)
    draw_arrow(ax, 6.5, 5.2, 6.5, 5.8)

    save_fig(fig, path)
    return path


def gen_gitea_account_binding(output_dir):
    """17. 账号绑定流程。"""
    path = os.path.join(output_dir, 'gitea_account_binding.png')
    fig, ax = new_fig(11, 8)
    _title(ax, 'Gitea 账号绑定流程')

    steps = [
        '学生登录',
        '生成 gitea 账号\n(stu_学号)',
        '创建 Gitea 用户',
        '绑定表记录',
        '加入 campus 组织',
    ]
    _vflow(ax, steps, x=5.5, y_start=1.3, dy=1.25, box_w=3.4, box_h=0.75)
    save_fig(fig, path)
    return path


def gen_team_collab_workflow(output_dir):
    """18. 团队协作全流程。"""
    path = os.path.join(output_dir, 'team_collab_workflow.png')
    fig, ax = new_fig(13, 9.5)
    _title(ax, '团队协作全流程')

    steps = [
        '创建项目',
        '分配成员',
        '生成仓库',
        'clone',
        'branch (feature/)',
        'commit',
        'push',
        'open PR',
        'code review',
        'merge to main',
    ]
    # 双列蛇形布局
    n = len(steps)
    per_row = 5
    bw, bh = 2.1, 0.8
    gap_x = 0.4
    row_h = 1.5
    x0 = 1.0
    y0 = 1.5
    positions = []
    for i, s in enumerate(steps):
        row = i // per_row
        col = i % per_row
        if row % 2 == 1:
            col = per_row - 1 - col
        x = x0 + col * (bw + gap_x)
        y = y0 + row * row_h
        positions.append((x, y, s))
        draw_box(ax, x, y, bw, bh, s, fill=C_ZEBRA, fontsize=8.5, bold=(s == 'merge to main'))

    # 箭头连接
    for i in range(n - 1):
        x1, y1, _ = positions[i]
        x2, y2, _ = positions[i + 1]
        if y1 == y2:
            draw_arrow(ax, x1 + bw, y1 + bh / 2, x2, y2 + bh / 2)
        else:
            # 换行：从行末向下再到下一行起点（同行末→下→下行首）
            draw_arrow(ax, x1 + bw / 2, y1 + bh, x2 + bw / 2, y2)

    save_fig(fig, path)
    return path


def gen_webhook_processing(output_dir):
    """19. Webhook 处理流程。"""
    path = os.path.join(output_dir, 'webhook_processing.png')
    fig, ax = new_fig(11, 8.5)
    _title(ax, 'Webhook 处理流程')

    centers, _ = _vflow(ax, ['Gitea 事件', '接收请求'], x=5.5, y_start=1.2,
                        dy=1.0, box_w=3.0, box_h=0.7)
    # 验签菱形
    dia_y = 1.2 + 2 * 1.0
    draw_diamond(ax, 4.1, dia_y, 2.8, 1.1, 'HMAC-SHA256\n验签', fontsize=8)
    draw_arrow(ax, 5.5, 1.2 + 2 * 1.0 - 0.3, 5.5, dia_y)

    # 解析事件类型
    parse_y = dia_y + 1.6
    draw_box(ax, 4.0, parse_y, 3.0, 0.75, '解析事件类型', fill=C_WHITE, bold=True)
    draw_arrow(ax, 5.5, dia_y + 1.1, 5.5, parse_y, text='通过')

    # 两种事件
    evt_y = parse_y + 1.4
    draw_box(ax, 1.2, evt_y, 2.6, 0.75, 'push 事件', fill=C_ZEBRA, fontsize=9)
    draw_box(ax, 7.2, evt_y, 2.6, 0.75, 'PR 事件', fill=C_ZEBRA, fontsize=9)
    draw_arrow(ax, 4.5, parse_y + 0.75, 2.5, evt_y)
    draw_arrow(ax, 6.5, parse_y + 0.75, 8.5, evt_y)

    # 应用事件 → 异步触发
    app_y = evt_y + 1.3
    draw_box(ax, 1.2, app_y, 8.6, 0.75, '应用事件 → 异步触发 AI 教练', fill=C_DARK,
             edge=C_DARK, text_color=C_WHITE, bold=True, fontsize=9)
    draw_arrow(ax, 2.5, evt_y + 0.75, 4.0, app_y)
    draw_arrow(ax, 8.5, evt_y + 0.75, 7.0, app_y)

    save_fig(fig, path)
    return path


def gen_ai_git_coach_loop(output_dir):
    """20. AI Git 教练闭环。"""
    path = os.path.join(output_dir, 'ai_git_coach_loop.png')
    fig, ax = new_fig(12, 10.5)
    _title(ax, 'AI Git 教练闭环')

    main_steps = [
        'Webhook 触发',
        '异步任务',
        '加载项目',
        '遍历 commits',
        '匹配作者',
        '规则校验 (评分)',
        '获取 diff',
        '构建 prompt',
        'LLM 点评',
        '解析 JSON',
        '写回反馈',
    ]
    centers, end_y = _vflow(ax, main_steps, x=5.0, y_start=1.2,
                            dy=0.82, box_w=3.2, box_h=0.6)

    # fallback 分支（从 LLM 点评 拉出）
    llm_idx = 8
    _, _, _, llm_bot = centers[llm_idx]
    draw_box(ax, 8.5, centers[llm_idx][1] - 0.1, 2.8, 0.8, 'fallback\n兜底点评',
             fill=C_ZEBRA, fontsize=8.5)
    draw_arrow(ax, 5.0 + 1.6, centers[llm_idx][1] + 0.3, 8.5, centers[llm_idx][1] + 0.3,
               text='LLM 失败')
    # fallback 回到 写回反馈
    fb_y = centers[llm_idx][1] + 0.3
    write_y = centers[10][1] + 0.3
    draw_arrow(ax, 9.9, fb_y, 9.9, write_y)
    draw_arrow(ax, 9.9, write_y, 5.0 + 1.6, write_y)

    save_fig(fig, path)
    return path


def gen_git_rules_validation(output_dir):
    """21. Git 规则校验体系。"""
    path = os.path.join(output_dir, 'git_rules_validation.png')
    fig, ax = new_fig(13, 8)
    _title(ax, 'Git 规则校验体系（8 条规则）')

    rules = [
        'push_to_default',
        'branch_name',
        'commit_msg_short',
        'commit_msg_empty',
        'author_unmatched',
        'pr_base',
        'pr_head',
        'member_not_in_team',
    ]
    # 2 行 4 列
    bw, bh = 2.6, 0.8
    cols = 4
    gap_x = 0.4
    gap_y = 0.6
    x0 = (13 - (cols * bw + (cols - 1) * gap_x)) / 2
    y0 = 1.5
    for i, r in enumerate(rules):
        row = i // cols
        col = i % cols
        x = x0 + col * (bw + gap_x)
        y = y0 + row * (bh + gap_y)
        draw_box(ax, x, y, bw, bh, r, fill=C_ZEBRA, fontsize=8)
        # 向下汇聚到 扣分计算
        draw_arrow(ax, x + bw / 2, y + bh, 6.5, 4.6, color=C_GRAY)

    # 扣分计算
    draw_box(ax, 4.8, 4.6, 3.4, 0.9, '计算扣分', fill=C_DARK, edge=C_DARK,
             text_color=C_WHITE, bold=True, fontsize=10)
    draw_arrow(ax, 6.5, 5.5, 6.5, 6.1)
    draw_box(ax, 4.8, 6.1, 3.4, 0.8, '输出 score', fill=C_WHITE, bold=True, fontsize=10)

    save_fig(fig, path)
    return path


def gen_doc_processing_flow(output_dir):
    """22. 文档处理流程。"""
    path = os.path.join(output_dir, 'doc_processing_flow.png')
    fig, ax = new_fig(12, 8)
    _title(ax, '文档处理流程')

    centers, _ = _vflow(ax, ['上传 PDF', 'classify (仅 PDF)', 'RAGFlow upload',
                             '配置 parser (DeepDOC)', '启动解析'],
                        x=6.0, y_start=1.2, dy=1.0, box_w=3.4, box_h=0.7)

    # 状态同步（右侧四个状态）
    states = ['queued', 'parsing', 'parsed', 'failed']
    sy = 1.5
    draw_box(ax, 9.5, 1.2, 2.2, 0.7, '状态同步', fill=C_DARK, edge=C_DARK,
             text_color=C_WHITE, bold=True, fontsize=9)
    for i, s in enumerate(states):
        y = 2.2 + i * 0.85
        draw_box(ax, 9.5, y, 2.2, 0.6, s, fill=C_ZEBRA, fontsize=8.5)
    draw_arrow(ax, 7.7, 1.55, 9.5, 1.55)

    save_fig(fig, path)
    return path


def gen_rag_retrieval_flow(output_dir):
    """23. RAG 检索流程。"""
    path = os.path.join(output_dir, 'rag_retrieval_flow.png')
    fig, ax = new_fig(11, 9)
    _title(ax, 'RAG 检索流程')

    centers, _ = _vflow(ax, ['用户提问'], x=5.5, y_start=1.2, dy=0.95,
                        box_w=3.0, box_h=0.65)
    # 寒暄检测菱形
    dia_y = 1.2 + 0.95
    draw_diamond(ax, 4.1, dia_y, 2.8, 1.0, '寒暄检测', fontsize=8)
    draw_arrow(ax, 5.5, 1.2 + 0.65, 5.5, dia_y)

    # 是 → 跳过检索（右侧）
    draw_box(ax, 8.0, dia_y + 0.1, 2.6, 0.8, '跳过检索', fill=C_ZEBRA, fontsize=9)
    draw_arrow(ax, 6.9, dia_y + 0.5, 8.0, dia_y + 0.5, text='是')

    # 否 → 继续检索
    steps = ['检索公共数据集', '检索私有数据集\n(metadata 过滤)', '拼装上下文', 'LLM 生成', '附加引用来源']
    y = dia_y + 1.25
    prev_bot = dia_y + 1.0
    for i, s in enumerate(steps):
        draw_box(ax, 4.0, y, 3.0, 0.7, s, fill=C_WHITE if i < 4 else C_DARK,
                 text_color=C_WHITE if i == 4 else C_PRIMARY,
                 bold=(i == 4), fontsize=8.5)
        draw_arrow(ax, 5.5, prev_bot, 5.5, y, text='否' if i == 0 else '')
        prev_bot = y + 0.7
        y += 0.95

    save_fig(fig, path)
    return path


def gen_fallback_strategy(output_dir):
    """24. 三级降级策略。"""
    path = os.path.join(output_dir, 'fallback_strategy.png')
    fig, ax = new_fig(12, 6.5)
    _title(ax, '三级降级策略')

    steps = [
        ('首选: SSE 流式\n(/chat/stream)', C_DARK, C_WHITE),
        ('降级: 非流式\n(/chat)', C_MED, C_WHITE),
        ('降级: 本地模拟\n(setInterval 打字机)', C_GRAY, C_WHITE),
    ]
    bw, bh = 3.0, 1.3
    gap = 0.8
    total = 3 * bw + 2 * gap
    x0 = (12 - total) / 2
    y = 2.8
    for i, (s, fill, tc) in enumerate(steps):
        x = x0 + i * (bw + gap)
        draw_box(ax, x, y, bw, bh, s, fill=fill, edge=fill, text_color=tc,
                 fontsize=9, bold=True)
        if i > 0:
            px = x0 + (i - 1) * (bw + gap) + bw
            draw_arrow(ax, px, y + bh / 2, x, y + bh / 2, text='失败')

    save_fig(fig, path)
    return path


def gen_jwt_auth_flow(output_dir):
    """25. JWT 认证流程。"""
    path = os.path.join(output_dir, 'jwt_auth_flow.png')
    fig, ax = new_fig(11, 9.5)
    _title(ax, 'JWT 认证流程')

    steps = [
        '用户登录',
        '验证密码\n(pbkdf2_sha256)',
        '生成 Token\n(payload + HMAC-SHA256)',
        '返回前端',
        '后续请求携带\nAuthorization 头',
        '后端验签',
        '提取用户信息',
    ]
    _vflow(ax, steps, x=5.5, y_start=1.2, dy=1.15, box_w=3.6, box_h=0.75)
    save_fig(fig, path)
    return path


def gen_webhook_verify_flow(output_dir):
    """26. Webhook 验签流程。"""
    path = os.path.join(output_dir, 'webhook_verify_flow.png')
    fig, ax = new_fig(11, 8)
    _title(ax, 'Webhook 验签流程')

    centers, _ = _vflow(ax, ['收到请求', '提取 X-Gitea-Signature',
                             '用 Webhook Secret\n计算 HMAC-SHA256'],
                        x=5.5, y_start=1.2, dy=1.05, box_w=3.6, box_h=0.7)

    # 比对菱形
    dia_y = 1.2 + 3 * 1.05
    draw_diamond(ax, 4.0, dia_y, 3.0, 1.1, 'hmac.compare_digest\n比对', fontsize=8)
    draw_arrow(ax, 5.5, 1.2 + 3 * 1.05 - 0.35, 5.5, dia_y)

    # 通过 / 拒绝
    draw_box(ax, 1.2, dia_y + 1.5, 2.6, 0.8, '通过', fill=C_DARK, edge=C_DARK,
             text_color=C_WHITE, bold=True)
    draw_box(ax, 7.2, dia_y + 1.5, 2.6, 0.8, '拒绝', fill=C_WHITE, bold=True)
    draw_arrow(ax, 4.5, dia_y + 1.1, 2.5, dia_y + 1.5, text='匹配')
    draw_arrow(ax, 6.5, dia_y + 1.1, 8.5, dia_y + 1.5, text='不匹配')

    save_fig(fig, path)
    return path


def gen_multi_end_sync(output_dir):
    """27. 多端数据同步。"""
    path = os.path.join(output_dir, 'multi_end_sync.png')
    fig, ax = new_fig(13, 5.5)
    _title(ax, '多端数据同步')

    steps = ['PC 端操作', '后端 API', '数据库', '小程序读取\n(云函数)']
    n = len(steps)
    bw, bh = 2.6, 1.0
    gap = 0.7
    total = n * bw + (n - 1) * gap
    x0 = (13 - total) / 2
    y = 2.5
    for i, s in enumerate(steps):
        x = x0 + i * (bw + gap)
        fill = C_DARK if i == 2 else (C_ZEBRA if i % 2 == 0 else C_WHITE)
        tc = C_WHITE if i == 2 else C_PRIMARY
        draw_box(ax, x, y, bw, bh, s, fill=fill, edge=(C_DARK if i == 2 else C_MED),
                 text_color=tc, fontsize=9, bold=True)
        if i > 0:
            px = x0 + (i - 1) * (bw + gap) + bw
            draw_arrow(ax, px, y + bh / 2, x, y + bh / 2)

    save_fig(fig, path)
    return path


def gen_defect_fix_flow(output_dir):
    """28. 缺陷修复流程。"""
    path = os.path.join(output_dir, 'defect_fix_flow.png')
    fig, ax = new_fig(12, 8.5)
    _title(ax, '缺陷修复流程')

    centers, _ = _vflow(ax, ['发现缺陷'], x=6.0, y_start=1.2, dy=0.95,
                        box_w=3.0, box_h=0.65)
    # 分级菱形
    dia_y = 1.2 + 0.95
    draw_diamond(ax, 4.5, dia_y, 3.0, 1.0, '分级', fontsize=9)
    draw_arrow(ax, 6.0, 1.2 + 0.65, 6.0, dia_y)

    # 四级
    levels = ['致命', '严重', '一般', '轻微']
    ly = dia_y + 1.5
    _place_row(ax, levels, 1.0, 11.0, ly + 0.35, box_h=0.7, max_w=2.0,
               fontsize=9, fill=C_ZEBRA)
    for x in [2.0, 4.8, 7.6, 10.4]:
        draw_arrow(ax, 6.0, dia_y + 1.0, x, ly)

    # 后续流程
    rest = ['分配', '修复', '验证', '关闭']
    y = ly + 1.4
    prev_bot = ly + 0.7
    for i, s in enumerate(rest):
        fill = C_DARK if s == '关闭' else C_WHITE
        tc = C_WHITE if s == '关闭' else C_PRIMARY
        draw_box(ax, 4.5, y, 3.0, 0.7, s, fill=fill, edge=C_MED,
                 text_color=tc, bold=(s == '关闭'), fontsize=9)
        draw_arrow(ax, 6.0, prev_bot, 6.0, y)
        prev_bot = y + 0.7
        y += 0.95

    save_fig(fig, path)
    return path


def gen_nginx_proxy_flow(output_dir):
    """29. Nginx 代理流程。"""
    path = os.path.join(output_dir, 'nginx_proxy_flow.png')
    fig, ax = new_fig(13, 7)
    _title(ax, 'Nginx 代理流程')

    # 请求进入
    draw_box(ax, 5.2, 1.2, 2.6, 0.8, '请求进入', fill=C_DARK, edge=C_DARK,
             text_color=C_WHITE, bold=True)
    draw_arrow(ax, 6.5, 2.0, 6.5, 2.6)

    # location 匹配菱形
    draw_diamond(ax, 4.8, 2.6, 3.4, 1.1, '匹配 location', fontsize=9)

    # 四个目标
    targets = [
        ('/api/', 'FastAPI :8516'),
        ('/static/', 'FastAPI :8516/static'),
        ('/gitea/', 'Gitea :3000'),
        ('/', '前端静态文件'),
    ]
    ty = 4.6
    _place_row(ax, [f'{a}\n→ {b}' for a, b in targets],
               0.6, 12.4, ty + 0.5, box_h=1.0, max_w=2.9, fontsize=8, fill=C_ZEBRA)
    for x in [2.0, 4.9, 7.8, 10.7]:
        draw_arrow(ax, 6.5, 3.7, x, ty)

    save_fig(fig, path)
    return path


def gen_clone_url_dual_mode(output_dir):
    """30. Clone URL 双模式。"""
    path = os.path.join(output_dir, 'clone_url_dual_mode.png')
    fig, ax = new_fig(13, 6.5)
    _title(ax, 'Clone URL 双模式')

    # 左：HTTPS 模式
    _band(ax, 0.5, 1.4, 5.8, 4.2, fill=C_ZEBRA, edge=C_LIGHT)
    ax.text(0.7, 1.65, 'HTTPS 模式', fontsize=10, color=C_DARK, weight='bold', ha='left', va='center')
    draw_box(ax, 1.0, 2.2, 4.8, 0.9, '显示原始 URL', fill=C_WHITE, fontsize=9)
    draw_box(ax, 1.0, 3.5, 4.8, 1.6, 'https://git.example.com/\nstu_2024001/demo.git', fill=C_WHITE,
             edge=C_GRAY, fontsize=8.5)
    draw_arrow(ax, 3.4, 3.1, 3.4, 3.5)

    # 右：HTTPS + Token 模式
    _band(ax, 6.7, 1.4, 5.8, 4.2, fill=C_ZEBRA, edge=C_LIGHT)
    ax.text(6.9, 1.65, 'HTTPS + Token 模式', fontsize=10, color=C_DARK, weight='bold', ha='left', va='center')
    draw_box(ax, 7.2, 2.2, 4.8, 0.9, '生成带凭证 URL', fill=C_WHITE, fontsize=9)
    draw_box(ax, 7.2, 3.5, 4.8, 1.6, 'https://stu_2024001:\n<token>@git.example.com/\nstu_2024001/demo.git',
             fill=C_WHITE, edge=C_GRAY, fontsize=8)
    draw_arrow(ax, 9.6, 3.1, 9.6, 3.5)

    save_fig(fig, path)
    return path


# ════════════════════════════════════════════════
#  数据图表（31-42）
# ════════════════════════════════════════════════

def _styled_ax(fig):
    ax = fig.add_subplot(111)
    ax.set_facecolor(C_WHITE)
    for spine in ax.spines.values():
        spine.set_color(C_LIGHT)
    ax.tick_params(colors=C_MED, labelsize=9)
    ax.title.set_color(C_PRIMARY)
    ax.xaxis.label.set_color(C_MED)
    ax.yaxis.label.set_color(C_MED)
    return ax


def gen_git_pain_points(output_dir):
    """31. 需求痛点饼图。"""
    path = os.path.join(output_dir, 'git_pain_points.png')
    fig = plt.figure(figsize=(8, 6), dpi=200)
    fig.patch.set_facecolor(C_WHITE)
    ax = _styled_ax(fig)
    labels = ['Git 使用率低 (35%)', '团队协作流程缺失 (25%)',
              '个性化指导不足 (20%)', '知识检索效率低 (20%)']
    sizes = [35, 25, 20, 20]
    colors = GRAY_PALETTE
    wedges, texts = ax.pie(sizes, labels=labels, colors=colors,
                           startangle=90, wedgeprops=dict(edgecolor=C_WHITE, linewidth=1.5),
                           textprops=dict(color=C_PRIMARY, fontsize=9))
    ax.set_title('需求痛点分布', fontsize=13, color=C_PRIMARY, weight='bold', pad=15)
    ax.set_aspect('equal')
    save_fig(fig, path)
    return path


def gen_git_proficiency(output_dir):
    """32. Git 使用熟练度横条图。"""
    path = os.path.join(output_dir, 'git_proficiency.png')
    fig = plt.figure(figsize=(8, 6), dpi=200)
    fig.patch.set_facecolor(C_WHITE)
    ax = _styled_ax(fig)
    items = [('基础命令', 45), ('分支管理', 28), ('PR 流程', 15),
             ('冲突解决', 8), ('CI/CD', 4)]
    items_sorted = sorted(items, key=lambda t: t[1])
    names = [t[0] for t in items_sorted]
    vals = [t[1] for t in items_sorted]
    colors = [GRAY_PALETTE[i % len(GRAY_PALETTE)] for i in range(len(names))][::-1]
    bars = ax.barh(names, vals, color=colors, edgecolor=C_WHITE, height=0.6)
    for bar, v in zip(bars, vals):
        ax.text(v + 0.8, bar.get_y() + bar.get_height() / 2, f'{v}%',
                va='center', ha='left', fontsize=9, color=C_PRIMARY)
    ax.set_xlim(0, 55)
    ax.set_xlabel('学生掌握比例 (%)')
    ax.set_title('Git 使用熟练度（学生掌握比例）', fontsize=13, color=C_PRIMARY, weight='bold', pad=12)
    ax.grid(axis='x', color=C_LIGHT, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    save_fig(fig, path)
    return path


def gen_knowledge_dist(output_dir):
    """33. 知识库数据分布柱状图。"""
    path = os.path.join(output_dir, 'knowledge_dist.png')
    fig = plt.figure(figsize=(9, 6), dpi=200)
    fig.patch.set_facecolor(C_WHITE)
    ax = _styled_ax(fig)
    names = ['人工智能', '计算机程序设计', '数据结构', '数据库原理', '计算机组成']
    vals = [1200, 800, 600, 400, 300]
    colors = [GRAY_PALETTE[i % len(GRAY_PALETTE)] for i in range(len(names))]
    bars = ax.bar(names, vals, color=colors, edgecolor=C_WHITE, width=0.6)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 20, str(v),
                ha='center', va='bottom', fontsize=9, color=C_PRIMARY)
    ax.set_ylabel('文档篇数')
    ax.set_ylim(0, 1400)
    ax.set_title('知识库数据分布', fontsize=13, color=C_PRIMARY, weight='bold', pad=12)
    ax.grid(axis='y', color=C_LIGHT, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    save_fig(fig, path)
    return path


def gen_dashboard_layout(output_dir):
    """34. 仪表盘 Bento 网格布局示意图。"""
    path = os.path.join(output_dir, 'dashboard_layout.png')
    fig, ax = new_fig(11, 7.5)
    _title(ax, '仪表盘 Bento 网格布局')

    # HERO 区
    draw_box(ax, 0.5, 1.1, 10.0, 2.2, 'HERO 区\n(核心概览 / 学习进度)',
             fill=C_DARK, edge=C_DARK, text_color=C_WHITE, fontsize=11, bold=True)

    # 5 卡片
    cards = [
        ('A 今日作业', 0.5, 3.6, 1.9, 1.6),
        ('B 科目截止', 2.6, 3.6, 1.9, 1.6),
        ('C 考试通知', 4.7, 3.6, 1.9, 1.6),
        ('D 易错点', 6.8, 3.6, 1.9, 1.6),
        ('E 错题本', 8.9, 3.6, 1.6, 1.6),
    ]
    for name, x, y, w, h in cards:
        draw_box(ax, x, y, w, h, name, fill=C_ZEBRA, fontsize=9, bold=True)

    save_fig(fig, path)
    return path


def gen_test_coverage(output_dir):
    """35. 测试覆盖度柱状图（按模块）。"""
    path = os.path.join(output_dir, 'test_coverage.png')
    fig = plt.figure(figsize=(10, 6), dpi=200)
    fig.patch.set_facecolor(C_WHITE)
    ax = _styled_ax(fig)
    names = ['auth', 'agents', 'chat', 'team_git', 'gitea_accounts',
             'user_knowledge', 'homework', 'ranked', 'forum', 'analytics', '其他']
    vals = [8, 5, 6, 7, 4, 5, 4, 3, 3, 4, 12]
    colors = [GRAY_PALETTE[i % len(GRAY_PALETTE)] for i in range(len(names))]
    bars = ax.bar(names, vals, color=colors, edgecolor=C_WHITE, width=0.65)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.2, str(v),
                ha='center', va='bottom', fontsize=8.5, color=C_PRIMARY)
    ax.set_ylabel('测试用例数')
    ax.set_ylim(0, 14)
    ax.set_title('测试覆盖度（按模块）', fontsize=13, color=C_PRIMARY, weight='bold', pad=12)
    ax.grid(axis='y', color=C_LIGHT, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
    save_fig(fig, path)
    return path


def gen_test_pass_rate(output_dir):
    """36. 功能测试通过率柱状图（按模块）。"""
    path = os.path.join(output_dir, 'test_pass_rate.png')
    fig = plt.figure(figsize=(10, 6), dpi=200)
    fig.patch.set_facecolor(C_WHITE)
    ax = _styled_ax(fig)
    names = ['auth', 'agents', 'chat', 'team_git', 'gitea_accounts',
             'user_knowledge', 'homework', 'ranked', 'forum', 'analytics', '其他']
    vals = [98, 95, 96, 97, 99, 94, 96, 92, 100, 97, 98]
    colors = [GRAY_PALETTE[i % len(GRAY_PALETTE)] for i in range(len(names))]
    bars = ax.bar(names, vals, color=colors, edgecolor=C_WHITE, width=0.65)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.3, f'{v}%',
                ha='center', va='bottom', fontsize=8.5, color=C_PRIMARY)
    ax.set_ylabel('通过率 (%)')
    ax.set_ylim(85, 102)
    ax.set_title('功能测试通过率（按模块）', fontsize=13, color=C_PRIMARY, weight='bold', pad=12)
    ax.grid(axis='y', color=C_LIGHT, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
    save_fig(fig, path)
    return path


def _radar_chart(path, title, labels, values, max_val=100):
    fig = plt.figure(figsize=(8, 6), dpi=200)
    fig.patch.set_facecolor(C_WHITE)
    ax = fig.add_subplot(111, projection='polar')
    ax.set_facecolor(C_WHITE)
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    vals_plot = values + [values[0]]
    ang_plot = angles + [angles[0]]
    ax.plot(ang_plot, vals_plot, color=C_MED, linewidth=1.8)
    ax.fill(ang_plot, vals_plot, color=C_MED, alpha=0.22)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=9, color=C_PRIMARY)
    ax.set_ylim(0, max_val)
    ticks = [max_val * f for f in (0.25, 0.5, 0.75, 1.0)]
    ax.set_yticks(ticks)
    ax.set_yticklabels([str(int(t)) for t in ticks], fontsize=7, color=C_GRAY)
    ax.grid(color=C_LIGHT, linewidth=0.5)
    ax.spines['polar'].set_color(C_LIGHT)
    ax.set_title(title, fontsize=13, color=C_PRIMARY, weight='bold', pad=20)
    save_fig(fig, path)
    return path


def gen_ai_quality_radar(output_dir):
    """37. AI 智能体质量雷达图。"""
    path = os.path.join(output_dir, 'ai_quality_radar.png')
    labels = ['准确性', '相关性', '流畅度', '安全性', '效率']
    values = [92, 88, 95, 90, 85]
    return _radar_chart(path, 'AI 智能体质量评估', labels, values)


def gen_performance_test(output_dir):
    """38. 性能测试折线图。"""
    path = os.path.join(output_dir, 'performance_test.png')
    fig = plt.figure(figsize=(9, 6), dpi=200)
    fig.patch.set_facecolor(C_WHITE)
    ax = _styled_ax(fig)
    users = [1, 5, 10, 20, 30, 50, 75, 100]
    normal = [50, 60, 75, 95, 120, 180, 260, 380]
    ai = [800, 950, 1200, 1600, 2100, 3000, 4200, 5800]
    ax.plot(users, normal, color=C_PRIMARY, marker='o', linewidth=1.8,
            markersize=5, label='普通 API')
    ax.plot(users, ai, color=C_GRAY, marker='s', linewidth=1.8,
            markersize=5, label='AI 接口', linestyle='--')
    ax.set_xlabel('并发用户数')
    ax.set_ylabel('平均响应时间 (ms)')
    ax.set_title('性能测试：并发用户 vs 响应时间', fontsize=13, color=C_PRIMARY, weight='bold', pad=12)
    ax.grid(color=C_LIGHT, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    leg = ax.legend(loc='upper left', frameon=True, fontsize=9)
    leg.get_frame().set_edgecolor(C_LIGHT)
    leg.get_frame().set_facecolor(C_WHITE)
    for t in leg.get_texts():
        t.set_color(C_PRIMARY)
    save_fig(fig, path)
    return path


def gen_defect_level_pie(output_dir):
    """39. 缺陷分级饼图。"""
    path = os.path.join(output_dir, 'defect_level_pie.png')
    fig = plt.figure(figsize=(8, 6), dpi=200)
    fig.patch.set_facecolor(C_WHITE)
    ax = _styled_ax(fig)
    labels = ['致命 (2%)', '严重 (8%)', '一般 (45%)', '轻微 (45%)']
    sizes = [2, 8, 45, 45]
    colors = [C_PRIMARY, C_MED, C_GRAY, C_LIGHT]
    ax.pie(sizes, labels=labels, colors=colors, startangle=90,
           wedgeprops=dict(edgecolor=C_WHITE, linewidth=1.5),
           textprops=dict(color=C_PRIMARY, fontsize=9))
    ax.set_title('缺陷分级分布', fontsize=13, color=C_PRIMARY, weight='bold', pad=15)
    ax.set_aspect('equal')
    save_fig(fig, path)
    return path


def gen_defect_distribution(output_dir):
    """40. 缺陷分布柱状图（按模块）。"""
    path = os.path.join(output_dir, 'defect_distribution.png')
    fig = plt.figure(figsize=(9, 6), dpi=200)
    fig.patch.set_facecolor(C_WHITE)
    ax = _styled_ax(fig)
    names = ['前端', '后端 API', 'AI 智能体', 'Gitea 集成', 'RAGFlow', '小程序', '部署']
    vals = [12, 8, 6, 4, 3, 5, 2]
    colors = [GRAY_PALETTE[i % len(GRAY_PALETTE)] for i in range(len(names))]
    bars = ax.bar(names, vals, color=colors, edgecolor=C_WHITE, width=0.6)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.2, str(v),
                ha='center', va='bottom', fontsize=9, color=C_PRIMARY)
    ax.set_ylabel('缺陷数')
    ax.set_ylim(0, 15)
    ax.set_title('缺陷分布（按模块）', fontsize=13, color=C_PRIMARY, weight='bold', pad=12)
    ax.grid(axis='y', color=C_LIGHT, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    plt.setp(ax.get_xticklabels(), rotation=20, ha='right')
    save_fig(fig, path)
    return path


def gen_quality_radar(output_dir):
    """41. 系统质量评估雷达图。"""
    path = os.path.join(output_dir, 'quality_radar.png')
    labels = ['功能完整性', '性能', '安全性', '可维护性', '可用性', '可扩展性']
    values = [90, 82, 88, 85, 87, 80]
    return _radar_chart(path, '系统质量评估', labels, values)


def gen_agent_overview_chart(output_dir):
    """42. 智能体模型分布柱状图。"""
    path = os.path.join(output_dir, 'agent_overview_chart.png')
    fig = plt.figure(figsize=(9, 6), dpi=200)
    fig.patch.set_facecolor(C_WHITE)
    ax = _styled_ax(fig)
    names = ['qwen-plus', 'qwen-max', 'kimi-code', 'qwen-image', 'qwen-turbo']
    vals = [5, 3, 2, 1, 1]
    colors = [GRAY_PALETTE[i % len(GRAY_PALETTE)] for i in range(len(names))]
    bars = ax.bar(names, vals, color=colors, edgecolor=C_WHITE, width=0.6)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.1, str(v),
                ha='center', va='bottom', fontsize=9, color=C_PRIMARY)
    ax.set_ylabel('使用该模型的 Agent 数')
    ax.set_ylim(0, 6)
    ax.set_title('智能体模型分布（各模型被多少 Agent 使用）',
                 fontsize=13, color=C_PRIMARY, weight='bold', pad=12)
    ax.grid(axis='y', color=C_LIGHT, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    save_fig(fig, path)
    return path


# ════════════════════════════════════════════════
#  汇总入口
# ════════════════════════════════════════════════

_DIAGRAM_SPECS = [
    ('system_overview', gen_system_overview),
    ('deployment_arch', gen_deployment_arch),
    ('multi_end_arch', gen_multi_end_arch),
    ('gitea_service_arch', gen_gitea_service_arch),
    ('ragflow_arch', gen_ragflow_arch),
    ('frontend_arch', gen_frontend_arch),
    ('miniprogram_arch', gen_miniprogram_arch),
    ('cloud_function_proxy', gen_cloud_function_proxy),
    ('langgraph_workflow', gen_langgraph_workflow),
    ('docker_compose', gen_docker_compose),
    ('security_system', gen_security_system),
    ('test_layer_arch', gen_test_layer_arch),
    ('multi_agent_flow', gen_multi_agent_flow),
    ('model_routing', gen_model_routing),
    ('tool_call_flow', gen_tool_call_flow),
    ('homework_diagnosis_flow', gen_homework_diagnosis_flow),
    ('gitea_account_binding', gen_gitea_account_binding),
    ('team_collab_workflow', gen_team_collab_workflow),
    ('webhook_processing', gen_webhook_processing),
    ('ai_git_coach_loop', gen_ai_git_coach_loop),
    ('git_rules_validation', gen_git_rules_validation),
    ('doc_processing_flow', gen_doc_processing_flow),
    ('rag_retrieval_flow', gen_rag_retrieval_flow),
    ('fallback_strategy', gen_fallback_strategy),
    ('jwt_auth_flow', gen_jwt_auth_flow),
    ('webhook_verify_flow', gen_webhook_verify_flow),
    ('multi_end_sync', gen_multi_end_sync),
    ('defect_fix_flow', gen_defect_fix_flow),
    ('nginx_proxy_flow', gen_nginx_proxy_flow),
    ('clone_url_dual_mode', gen_clone_url_dual_mode),
    ('git_pain_points', gen_git_pain_points),
    ('git_proficiency', gen_git_proficiency),
    ('knowledge_dist', gen_knowledge_dist),
    ('dashboard_layout', gen_dashboard_layout),
    ('test_coverage', gen_test_coverage),
    ('test_pass_rate', gen_test_pass_rate),
    ('ai_quality_radar', gen_ai_quality_radar),
    ('performance_test', gen_performance_test),
    ('defect_level_pie', gen_defect_level_pie),
    ('defect_distribution', gen_defect_distribution),
    ('quality_radar', gen_quality_radar),
    ('agent_overview_chart', gen_agent_overview_chart),
]


def generate_all_diagrams(output_dir: str) -> dict:
    """生成所有图表，返回 {图片名(不含.png): 文件路径} 字典。"""
    os.makedirs(output_dir, exist_ok=True)
    result = {}
    for name, fn in _DIAGRAM_SPECS:
        path = fn(output_dir)
        result[name] = path
    return result


if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else './diagrams_out'
    res = generate_all_diagrams(out)
    print(f'已生成 {len(res)} 张图表，保存到 {out}')
    for k, v in res.items():
        print(f'  {k}: {v}')
