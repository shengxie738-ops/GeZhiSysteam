"""Generate detailed README.md for repos missing one, push to Gitea."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("OPENAI_API_KEY", "test")

from app.core.config import settings
from app.core.database import SessionLocal
from app.repositories.json_store import JsonStore
from app.services.gitea_service import GiteaService
from app.utils.datetime import utc_now_iso

MODULE = "code_repository"
PROJECT = "project"

README_BY_SLUG: dict[str, str] = {}


def _register(slug: str, content: str) -> None:
    README_BY_SLUG[slug] = content.strip() + "\n"


_register(
    "smart-dormitory-system",
    """
# 智能宿舍安全与能耗管理系统

## 项目简介

本系统面向高校宿舍管理场景，通过 **物联网传感数据模拟**、**Spring Boot 后端服务** 与 **Python AI 分析引擎**，实现对宿舍用电、环境质量、安全预警的全方位智能监控。系统帮助宿管人员及时发现违规用电、环境异常与能耗浪费，为学生创造更安全、更节能的住宿环境。

## 功能特性

| 模块 | 功能 | 说明 |
|------|------|------|
| 宿舍管理 | 楼栋/房间/学生信息 | 查看入住统计与房间状态 |
| 用电监测 | 实时功率、趋势、排行 | 24 小时用电分布与每日统计 |
| 环境监测 | 温湿度、PM2.5、CO₂、噪音 | 多指标趋势分析与异常提醒 |
| 安全预警 | 四级预警机制 | 用电/环境/设备/行为异常检测 |
| 能耗分析 | AI 报告与节能建议 | 异常检测、安全评估、趋势预测 |
| IoT 模拟 | 传感器数据生成 | 支持异常场景模拟与历史回放 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | HTML5、CSS3、JavaScript、ECharts |
| 后端 | Spring Boot、MyBatis Plus、WebSocket |
| AI 服务 | Python Flask、数据分析算法 |
| 数据层 | MySQL、Redis、IoT 模拟器 |
| 通信 | RESTful API + WebSocket 实时推送 |

## 项目结构

```
smart-dormitory-system/
├── frontend/              # 前端页面（总览、用电、环境、预警、能耗）
│   ├── index.html
│   ├── pages/
│   ├── js/
│   └── css/
├── backend/               # Spring Boot 后端
│   └── src/main/java/com/dorm/
│       ├── controller/    # 宿舍、用电、环境、预警、AI 接口
│       ├── service/
│       ├── mapper/
│       └── websocket/     # 实时监控推送
├── ai-service/            # Python AI 分析服务
│   ├── app.py
│   ├── power_anomaly.py   # 用电异常检测
│   ├── safety_predict.py  # 安全评估
│   └── energy_report.py   # 能耗报告
├── iot-simulator/         # IoT 传感器数据模拟
│   ├── app.py
│   └── sensor_mock.py
├── database/              # SQL 初始化脚本
└── docs/
    └── project_design.md  # 详细设计文档
```

## 核心 API

### 后端接口

| 模块 | 接口 | 方法 | 描述 |
|------|------|------|------|
| 宿舍 | `/api/dorm/rooms` | GET | 房间列表 |
| 用电 | `/api/power/realtime/{roomId}` | GET | 实时用电 |
| 用电 | `/api/power/trend/{roomId}` | GET | 用电趋势 |
| 环境 | `/api/environment/latest` | GET | 最新环境数据 |
| 预警 | `/api/warning/list` | GET | 预警列表 |
| 预警 | `/api/warning/handle/{id}` | PUT | 处理预警 |
| AI | `/api/ai/energy-report` | POST | 能耗报告 |
| AI | `/api/ai/safety-report` | POST | 安全评估 |

### AI 服务接口

| 接口 | 描述 |
|------|------|
| `POST /api/ai/anomaly/detect` | 用电异常检测 |
| `POST /api/ai/safety/predict` | 安全状况预测 |
| `POST /api/ai/energy/report` | 能耗报告生成 |
| `POST /api/ai/energy/saving-advice` | 节能建议 |

## AI 算法说明

1. **用电异常检测**：功率超标、深夜大功率、违规电器识别、长时间高功率监测
2. **安全评估模型**：综合用电(30%)、环境(20%)、设备(20%)、行为(15%)、历史(15%) 加权评分
3. **能耗分析**：趋势分析、等级评定、节能潜力计算、设备能耗占比

## 快速开始

### 1. 初始化数据库

```bash
mysql -u root -p < database/dorm.sql
mysql -u root -p < database/device.sql
mysql -u root -p < database/warning.sql
```

### 2. 启动后端

```bash
cd backend
# 修改 src/main/resources/application.yml 中的数据库配置
mvn spring-boot:run
```

### 3. 启动 AI 服务

```bash
cd ai-service
pip install -r requirements.txt
python app.py
```

### 4. 启动 IoT 模拟器

```bash
cd iot-simulator
pip install -r requirements.txt
python app.py
```

### 5. 访问前端

浏览器打开 `frontend/index.html`，进入总览面板查看实时数据与预警信息。

## 前端页面

| 页面 | 文件 | 功能 |
|------|------|------|
| 总览面板 | `index.html` | 关键指标、最新预警 |
| 宿舍管理 | `dorm-dashboard.html` | 楼栋与房间管理 |
| 用电监测 | `power-monitor.html` | 实时功率与趋势 |
| 环境监测 | `environment.html` | 环境指标监控 |
| 安全预警 | `safety-warning.html` | 预警处理 |
| 能耗分析 | `energy-analysis.html` | AI 报告与节能建议 |

## 项目特色

- 全栈覆盖：前端 + Java 后端 + Python AI + IoT 模拟
- 实时监控：WebSocket 推送传感器与预警数据
- 可视化丰富：折线图、柱状图、饼图、面积图
- 模块化设计：各服务独立部署，便于扩展

## 后续规划

- [ ] 接入真实 IoT 设备
- [ ] 用户登录与权限管理
- [ ] 移动端适配
- [ ] 消息推送与数据导出
- [ ] 优化 AI 检测准确率

## 许可证

本项目仅供课程学习与校园信息化演示使用。
""",
)

_register(
    "ai-emotion-companion",
    """
# AI 心理压力识别与情绪陪伴系统

## 项目简介

AI 情绪陪伴系统是一款面向 **校园心理健康辅助** 场景的全栈应用，帮助学生通过心情打卡、情绪日记、压力评估与 AI 对话等方式，持续追踪自身心理状态，并在压力升高时获得及时提醒与温暖陪伴。

系统遵循 **最小必要** 与 **隐私优先** 原则，对日记等敏感内容采用加密存储方案，详见 `docs/privacy_design.md`。

## 功能特性

| 功能 | 描述 |
|------|------|
| 心情打卡 | 每日情绪记录，支持备注与趋势可视化 |
| 情绪日记 | 私密日记书写，AES 加密存储 |
| 压力评估 | 基于多维度数据生成压力评分与预警 |
| 情绪分析 | NLP 识别文本情绪倾向（正向/负向/中性） |
| AI 陪伴聊天 | 个性化回复与心理支持对话 |
| 压力报告 | 周报/月报形式展示情绪变化趋势 |
| 隐私控制 | 数据导出、删除、功能开关 |

## 技术栈

| 模块 | 技术 |
|------|------|
| 前端 | HTML5、CSS3、原生 JavaScript |
| 后端 | Java Spring Boot、MyBatis |
| AI 服务 | Python（情绪检测、压力评分、回复生成） |
| 数据库 | MySQL |
| 安全 | HTTPS、AES-256 加密、RBAC 权限控制 |

## 项目结构

```
ai-emotion-companion/
├── frontend/
│   ├── index.html
│   ├── pages/
│   │   ├── mood-checkin/      # 心情打卡
│   │   ├── emotion-chart/     # 情绪趋势图
│   │   ├── ai-chat/           # AI 陪伴对话
│   │   └── stress-report/     # 压力报告
│   ├── components/
│   └── assets/
├── backend/
│   ├── controller/            # Mood / Diary / Stress 控制器
│   ├── service/
│   ├── mapper/
│   └── entity/
├── ai-service/
│   ├── emotion_detect.py      # 情绪识别
│   ├── stress_score.py        # 压力评分
│   └── reply_generate.py      # AI 回复生成
├── database/
│   ├── mood_record.sql
│   ├── diary.sql
│   └── stress_warning.sql
└── docs/
    └── privacy_design.md      # 隐私保护设计
```

## 核心 API

| 模块 | 接口 | 方法 | 描述 |
|------|------|------|------|
| 心情 | `/api/mood/records` | GET/POST | 心情记录查询与新增 |
| 日记 | `/api/diary/list` | GET | 日记列表 |
| 日记 | `/api/diary/save` | POST | 保存加密日记 |
| 压力 | `/api/stress/report` | GET | 压力评估报告 |
| 压力 | `/api/stress/warnings` | GET | 压力预警列表 |
| AI | `/api/ai/emotion` | POST | 文本情绪分析 |
| AI | `/api/ai/reply` | POST | 生成陪伴回复 |

## 隐私保护

- 日记内容采用 **AES-256-GCM** 端到端加密
- 用户仅可访问本人数据，支持一键导出与删除
- 管理员无法查看原始日记，仅可访问匿名统计
- 遵循《个人信息保护法》与校园心理健康数据规范

## 快速开始

### 后端

```bash
cd backend
# 执行 database/*.sql 初始化表结构
mvn spring-boot:run
```

### AI 服务

```bash
cd ai-service
pip install flask flask-cors cryptography
python app.py
```

### 前端

使用静态服务器或直接打开 `frontend/index.html`，推荐通过后端同源访问以避免跨域问题。

## 使用流程

1. 首次登录 → 阅读并同意隐私政策
2. 每日心情打卡 → 查看情绪趋势图
3. 撰写日记（可选）→ 系统自动分析情绪
4. 查看压力报告 → 关注预警提示
5. 与 AI 助手对话 → 获取陪伴与建议

## 注意事项

- 本系统为 **心理健康辅助工具**，不能替代专业心理咨询或医疗诊断
- 若出现严重心理困扰，请及时联系学校心理咨询中心
- 敏感数据请定期备份或导出

## 许可证

本项目仅供课程学习与校园心理健康信息化演示使用。
""",
)

_register(
    "ai-medication-reminder",
    """
# AI 家庭用药提醒与健康档案系统

## 项目简介

AI 家庭用药提醒与健康档案系统面向 **家庭生活健康管理** 场景，帮助用户（尤其是老人、慢性病患者）管理常用药品、服药时间、健康档案和复诊提醒。系统集成 AI 智能分析，可自动生成用药摘要、健康趋势报告与个性化提醒方案。

## 功能特性

| 模块 | 功能 |
|------|------|
| 家庭成员管理 | 添加/编辑成员，记录关系、过敏史、慢性病史 |
| 药品记录 | 药品名称、剂量、频次、途径、使用状态 |
| 服药提醒 | 定时提醒、重复规则（日/周/月）、确认服药 |
| 复诊提醒 | 自动生成复诊时间与到院提醒 |
| 健康档案 | 体检、门诊、住院、用药等多类型档案 |
| AI 用药摘要 | 一键生成用药情况分析报告 |
| AI 健康分析 | 档案摘要、趋势分析与改善建议 |
| 今日统计 | 提醒完成率与待办事项概览 |

## 技术栈

| 模块 | 技术 |
|------|------|
| 前端 | 微信小程序（WXML / WXSS / JS） |
| 后端 | Java Spring Boot 2.7 + MyBatis-Plus |
| 数据库 | H2 内存数据库（开箱即用） |
| AI 服务 | Python Flask |
| 定时任务 | Spring `@Scheduled` |

## 项目结构

```
ai-medication-reminder/
├── frontend/                  # 微信小程序
│   ├── pages/
│   │   ├── index/             # 首页
│   │   ├── family-member/     # 成员管理
│   │   ├── medicine-record/   # 药品记录
│   │   ├── reminder/          # 提醒中心
│   │   └── health-archive/    # 健康档案
│   ├── components/
│   └── utils/
├── backend/
│   └── src/main/java/com/medication/reminder/
│       ├── controller/
│       ├── service/
│       └── task/ReminderTask.java
├── ai-service/
│   ├── medication_summary.py
│   ├── health_archive_analyse.py
│   └── reminder_generate.py
├── database/
└── docs/
    └── user_manual.md
```

## 核心 API

### 家庭成员

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/family-member/listAll` | 全部成员 |
| POST | `/api/family-member/add` | 添加成员 |
| PUT | `/api/family-member/update` | 更新成员 |
| DELETE | `/api/family-member/{id}` | 删除成员 |

### 药品与提醒

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/medicine/listByMember/{id}` | 按成员查药品 |
| POST | `/api/medicine/add` | 添加药品 |
| GET | `/api/reminder/today` | 今日提醒 |
| PUT | `/api/reminder/take/{id}` | 标记已服药 |

### 健康档案

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/health-archive/add` | 添加档案 |
| POST | `/api/health-archive/ai-summary/{id}` | AI 摘要 |

### AI 服务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/medication/summary` | 用药摘要 |
| POST | `/api/health-archive/trend` | 健康趋势分析 |
| POST | `/api/reminder/generate` | 智能生成提醒 |

## 快速开始

### 1. 启动后端

```bash
cd backend
mvn spring-boot:run
# 默认 http://localhost:8080
# H2 控制台: http://localhost:8080/h2-console
```

### 2. 启动 AI 服务

```bash
cd ai-service
pip install -r requirements.txt
python app.py
# 默认 http://localhost:5000
```

### 3. 运行小程序

1. 打开微信开发者工具
2. 导入 `frontend/` 目录
3. 配置 AppID（可用测试号）
4. 编译运行

## 使用流程

1. **添加家庭成员** → 填写基本信息与健康标签
2. **录入药品** → 设置剂量与频次
3. **创建提醒** → 配置服药/复诊时间
4. **记录健康档案** → 保存体检与就诊记录
5. **查看 AI 报告** → 获取用药与健康建议

## 注意事项

> ⚠️ 本系统为辅助工具，**不能替代医生专业诊断**。用药请以医嘱为准，如有不适请及时就医。

## 许可证

本项目仅供课程学习与家庭健康管理演示使用。
""",
)

_register(
    "ai-green-life-assistant",
    """
# 智能垃圾分类与低碳生活助手

## 项目简介

AI 绿色生活助手面向 **环保与低碳校园** 场景，帮助用户通过 **拍照识别** 或 **文字查询** 快速获取垃圾分类建议，并记录步行、骑行、节水、节电、垃圾分类等低碳行为，累积绿色积分、解锁环保等级与成就徽章。

## 功能特性

| 模块 | 功能 |
|------|------|
| 垃圾分类识别 | 图片识别 + 文字查询，四大类投放建议 |
| 低碳行为记录 | 步行、骑行、节水、节电、公交、植树等 |
| 绿色积分 | 自动计分、等级晋升、校园排行榜 |
| 成就系统 | 完成环保任务获得徽章 |
| 环保知识库 | 分类指南、低碳贴士、校园环保倡议 |
| 碳减排统计 | 个人/班级碳减排量可视化 |

## 技术栈

| 模块 | 技术 |
|------|------|
| 前端 | HTML5、CSS3、原生 JavaScript |
| 后端 | Spring Boot 2.7 + MyBatis |
| 数据库 | H2（开发）/ MySQL（生产） |
| AI 服务 | Python Flask（图像识别、NLP、积分引擎） |

## 项目结构

```
ai-green-life-assistant/
├── frontend/
│   ├── index.html
│   ├── pages/
│   │   ├── garbage-identify/   # 垃圾分类
│   │   ├── carbon-record/      # 低碳记录
│   │   ├── green-score/        # 积分排行
│   │   └── knowledge/          # 环保知识
│   └── assets/
├── backend/
│   ├── controller/
│   ├── service/
│   └── entity/
├── ai-service/
│   ├── image_classify.py       # 图像分类
│   ├── garbage_nlp.py          # 垃圾名称 NLP
│   └── carbon_score.py         # 积分计算
├── database/
└── docs/
    └── product_design.md
```

## 积分等级

| 等级 | 名称 | 积分范围 |
|------|------|----------|
| Lv.1 | 环保新手 | 0 - 99 |
| Lv.2 | 环保学徒 | 100 - 299 |
| Lv.3 | 环保达人 | 300 - 599 |
| Lv.4 | 环保卫士 | 600 - 999 |
| Lv.5 | 环保大使 | 1000 - 1999 |
| Lv.6 | 地球守护者 | 2000+ |

## 核心 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/garbage/identify` | GET | 文字识别垃圾分类 |
| `/api/garbage/list` | GET | 全部分类列表 |
| `/api/carbon/record` | POST | 记录低碳行为 |
| `/api/carbon/stats/{userId}` | GET | 用户统计 |
| `/api/carbon/ranking` | GET | 积分排行榜 |
| `/api/knowledge/list` | GET | 环保知识列表 |
| `/api/user/login` | POST | 用户登录 |

## 快速开始

### 前端

```bash
cd frontend
node server.js
# 访问 http://localhost:3000
```

### 后端

```bash
cd backend
mvn clean package -DskipTests
java -jar target/ai-green-life-assistant-1.0.0.jar
# 访问 http://localhost:8080
```

### AI 服务

```bash
cd ai-service
pip install -r requirements.txt
python app.py
# 访问 http://localhost:5000
```

## 环境要求

- JDK 8+
- Node.js 14+
- Python 3.8+
- Maven 3.6+

## 适用场景

- 校园环保主题活动
- 垃圾分类宣传与实训
- 低碳生活课程设计
- 大学生全栈开发实践

## 许可证

本项目仅供课程学习与校园环保演示使用。
""",
)

_register(
    "ai-campus-life-assistant",
    """
# AI 校园生活服务助手

## 项目简介

AI 校园生活服务助手整合 **课程表、食堂、通知、失物招领、图书馆座位、快递、活动推荐** 等高频校园服务，并通过 AI 问答与个性化推荐，为学生提供一站式校园生活体验。

## 功能特性

| 模块 | 功能 |
|------|------|
| 课程表管理 | 周视图、增删改课程、颜色标记 |
| 食堂推荐 | 按时段推荐菜品、搜索、评分展示 |
| 校园通知 | 分类筛选、优先级标识、AI 摘要 |
| 失物招领 | 发布/搜索、状态管理（未找到/已认领） |
| 图书馆座位 | 楼层视图、时段预约、电源/网络属性 |
| 快递提醒 | 状态跟踪、取件码、确认签收 |
| 活动推荐 | 分类浏览、在线报名、AI 个性化推荐 |
| AI 校园问答 | 智能对话、历史记录、关键词匹配 |

## 技术栈

| 模块 | 技术 |
|------|------|
| 前端 | HTML5、CSS3、原生 JavaScript（移动端优先 SPA） |
| 后端 | Spring Boot 2.7、MyBatis-Plus |
| 数据库 | H2 内嵌数据库 |
| AI 服务 | Python Flask（问答、摘要、推荐） |

## 项目结构

```
ai-campus-life-assistant/
├── frontend/
│   ├── index.html
│   ├── js/                    # 各功能模块脚本
│   │   ├── schedule.js
│   │   ├── canteen.js
│   │   ├── notice.js
│   │   ├── lost-found.js
│   │   ├── library.js
│   │   ├── express.js
│   │   ├── activity.js
│   │   └── ai-chat.js
│   └── css/
├── backend/
│   └── src/main/java/com/campus/
│       ├── controller/
│       └── service/
├── ai-service/
│   ├── campus_qa.py           # 校园问答
│   ├── notice_summary.py      # 通知摘要
│   └── activity_recommend.py  # 活动推荐
└── docs/
    ├── requirement.md
    └── database_design.md
```

## 核心 API

| 模块 | 接口 | 描述 |
|------|------|------|
| 课程 | `GET /api/schedule/week` | 本周课程 |
| 食堂 | `GET /api/canteen/recommend` | 智能推荐 |
| 通知 | `GET /api/notice/list` | 通知列表 |
| 失物 | `POST /api/lost-found/publish` | 发布信息 |
| 图书馆 | `POST /api/library/reserve` | 座位预约 |
| 快递 | `GET /api/express/list` | 快递列表 |
| 活动 | `GET /api/activity/recommend` | AI 推荐活动 |
| AI | `POST /api/ai/chat` | 校园问答 |

## 快速开始

### 后端

```bash
cd backend
mvn spring-boot:run
```

### AI 服务

```bash
cd ai-service
pip install -r requirements.txt
python app.py
```

### 前端

浏览器打开 `frontend/index.html`，或使用本地静态服务器。推荐移动端视口预览。

## 非功能指标

- 接口响应时间 < 2 秒
- 页面加载时间 < 3 秒
- 支持 Chrome / Safari / Firefox
- 适配 iOS / Android 移动端

## 使用场景

- 新生校园生活指南
- 校园信息化课程实训
- 全栈 + AI 综合设计项目
- 智慧校园原型演示

## 许可证

本项目仅供课程学习与校园生活服务演示使用。
""",
)

_register(
    "ai-smart-campus-platform",
    """
# 墨韵博客系统

## 项目简介

墨韵博客是一个功能完整的 **内容创作与分享平台**，支持用户注册登录、文章发布与管理、分类标签、评论互动等功能。前端采用精美的 serif 字体排版与动画效果，后端提供 RESTful API 与 JWT 认证，适合作为 Web 开发课程的综合实训项目。

> 仓库 slug 为 `ai-smart-campus-platform`，实际内容为墨韵博客全栈系统。

## 功能特性

| 模块 | 功能 |
|------|------|
| 用户管理 | 注册、登录、个人资料、角色权限（管理员/作者/读者） |
| 文章管理 | 创建、编辑、删除、分类、标签、搜索 |
| 内容展示 | 首页列表、详情页、分类筛选、分页 |
| 互动功能 | 评论、点赞、收藏、分享 |
| 管理后台 | 文章/用户/评论管理、数据统计 |
| 响应式设计 | 桌面端与移动端自适应 |

## 技术栈

| 模块 | 技术 |
|------|------|
| 前端 | HTML5、CSS3、JavaScript、Font Awesome |
| 后端 | Node.js、Express.js |
| 数据库 | SQLite / 可扩展 PostgreSQL |
| 认证 | JWT Token |
| 安全 | 密码加密、SQL 注入防护、XSS 过滤 |

## 项目结构

```
ai-smart-campus-platform/
├── frontend/
│   ├── index.html             # 墨韵博客首页
│   ├── css/
│   │   ├── main.css
│   │   ├── components.css
│   │   └── animations.css
│   └── js/
│       └── app.js
├── backend/
│   ├── server.js              # Express 入口
│   ├── routes/
│   │   ├── articles.js
│   │   ├── users.js
│   │   ├── categories.js
│   │   └── comments.js
│   ├── controllers/
│   ├── middleware/auth.js
│   └── models/database.js
├── 需求分析.md
├── 系统架构设计.md
└── 数据库设计.md
```

## 核心 API

| 模块 | 接口 | 方法 | 描述 |
|------|------|------|------|
| 用户 | `/api/users/register` | POST | 用户注册 |
| 用户 | `/api/users/login` | POST | 用户登录 |
| 文章 | `/api/articles` | GET/POST | 文章列表/创建 |
| 文章 | `/api/articles/:id` | GET/PUT/DELETE | 文章详情/更新/删除 |
| 分类 | `/api/categories` | GET | 分类列表 |
| 评论 | `/api/comments` | POST | 发表评论 |

## 快速开始

### 1. 启动后端

```bash
cd backend
npm install express jsonwebtoken bcryptjs cors dotenv
node server.js
# 默认 http://localhost:3001
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 JWT_SECRET 与数据库路径
```

### 3. 访问前端

浏览器打开 `frontend/index.html`，或通过静态服务器访问。

## 数据库设计

主要数据表：

- `users` — 用户账号与角色
- `articles` — 文章内容与元数据
- `categories` — 文章分类
- `comments` — 评论与回复
- `tags` — 标签关联

详细 ER 设计见 `数据库设计.md`。

## 性能与安全

- 页面加载目标 < 3 秒
- 支持 100+ 并发用户
- JWT 会话管理 + 密码哈希存储
- 服务端输入验证与参数化查询

## 许可证

本项目仅供课程学习与 Web 开发演示使用。
""",
)

_register(
    "course-review-sentiment-analysis",
    """
# 课程评论情感分析系统

## 项目简介

课程评论情感分析系统通过 NLP 技术对 **课程评价文本** 进行自动清洗、分词、情感分类与关键词提取，帮助教师快速了解学生对课程的真实反馈，识别负面评论中的共性问题，并生成可视化分析报告。

## 功能特性

| 功能 | 描述 |
|------|------|
| 文本清洗 | 去除 HTML、特殊字符、重复空格 |
| 中文分词 | 基于词典分词 + 停用词过滤 |
| 情感分类 | 正向 / 中性 / 负向 三分类 |
| 关键词提取 | TF-IDF / 词频统计生成词云 |
| 反馈报告 | 课程整体满意度与情感分布 |
| 负面评论分析 | 低分评论聚合与改进建议 |
| 可视化仪表盘 | 饼图、词云、评论卡片 |

## 技术栈

| 模块 | 技术 |
|------|------|
| 后端 | Python、Flask、Flask-CORS |
| NLP | jieba 分词、自定义情感词典 |
| 前端 | Vue.js |
| 数据 | CSV 评论数据集 |
| 测试 | pytest |

## 项目结构

```
course-review-sentiment-analysis/
├── README.md
├── requirements.txt
├── data/
│   ├── course_reviews.csv     # 课程评论样本
│   └── stopwords.txt          # 停用词表
├── backend/
│   ├── main.py
│   ├── api/
│   │   └── sentiment_api.py   # RESTful API
│   ├── services/
│   │   ├── text_cleaner.py    # 文本清洗
│   │   ├── tokenizer.py       # 分词
│   │   ├── sentiment_classifier.py
│   │   ├── keyword_extractor.py
│   │   └── report_service.py
│   └── models/
│       ├── course_review.py
│       ├── sentiment_result.py
│       └── keyword_stat.py
├── frontend/
│   ├── pages/
│   │   ├── ReviewAnalysisDashboard.vue
│   │   ├── CourseFeedbackReport.vue
│   │   └── NegativeReviewList.vue
│   └── components/
│       ├── SentimentPieChart.vue
│       ├── KeywordCloud.vue
│       └── ReviewCard.vue
├── notebooks/
│   └── sentiment_training_demo.ipynb
└── tests/
    ├── test_text_cleaner.py
    ├── test_sentiment_classifier.py
    └── test_keyword_extractor.py
```

## 核心 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/reviews/load` | POST | 加载 CSV 评论数据 |
| `/api/reviews/analyze` | POST | 批量情感分析 |
| `/api/reviews/sentiment-stats` | GET | 情感分布统计 |
| `/api/reviews/keywords` | GET | 关键词提取结果 |
| `/api/reviews/negative` | GET | 负面评论列表 |
| `/api/reports/course/{id}` | GET | 课程反馈报告 |

## 情感分类规则

系统采用 **词典 + 规则** 混合方法：

1. 清洗原始评论文本
2. jieba 分词并去除停用词
3. 匹配正向/负向情感词表
4. 计算情感得分并映射为三分类
5. 提取 Top-N 关键词用于词云展示

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动后端

```bash
python -m backend.main
# 或
python backend/main.py
# 默认 http://localhost:5000
```

### 3. 运行测试

```bash
pytest tests/ -v
```

### 4. 前端

将 Vue 页面集成到前端构建工具，或通过 API 直接调用演示。

## 数据格式

`data/course_reviews.csv` 示例字段：

| 字段 | 说明 |
|------|------|
| review_id | 评论 ID |
| course_id | 课程 ID |
| course_name | 课程名称 |
| student_id | 学生 ID |
| content | 评论正文 |
| rating | 评分 (1-5) |
| created_at | 评论时间 |

## 应用场景

- 教务系统课程质量评估
- 教学改进决策支持
- NLP 课程实验项目
- 教育数据挖掘演示

## 许可证

本项目仅供课程学习与教学评价分析演示使用。
""",
)


def _clone_url(owner: str, repo: str) -> str:
    token = settings.GITEA_API_TOKEN
    base = settings.GITEA_BASE_URL.rstrip("/")
    if token:
        return f"{base.replace('://', f'://oauth2:{token}@')}/{owner}/{repo}.git"
    return f"{base}/{owner}/{repo}.git"


def _run_git(args: list[str], *, cwd: Path) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {(result.stderr or result.stdout).strip()}")


def push_readme(slug: str, content: str, *, author: str = "system") -> dict:
    owner = settings.GITEA_ORG or "campus"
    with tempfile.TemporaryDirectory(prefix=f"readme-{slug}-") as tmp:
        parent = Path(tmp)
        _run_git(["clone", _clone_url(owner, slug), "repo"], cwd=parent)
        work = parent / "repo"
        (work / "README.md").write_text(content, encoding="utf-8")
        _run_git(["config", "user.name", author], cwd=work)
        _run_git(["config", "user.email", "readme-bot@gezhi.local"], cwd=work)
        _run_git(["add", "README.md"], cwd=work)
        _run_git(["commit", "-m", f"docs: add detailed README for {slug}"], cwd=work)
        _run_git(["push", "origin", "HEAD"], cwd=work)
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(work), text=True).strip()
    return {"slug": slug, "status": "pushed", "commit": sha}


def sync_db_readme(db, slug: str, content: str) -> None:
    store = JsonStore(db)
    project = store.get_payload(MODULE, PROJECT, slug)
    if not project:
        return
    project["readme"] = content
    project["readmeSyncedAt"] = utc_now_iso()
    project.pop("readmeError", None)
    store.upsert(MODULE, PROJECT, slug, project, owner_id=project.get("author") or "", status=project.get("status") or "active")


def main() -> int:
    parser = argparse.ArgumentParser(description="Add detailed README to repos missing one")
    parser.add_argument("--only", default="", help="Comma-separated slugs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    targets = [s for s in README_BY_SLUG if not only or s in only]

    if args.dry_run:
        print(json.dumps({"targets": targets, "count": len(targets)}, ensure_ascii=False, indent=2))
        return 0

    db = SessionLocal()
    results = []
    try:
        for slug in targets:
            content = README_BY_SLUG[slug]
            store = JsonStore(db)
            project = store.get_payload(MODULE, PROJECT, slug)
            author = (project or {}).get("author") or "system"
            try:
                result = push_readme(slug, content, author=author)
                sync_db_readme(db, slug, content)
                results.append(result)
                print(json.dumps(result, ensure_ascii=False))
            except Exception as exc:
                err = {"slug": slug, "status": "failed", "error": str(exc)}
                results.append(err)
                print(json.dumps(err, ensure_ascii=False))
        print(json.dumps({"summary": results}, ensure_ascii=False, indent=2))
        return 1 if any(r.get("status") == "failed" for r in results) else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
