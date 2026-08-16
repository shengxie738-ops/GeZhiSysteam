# NextUp（小程序端下一阶段开发说明）

本文档用于指导下一棒 AI/工程同学在**不依赖额外口头说明**的情况下，将“格至学习系统”微信小程序端从当前雏形推进到可稳定演示、可持续迭代的阶段。  
文档以**学子端优先**，并对照 Web 端的能力模块（Coach / Profiler / Mapper / Evaluator）抽取出在小程序端实现**可行性中-高**且**必要程度高**的部分，形成明确的目标、边界、实现细节与验收标准。

重要约束：你当前小程序端已完成“书院升级”前端体系（设计 token + 组件类 + 页面重构）。后续新增/改造功能**必须遵循现有风格与工程约束**，不得另起一套视觉或引入重型 UI 方案。

---

## 0. 现状快照（以仓库为准）

### 0.1 已存在页面（app.json）

- 启动页：`pages/splash/index`
- 登录页：`pages/login/index`
- 首页（学业案卷仪表盘）：`pages/home/index`
- 学术空间（论坛列表）：`pages/course/index`
- AI 导师（Tutor/RAG）：`pages/chat/index`
- 个人中心（学习档案雏形）：`pages/profile/index`
- 论坛详情：`pages/forum-detail/index`
- 错题本：`pages/mistake-book/index`
- 知识库（课件资料）：`pages/knowledge-base/index`

### 0.2 已存在的基础设施

- 请求封装：`utils/request.js`
  - 自动注入 `Authorization: Bearer <token>`
  - 401 自动清理登录态并重定向登录页
  - 超时与错误信息已统一
- 全局设计系统：`app.wxss`
  - 颜色/字号/间距/圆角/阴影 token
  - `card / btn / tag / modal / empty-state / bamboo-divider / wave-bg` 等通用类
- 自定义 TabBar：`custom-tab-bar/*`（已完成 emoji→Unicode、pill 样式）

---

## 1. NextUp 总目标（必须达成）

### 1.1 产品目标（学子端）

将小程序从“功能入口集合”提升为“可闭环的学习系统”：

1) 学子能明确看到：**我学得怎么样（画像）→ 下一步做什么（建议/任务）→ 做完是否变好（记录/趋势）**  
2) AI 导师不只是聊天：能在 Tutor/RAG 模式中体现 **多智能体协作 + 证据引用 + 可行动建议**  
3) 学情画像不只分数：要有**解释层**与**可执行的学习路线（简化的知识图谱/知识点地图）**  
4) 轻量测评（Evaluator 的小程序版）形成“学-练-测-评”的最小闭环（不做本地执行）

### 1.2 工程目标（必须达成）

- 新增功能必须复用 `app.wxss` 设计系统与通用类，保持全端一致
- 不引入重型第三方 UI 库（含图表/编辑器/富文本大依赖）
- 维持包体积与真机调试可用（已在 `project.config.json` 配置忽略 `.trae` 等目录）
- 错误态/空态/加载态必须覆盖关键路径（登录、首页、问答、资料、错题、测评）

---

## 2. 范围与非目标（必须遵守）

### 2.1 范围（本期要做：可行性中-高）

#### A. 学纪（Learning Journal）
- 目标：把“学习系统”落在可持续记录与复盘上  
- 落地：学习事件流 + 今日学纪卡 + 学纪详情页

#### B. 多智能体导师（Coach）
- 目标：让 Tutor/RAG 两种模式“有明确定位、有建议可点、有证据可追溯”  
- 落地：会话组织、建议问题、引用来源卡、对话结果沉淀为学习事件

#### C. 学情画像 + 简化拓扑（Profiler / Mapper）
- 目标：用“小程序友好”的结构呈现画像与知识地图  
- 落地：画像概要卡、趋势、知识点树/章节地图（简化拓扑）

#### D. 轻量测评（Evaluator 的小程序版）
- 目标：在不做本地沙箱执行的前提下，形成最小“测评闭环”  
- 落地：测评列表、测评详情（题目）、提交、结果、错因沉淀到错题本/画像

### 2.2 非目标（本期不做）

1) Web 端“智能网格/规约编排控制台”类能力：不搬到小程序  
2) 完整代码仓库（Repository）：不在小程序做文件树/diff/版本管理  
3) 复杂全域拓扑大图（力导图/大规模节点渲染）：不在小程序做  
4) 小程序端本地代码执行：不做（全部依赖后端沙箱）

---

## 3. 强约束：UI/交互必须遵循“书院升级”体系（可以做 / 不可以做）

### 3.1 必须复用的设计系统

#### 色彩/字号/间距
所有新增页面、弹窗、标签、按钮必须使用 `app.wxss` 的 token（`--color-* / --font-* / --space-* / --radius-* / --shadow-*`）。

#### 必须优先复用的通用类
- 卡片：`card / card-lg`
- 按钮：`btn / btn-primary / btn-secondary / btn-ghost / btn-sm / btn-xs`
- 标签：`tag / tag-seal / tag-indigo / tag-bamboo / tag-warning / tag-dark`
- 弹窗：`modal-mask / modal-content / modal-header / modal-title / modal-close`
- 空状态：`empty-state / empty-state-icon / empty-state-text`
- 分隔：`bamboo-divider / bamboo-divider-dot`
- 背景：`wave-bg`

### 3.2 不可以做（硬禁止）

- 不允许重新引入 emoji 作为主要 UI 图标
- 不允许在页面内复制大量“局部私有样式”而不沉淀为全局类（除非页面确实独有）
- 不允许引入重型 UI 组件库（会带来包体积、风格不一致、维护成本）
- 不允许新增与现有风格冲突的配色体系（尤其是泛科技霓虹风、纯黑高饱和风）

### 3.3 可以做（允许且推荐）

- 在 `app.wxss` 增量补充 token（必须语义化命名、保持现有命名风格）
- 在 `components/` 中沉淀高频 UI（在功能稳定后再抽；本期可先以样式复用为主）
- 使用小程序原生 `canvas` 做轻量图表（环形进度、柱状、折线），但必须有降级与性能边界

---

## 4. 信息架构（IA）与页面规划

### 4.1 保持现有 Tab 结构（不改变四大入口）
- 首页：仪表盘 + 今日建议 + 快捷入口
- 学术空间：论坛（后续可扩展为课程/讨论/资源）
- AI 导师：Tutor/RAG
- 我的：学习档案

### 4.2 建议新增页面（NextUp 需要）

为保证闭环，建议新增以下页面（命名可调整，但职责必须一致）：

1) `pages/journal/index`：学纪列表/时间线（学习事件流）
2) `pages/journal-detail/index`：学纪详情（按日/周查看）
3) `pages/portrait/index`：学情画像详情（趋势 + 知识点地图入口）
4) `pages/knowledge-map/index`：知识点地图（简化拓扑/章节树）
5) `pages/evaluator/index`：测评中心（测评列表、练习入口）
6) `pages/evaluator-detail/index`：测评详情（题目展示/作答/提交）
7) `pages/evaluator-result/index`：测评结果（解析、薄弱点、沉淀错题）

如果你希望控制页面数量，也可合并：
- `journal` 与 `journal-detail` 合并为一个页面（顶部筛选 日/周）
- `portrait` 与 `knowledge-map` 合并（tab 切换：画像/地图）

---

## 5. 统一数据模型（前后端都应遵循）

说明：以下模型是“实现时必须能落地”的最小集合。字段可增，但不要删核心字段。  
时间字段建议统一 ISO 字符串（或后端统一时间戳，前端统一格式化）。

### 5.1 LearningEvent（学习事件：学纪核心）

- `id: string`
- `userId: string`
- `type: 'chat' | 'rag' | 'mistake' | 'quiz' | 'knowledge_upload' | 'forum' | 'profile_update'`
- `title: string`（列表显示主标题）
- `summary?: string`（列表摘要/一句话复盘）
- `relatedIds?: string[]`（关联实体：chatSessionId / mistakeId / docId / quizAttemptId）
- `tags?: string[]`（课程/知识点/模块标签）
- `scoreDelta?: number`（画像指标变化，可选）
- `createdAt: string`

### 5.2 ProfileSummary（画像概要）

- `userId: string`
- `knowledgeScore: number`（0-100）
- `paceScore: number`（0-100）
- `cognitiveStyle: string`（如“渐进理解型”）
- `goal: string`
- `level?: string`（如“致知境”）
- `updatedAt: string`

### 5.3 KnowledgeMapNode（知识地图节点：简化拓扑）

- `id: string`
- `name: string`
- `parentId?: string`
- `mastery: number`（0-100）
- `status: 'weak' | 'ok' | 'strong'`
- `relatedMistakeCount?: number`
- `recommendedActions?: Array<{ type: 'read' | 'quiz' | 'ask_ai'; label: string; payload?: any }>`

### 5.4 ChatSession / ChatMessage（AI 会话）

ChatSession：
- `id: string`
- `mode: 'tutor' | 'rag'`
- `title: string`（自动生成：来自首问/知识点）
- `folderId?: string`（RAG 绑定资料夹）
- `createdAt: string`

ChatMessage：
- `id: string`
- `sessionId: string`
- `role: 'user' | 'assistant'`
- `agent?: 'Alina' | 'CodeNinja' | 'Prof.X' | 'DataBot'`
- `content: string`
- `references?: Array<{ docId: string; docName: string; chunkId?: string; quote?: string }>`
- `createdAt: string`

### 5.5 Quiz / QuizAttempt（轻量测评）

Quiz：
- `id: string`
- `title: string`
- `topicTags: string[]`
- `difficulty: 1|2|3|4|5`
- `questionCount: number`
- `estimatedMinutes?: number`

QuizAttempt：
- `id: string`
- `quizId: string`
- `userId: string`
- `status: 'in_progress' | 'submitted' | 'graded'`
- `score?: number`
- `weakTags?: string[]`
- `createdAt: string`
- `submittedAt?: string`

---

## 6. 功能详述（中-高可行性模块，按“目标→流程→数据→UI→验收”写清）

### 6.1 学纪（Learning Journal）

#### 6.1.1 目标
- 将用户在小程序内的关键行为沉淀为可回看、可复盘、可影响画像的数据资产
- 首页能回答：今天做了什么、下一步做什么
- 个人中心能回答：近期成长、薄弱点、建议路线

#### 6.1.2 入口与页面
- 首页（`pages/home/index`）新增入口：`学纪`（建议放在“常用功能”或画像卡下方）
- 个人中心（`pages/profile/index`）新增入口：`学习档案/学纪`
- 新页面：`pages/journal/index`（时间线列表）与 `pages/journal-detail/index`（按日/周聚合）

#### 6.1.3 学纪事件触发点（必须覆盖）
以下行为发生时，必须写入 `LearningEvent`：
- AI 导师发送并成功返回回答：`type=chat` 或 `type=rag`
- 知识库上传并向量化成功：`type=knowledge_upload`
- 错题被新增/被标记掌握：`type=mistake`
- 测评提交并出分：`type=quiz`
- 论坛发帖/回复/点赞（若未来实现）：`type=forum`

#### 6.1.4 列表展示规范（UI）
- 每条事件用 `card` 展示：`标题区（title）- 摘要区（summary）- 行动区（查看/继续）`
- 时间与标签使用 `tag`：课程用 `tag-dark`，重要事件可用 `tag-seal`
- 空状态必须用 `empty-state`，并给出行动建议（去问 AI / 去做测评 / 上传资料）

#### 6.1.5 数据获取与缓存
- 列表分页：`page`/`cursor` 任一模式均可，但必须支持下拉刷新与触底加载
- 本地缓存策略（建议）：
  - 首页只取最近 N 条（如 5 条）并缓存 5 分钟
  - 学纪页缓存最近一次加载结果，弱网时展示缓存并提示“数据可能不是最新”

#### 6.1.6 验收标准
- 首页能看到“最近学纪/今日学纪”的可读卡片
- 学纪页能稳定展示事件流（含空态/失败态/分页）
- AI/错题/资料/测评至少三类事件能稳定写入并展示

---

### 6.2 多智能体导师（Coach：Tutor/RAG 的产品化）

#### 6.2.1 目标
- Tutor：像“主导师+分工助手”的学习对话（讲解/代码/推理/数据）
- RAG：像“基于你资料的课件问答”，引用可追溯
- 降低“不知道问什么”的空会话成本：提供建议问题与课程导向

#### 6.2.2 必须保留/强化的能力
1) 模式切换器（Tutor/RAG）必须清晰、可解释  
2) 引用来源必须是独立卡片（indigo 体系），包含：
   - 文档名
   - 可选：引用片段/定位（chunkId）
3) 建议问题（空会话 + 每次回答后）：
   - 空会话：3 条建议问题（你已做）
   - 回答后：可追加“追问建议”（建议后端返回 or 前端规则生成）
4) 会话归档：同一用户的会话要可在未来进入“历史会话列表”

#### 6.2.3 明确“可以做/不可以做”
- 可以做：
  - 将会话分组（按课程/资料夹/时间）
  - 将关键回答沉淀为学习事件（学纪）
  - 在 RAG 模式下绑定资料夹（从知识库选择）
- 不可以做：
  - 小程序端实现复杂的多轮编排控制台（属于 Web 智能网格）
  - 强依赖流式输出（可选增强；本期不作为必须）

#### 6.2.4 交互流（必须实现）
- 进入 AI 页：
  - 若无会话：展示空会话建议问题（已具备）
  - 若有会话：加载最近会话消息
- 发送消息：
  - 输入校验（空/过长）
  - loading/思考态（已具备）
  - 返回后：
    - 展示回答
    - 若有引用：展示引用卡
    - 写入学习事件 `type=chat/rag`

#### 6.2.5 验收标准
- Tutor/RAG 两种模式可用，UI 一致且“可解释”
- RAG 引用来源卡稳定展示，弱网/空引用有明确提示
- “建议问题”可一键发送（你已补齐 `onSuggestTap`）
- 对话完成后能写入学纪事件（依赖学纪模块）

---

### 6.3 学情画像 + 简化拓扑（Profiler / Mapper）

#### 6.3.1 目标
让“画像”变成可行动的学习指导，而不是数据展示：
- 我哪里弱（知识点/章节）
- 我该做什么（阅读资料/问 AI/做测评/复习错题）
- 做完后是否变好（趋势）

#### 6.3.2 小程序端的“拓扑”边界（非常重要）
- 不做：力导图、复杂节点拖拽、上千节点渲染
- 要做：章节树/知识点树（可折叠）、掌握度条、薄弱点列表、推荐动作按钮

#### 6.3.3 页面建议（两页或一页两 tab）
1) 画像详情页 `pages/portrait/index`
   - 顶部：`ProfileSummary`（知识掌握度/研学活力/认知风格/目标）
   - 中部：趋势（最近 7/30 天掌握度、活跃度）
   - 底部：薄弱点 Top N（直达：错题/测评/资料/问 AI）

2) 知识地图页 `pages/knowledge-map/index`
   - 章节树（折叠）
   - 节点右侧显示 mastery（进度条/小环）
   - 节点展开可显示推荐动作（read/quiz/ask_ai）

#### 6.3.4 数据联动规则（必须落地）
画像与其它模块联动的最小规则：
- 错题新增/掌握：影响对应知识点 mastery（后端算也可，前端只展示）
- 测评提交：影响对应知识点 mastery 与弱项标签
- RAG 问答：可记录为学习事件，并计入“研学活力/学习节奏”

#### 6.3.5 验收标准
- 画像页可解释：至少提供 3 条“下一步建议”
- 知识地图可用：可折叠、可定位薄弱点、可跳转行动入口
- 弱网/无数据时有明确空态与引导

---

### 6.4 轻量测评（Evaluator 的小程序版）

#### 6.4.1 目标
形成“测评闭环”但控制成本：
- 以客观题/结构化题为主（选择/判断/填空/简答），不强求代码运行
- 结果能沉淀到：错题本、学纪、画像薄弱点

#### 6.4.2 页面与流程（必须）
1) 测评中心 `pages/evaluator/index`
   - 分类/标签筛选（课程/知识点）
   - 测评卡片：标题、题量、预计时长、难度、标签
   - 入口：开始测评 / 继续上次

2) 测评详情 `pages/evaluator-detail/index`
   - 顶部：测评信息 + 进度（第 x/y 题）
   - 题目区：题干、选项/输入框
   - 底部：上一题/下一题/提交（统一按钮体系）
   - 临时保存：离开页面自动保存 attempt（本地+后端均可）

3) 测评结果 `pages/evaluator-result/index`
   - 得分、正确率、用时
   - 薄弱点标签（tag-warning）
   - 解析（分题展示：正确答案、解析、推荐动作）
   - 一键沉淀：加入错题本 / 去问 AI / 去看资料

#### 6.4.3 不可做（本期硬边界）
- 不在小程序端实现代码沙箱执行（运行/编译/交互式终端）
- 不在小程序端实现复杂代码编辑器（可以做简化输入框/textarea）

#### 6.4.4 验收标准
- 完成一次测评：开始→作答→提交→结果页完整闭环
- 结果可驱动行动：至少支持“加入错题本”和“去问 AI”
- 失败态明确：提交失败可重试；题目加载失败有提示

---

## 7. API 约定（给后端/实现同学的接口草案）

说明：你后端尚未最终定型，以下是“为了前端可实现与可测试”所需的最小接口集合。  
实现同学可调整路径与字段，但必须保证：可分页、可鉴权、可错误提示、返回结构稳定。

### 7.1 学纪
- `GET /api/journal/events?cursor=&limit=`
- `GET /api/journal/events/day?date=YYYY-MM-DD`
- `POST /api/journal/events`（前端可选：也可由后端在相关业务接口内部自动写事件）

### 7.2 画像与知识地图
- `GET /api/profile/summary`
- `GET /api/profile/trends?range=7d|30d`
- `GET /api/profile/knowledge-map?rootId=&depth=`

### 7.3 AI 会话（建议统一为会话制）
- `GET /api/chat/sessions?mode=tutor|rag`
- `GET /api/chat/sessions/:id/messages`
- `POST /api/chat/sessions`（创建会话，可选）
- `POST /api/chat/messages`（发送消息，返回 assistant 消息 + references + suggestedQuestions）

### 7.4 测评
- `GET /api/evaluator/quizzes?tag=&difficulty=&cursor=&limit=`
- `POST /api/evaluator/attempts`（开始/继续）
- `GET /api/evaluator/attempts/:id`
- `POST /api/evaluator/attempts/:id/submit`
- `GET /api/evaluator/attempts/:id/result`

### 7.5 错题联动（已有则复用）
- `POST /api/mistakes`（新增错题）
- `PATCH /api/mistakes/:id`（掌握状态）

---

## 8. 错误处理与状态规范（实现必须统一）

### 8.1 状态类型
每个页面至少覆盖：
- `loading`：首次进入加载
- `empty`：成功但无数据
- `error`：请求失败（含重试按钮）
- `partial`：弱网/缓存（可选）

### 8.2 提示口径
统一使用 `utils/request.js` 抛出的错误信息展示给用户（不要吞掉错误只 `console.error`）。

### 8.3 登录失效
已由 `request.js` 处理 401 重定向。新增模块不得重复实现不同的登录失效逻辑。

---

## 9. 性能与包体积约束（必须遵守）

- 小程序包体积控制：禁止把非运行期文件打包进来（`.trae`、文档、技能包等均应忽略）
- 列表必须分页与按需加载：学纪/测评/错题/知识地图都要避免一次性拉全量
- 复杂渲染降级：知识地图默认只渲染一层或两层，深层通过展开加载

---

## 10. 验收清单（实现同学按此逐项自测）

### 10.1 学纪
- 首页可见“最近学纪”模块（可点进详情）
- 学纪页：分页/下拉刷新/空态/错误态齐全
- AI 问答完成后自动新增学纪事件

### 10.2 AI 导师
- Tutor/RAG 模式切换清晰且不混乱
- RAG 引用卡可用，空引用不报错
- 建议问题可点击发送

### 10.3 画像/地图
- 画像页可给出下一步建议（3 条以上）
- 知识地图可折叠，薄弱点可行动（去测评/去错题/去问 AI）

### 10.4 测评
- 完整闭环：开始→作答→提交→结果
- 结果页可以“一键加入错题本”
- 失败可重试且提示清晰

### 10.5 风格一致性
- 所有新增 UI 只使用设计 token 和通用类（card/tag/btn/modal/empty-state）
- 无 emoji 主图标回归、无额外 UI 库风格污染

---

## 11. 给下一棒 AI 的落地建议（执行顺序）

1) 先实现“学纪事件模型 + 学纪列表页”（最小闭环：chat/knowledge/mistake 三类事件）
2) 再补“画像详情 + 知识地图（树形）”并做行动入口联动
3) 最后做“测评中心→测评详情→结果页”，并把结果沉淀到错题本与学纪

以上顺序能保证：每一步都能独立验收，不依赖后端一次性全部完善。

