# 小程序端 API 接口需求清单

本文档汇总了小程序端（微信小程序）需要从 PC 端服务器获取的所有数据接口。每次迭代后须同步更新此文档。

- 基础地址：`http://127.0.0.1:8000/api`（开发环境，见 `utils/request.js`）
- 正式建议地址：`https://gezhisystem.com/api`
- 鉴权方式：`Authorization: Bearer <token>`（401 时自动清理登录态并重定向）
- 请求封装：`utils/request.js`
- 对齐标准：`C:\Users\36257\Desktop\方案A-小程序接口数据样例.md`
- 统一响应：`ApiResponse<T>`，即 `{ "code": 0, "message": "ok", "data": T }`
- 统一分页：`{ "items": [], "nextCursor": null }`
- 统一时间：ISO 字符串（如 `2026-07-08T10:30:00Z`）

---

## 目录

1. [认证模块](#1-认证模块)
2. [学情画像模块](#2-学情画像模块)
3. [AI 导师模块](#3-ai-导师模块)
4. [学纪事件模块](#4-学纪事件模块)
5. [知识库模块](#5-知识库模块)
6. [错题本模块](#6-错题本模块)
7. [测评模块](#7-测评模块)
8. [论坛模块](#8-论坛模块)

---

## 1. 认证模块

### 1.1 学子登录

| 项目 | 值 |
|------|-----|
| 路径 | `POST /api/student/login` |
| 调用页面 | `pages/login/index.js` |
| 是否已有 | ✅ 已实现 |

**请求体：**
```json
{
  "username": "24001020106",
  "password": "123456",
  "role": "student"
}
```

**预期响应（ApiResponse 解包前）：**
```json
{
  "code": 0,
  "message": "login success",
  "data": {
    "token": "jwt_token_string",
    "user": {
      "username": "24001020106",
      "role": "student",
      "realName": "张华",
      "real_name": "张华",
      "studentId": "24001020106",
      "student_id": "24001020106",
      "className": "计科2301",
      "class_name": "计科2301",
      "avatarUrl": "",
      "avatar_url": ""
    }
  }
}
```

---

## 2. 学情画像模块

### 2.1 获取学生画像详情

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/profile/{userId}` |
| 调用页面 | `pages/home/index.js`、`pages/profile/index.js` |
| 是否已有 | ✅ 已实现 |

**预期响应（StudentProfile）：**
```json
{
  "user_id": "24001020106",
  "name": "张华",
  "class_name": "计科2301",
  "avatar_url": "",
  "behavior": {
    "knowledge": 72,
    "cognitive": "渐进理解型",
    "pace": 65,
    "goal": "掌握核心数据结构与算法"
  }
}
```

**调用方读取字段：**
- `profile.knowledge` → 知识掌握度分数
- `profile.cognitive` → 认知风格标签
- `profile.pace` → 学习节奏指数
- `profile.goal` → 学习目标
- `profile.name` / `profile.class_name` → 展示用

### 2.2 获取画像概要（新增）

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/profile/summary` |
| 调用页面 | `pages/portrait/index.js`（通过 `journal-service.js`） |
| 是否已有 | ❌ 待实现 |

**预期响应：**
```json
{
  "userId": "24001020106",
  "knowledgeScore": 72,
  "paceScore": 65,
  "cognitiveStyle": "渐进理解型",
  "goal": "掌握核心数据结构与算法",
  "level": "致知境",
  "updatedAt": "2026-07-08T10:00:00Z"
}
```

### 2.3 获取画像趋势（新增）

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/profile/trends?range=7d\|30d` |
| 调用页面 | `pages/portrait/index.js`（通过 `journal-service.js`） |
| 是否已有 | ❌ 待实现 |

**参数：**
- `range`：`7d`（最近7天）或 `30d`（最近30天）

**预期响应：**
```json
{
  "knowledge": [
    { "date": "2026-07-01", "value": 65 },
    { "date": "2026-07-02", "value": 68 }
  ],
  "pace": [
    { "date": "2026-07-01", "value": 60 },
    { "date": "2026-07-02", "value": 63 }
  ]
}
```

### 2.4 获取知识地图（新增）

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/profile/knowledge-map?rootId=&depth=` |
| 调用页面 | `pages/portrait/index.js`、`pages/knowledge-map/index.js`（通过 `journal-service.js`） |
| 是否已有 | ❌ 待实现 |

**参数：**
- `rootId`：可选，指定根节点
- `depth`：可选，展开深度（默认 3）

**预期响应（树形结构）：**
```json
{
  "id": "root",
  "name": "数据结构",
  "mastery": 72,
  "status": "ok",
  "children": [
    {
      "id": "ds_tree",
      "name": "树与二叉树",
      "parentId": "root",
      "mastery": 45,
      "status": "weak",
      "relatedMistakeCount": 3,
      "recommendedActions": [
        { "type": "quiz", "label": "做专项测评" },
        { "type": "ask_ai", "label": "问 AI 导师" }
      ],
      "children": [
        {
          "id": "ds_btree_traverse",
          "name": "二叉树遍历",
          "parentId": "ds_tree",
          "mastery": 38,
          "status": "weak",
          "relatedMistakeCount": 2,
          "recommendedActions": []
        }
      ]
    },
    {
      "id": "ds_graph",
      "name": "图论",
      "parentId": "root",
      "mastery": 85,
      "status": "strong",
      "children": []
    }
  ]
}
```

**字段说明：**
- `status`：`weak`（<60）/ `ok`（60-80）/ `strong`（>80）
- `recommendedActions`：前端展示为操作按钮，`type` 决定跳转目标

### 2.5 记录自测结果到画像

| 项目 | 值 |
|------|-----|
| 路径 | `POST /api/profile/record_test` |
| 调用页面 | `pages/mistake-book/index.js` |
| 是否已有 | ✅ 已实现 |

**请求体：**
```json
{
  "user_id": "24001020106",
  "problem_id": "mistake_test_xxx",
  "category": "数据结构",
  "status": "passed",
  "difficulty": "Easy",
  "error_msg": null
}
```

### 2.6 教师干预提醒

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/analytics/interactions` |
| 调用页面 | `pages/home/index.js` |
| 是否已有 | ✅ 已实现 |

**预期响应：** 数组，每项含 `type`、`message`、`createdAt` 等字段。

---

## 3. AI 导师模块

### 3.1 获取聊天历史

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/chat/history?session_id=&agent_mode=&limit=` |
| 调用页面 | `pages/chat/index.js` |
| 是否已有 | ✅ 已实现 |

**参数：**
- `session_id`：用户标识（当前用 username）
- `agent_mode`：`tutor` 或 `rag`
- `limit`：消息条数（默认 50）

**预期响应：**
```json
{
  "status": "success",
  "data": [
    {
      "id": "msg_001",
      "role": "assistant",
      "content": "你好！我是你的主规划师 Alina。",
      "sender_id": "agent_tutor",
      "created_at": "2026-07-08T10:00:00Z"
    }
  ]
}
```

### 3.2 发送消息（AI 问答）

| 项目 | 值 |
|------|-----|
| 路径 | `POST /api/chat` |
| 调用页面 | `pages/chat/index.js` |
| 是否已有 | ✅ 已实现 |

**请求体：**
```json
{
  "message": "二叉树的前序遍历和中序遍历有什么区别？",
  "agent_mode": "tutor",
  "sessionId": "24001020106",
  "thread_id": "24001020106"
}
```

**预期响应（非流式）：**
```json
{
  "reply": "前序遍历的顺序是：根节点 → 左子树 → 右子树..."
}
```

**建议增强（NextUp）：** 响应中增加 `references` 和 `suggestedQuestions` 字段：
```json
{
  "reply": "...",
  "references": [
    { "docId": "doc_001", "docName": "数据结构教程_第6章.pdf", "chunkId": "c01", "quote": "前序遍历定义..." }
  ],
  "suggestedQuestions": ["中序遍历的应用场景是什么？", "如何用栈实现非递归遍历？"]
}
```

---

## 4. 学纪事件模块（新增）

### 4.1 创建学纪事件

| 项目 | 值 |
|------|-----|
| 路径 | `POST /api/journal/events` |
| 调用页面 | `pages/chat/index.js`、`pages/mistake-book/index.js`、`pages/knowledge-base/index.js`、`pages/evaluator-detail/index.js`（通过 `journal-service.js`） |
| 是否已有 | ❌ 待实现 |

**请求体：**
```json
{
  "type": "chat",
  "title": "AI问答: 二叉树的前序遍历...",
  "summary": "前序遍历的顺序是：根节点→左子树→右子树...",
  "relatedIds": ["msg_001"],
  "tags": ["数据结构"],
  "scoreDelta": 2
}
```

**`type` 枚举值：**
- `chat`：AI Tutor 问答
- `rag`：RAG 课件问答
- `mistake`：错题操作（新增/掌握）
- `quiz`：测评提交
- `knowledge_upload`：课件上传向量化
- `forum`：论坛发帖/回复（预留）
- `profile_update`：画像更新（预留）

**预期响应：**
```json
{
  "id": "evt_001",
  "type": "chat",
  "title": "AI问答: 二叉树的前序遍历...",
  "createdAt": "2026-07-08T10:30:00Z"
}
```

### 4.2 获取学纪事件列表（分页）

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/journal/events?cursor=&limit=&type=` |
| 调用页面 | `pages/journal/index.js`、`pages/home/index.js`（通过 `journal-service.js`） |
| 是否已有 | ❌ 待实现 |

**参数：**
- `cursor`：分页游标（可选）
- `limit`：每页条数（默认 20）
- `type`：按类型筛选（可选）

**预期响应：**
```json
{
  "items": [
    {
      "id": "evt_001",
      "type": "chat",
      "title": "AI问答: 二叉树遍历区别",
      "summary": "前序遍历是根→左→右...",
      "tags": ["数据结构"],
      "scoreDelta": 2,
      "createdAt": "2026-07-08T10:30:00Z"
    }
  ],
  "nextCursor": "evt_000"
}
```

### 4.3 按日期获取学纪事件

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/journal/events/day?date=YYYY-MM-DD` |
| 调用页面 | `pages/journal-detail/index.js`（通过 `journal-service.js`） |
| 是否已有 | ❌ 待实现 |

---

## 5. 知识库模块

### 5.1 获取用户知识库

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/user/knowledge?user_id=` |
| 调用页面 | `pages/knowledge-base/index.js` |
| 是否已有 | ✅ 已实现 |

**预期响应：**
```json
{
  "repositories": [
    { "id": "repo_001", "name": "数据结构" }
  ],
  "documents": [
    {
      "id": "doc_001",
      "name": "数据结构教程_第6章.pdf",
      "repository_id": "repo_001",
      "size": 262144,
      "status": "success"
    }
  ]
}
```

### 5.2 新建知识库分类

| 项目 | 值 |
|------|-----|
| 路径 | `POST /api/user/knowledge/repositories` |
| 调用页面 | `pages/knowledge-base/index.js` |
| 是否已有 | ✅ 已实现 |

**请求体：**
```json
{
  "user_id": "24001020106",
  "name": "高等数学"
}
```

### 5.3 删除知识库文档

| 项目 | 值 |
|------|-----|
| 路径 | `DELETE /api/user/knowledge/documents/{id}?user_id=` |
| 调用页面 | `pages/knowledge-base/index.js` |
| 是否已有 | ✅ 已实现 |

### 5.4 上传文件并向量化

| 项目 | 值 |
|------|-----|
| 路径 | `POST /api/user/knowledge/upload`（`multipart/form-data`） |
| 调用页面 | `pages/knowledge-base/index.js` |
| 是否已有 | ✅ 已实现 |

**请求体：**
- `file`：文件二进制（支持 pdf/doc/docx/txt）
- `user_id`：用户标识
- `repository_id`：所属分类 ID

---

## 6. 错题本模块

### 6.1 获取学生错题列表

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/exams/student/{userId}/mistakes` |
| 调用页面 | `pages/mistake-book/index.js`、`pages/profile/index.js` |
| 是否已有 | ✅ 已实现 |

**预期响应：**
```json
{
  "mistakes": [
    {
      "id": "m_001",
      "problem": "手写双向链表节点删除逻辑",
      "answer": "...",
      "category": "数据结构",
      "mastered": false,
      "aiAnalysis": null
    }
  ],
  "summary": {
    "total": 8,
    "unresolved": 5
  }
}
```

### 6.2 AI 诊断错题

| 项目 | 值 |
|------|-----|
| 路径 | `POST /api/exams/mistakes/{id}/ai-analysis` |
| 调用页面 | `pages/mistake-book/index.js` |
| 是否已有 | ✅ 已实现 |

**预期响应：**
```json
{
  "diagnosis": "未正确区分 prev 指针与当前节点的边界情况...",
  "suggested_fix": "建议先检查 cur.next 是否为 null..."
}
```

### 6.3 切换错题掌握状态

| 项目 | 值 |
|------|-----|
| 路径 | `PATCH /api/exams/mistakes/{id}` |
| 调用页面 | `pages/mistake-book/index.js` |
| 是否已有 | ✅ 已实现 |

**请求体：**
```json
{
  "mastered": true
}
```

### 6.4 新增错题（从测评沉淀）

| 项目 | 值 |
|------|-----|
| 路径 | `POST /api/exams/mistakes` |
| 调用页面 | `pages/evaluator-result/index.js` |
| 是否已有 | ❌ 待实现 |

**请求体：**
```json
{
  "question": "二叉树前序遍历顺序是？",
  "answer": "根→左→右",
  "source": "quiz",
  "quizId": "quiz_001"
}
```

---

## 7. 测评模块（新增）

### 7.1 获取测评列表

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/evaluator/quizzes?tag=&difficulty=&cursor=&limit=` |
| 调用页面 | `pages/evaluator/index.js` |
| 是否已有 | ❌ 待实现 |

**参数：**
- `tag`：知识点标签筛选（可选）
- `difficulty`：难度 1-5（可选）
- `cursor`：分页游标（可选）
- `limit`：每页条数（可选）

**预期响应：**
```json
{
  "items": [
    {
      "id": "quiz_001",
      "title": "二叉树专项测评",
      "topicTags": ["数据结构", "二叉树"],
      "difficulty": 3,
      "questionCount": 10,
      "estimatedMinutes": 15
    }
  ],
  "nextCursor": "quiz_000"
}
```

### 7.2 创建/开始测评

| 项目 | 值 |
|------|-----|
| 路径 | `POST /api/evaluator/attempts` |
| 调用页面 | `pages/evaluator/index.js` |
| 是否已有 | ❌ 待实现 |

**请求体：**
```json
{
  "quizId": "quiz_001"
}
```

**预期响应：**
```json
{
  "id": "attempt_001",
  "quizId": "quiz_001",
  "status": "in_progress",
  "createdAt": "2026-07-08T10:00:00Z"
}
```

### 7.3 获取测评详情（含题目）

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/evaluator/attempts/{id}` |
| 调用页面 | `pages/evaluator-detail/index.js` |
| 是否已有 | ❌ 待实现 |

**预期响应：**
```json
{
  "id": "attempt_001",
  "quizId": "quiz_001",
  "title": "二叉树专项测评",
  "topicTags": ["数据结构", "二叉树"],
  "status": "in_progress",
  "questions": [
    {
      "id": "q_001",
      "type": "choice",
      "content": "二叉树前序遍历的顺序是？",
      "options": [
        { "key": "A", "text": "根→左→右" },
        { "key": "B", "text": "左→根→右" },
        { "key": "C", "text": "左→右→根" },
        { "key": "D", "text": "根→右→左" }
      ]
    },
    {
      "id": "q_002",
      "type": "judge",
      "content": "满二叉树一定是完全二叉树。"
    },
    {
      "id": "q_003",
      "type": "fill",
      "content": "二叉树的第 i 层最多有 ____ 个节点。"
    },
    {
      "id": "q_004",
      "type": "short",
      "content": "请简述二叉树中序遍历的递归算法。"
    }
  ]
}
```

**题目类型：**
- `choice`：单选题（需 `options` 数组）
- `judge`：判断题
- `fill`：填空题
- `short`：简答题

### 7.4 提交测评

| 项目 | 值 |
|------|-----|
| 路径 | `POST /api/evaluator/attempts/{id}/submit` |
| 调用页面 | `pages/evaluator-detail/index.js` |
| 是否已有 | ❌ 待实现 |

**请求体：**
```json
{
  "answers": {
    "q_001": "A",
    "q_002": true,
    "q_003": "2^(i-1)",
    "q_004": "中序遍历先递归左子树，再访问根节点，最后递归右子树。"
  }
}
```

### 7.5 获取测评结果

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/evaluator/attempts/{id}/result` |
| 调用页面 | `pages/evaluator-result/index.js` |
| 是否已有 | ❌ 待实现 |

**预期响应：**
```json
{
  "attemptId": "attempt_001",
  "quizId": "quiz_001",
  "title": "二叉树专项测评",
  "score": 75,
  "totalQuestions": 10,
  "correctCount": 7,
  "timeTaken": "12:30",
  "weakTags": ["二叉树遍历", "平衡树"],
  "questions": [
    {
      "id": "q_001",
      "content": "二叉树前序遍历的顺序是？",
      "type": "choice",
      "userAnswer": "A",
      "correctAnswer": "A",
      "isCorrect": true,
      "explanation": "前序遍历的定义就是根→左→右。"
    },
    {
      "id": "q_002",
      "content": "满二叉树一定是完全二叉树。",
      "type": "judge",
      "userAnswer": false,
      "correctAnswer": true,
      "isCorrect": false,
      "explanation": "满二叉树每一层都填满，当然是完全二叉树的特例。"
    }
  ]
}
```

---

## 8. 论坛模块

### 8.1 获取帖子列表

| 项目 | 值 |
|------|-----|
| 路径 | `GET /api/forum/posts` |
| 调用页面 | `pages/course/index.js`、`pages/forum-detail/index.js` |
| 是否已有 | ✅ 已实现 |

**预期响应：** 数组，每项含 `id`、`title`、`content`、`category`、`author`、`avatar`、`createdAt`、`replies[]`、`views`、`likes` 等字段。

### 8.2 提交帖子回复

| 项目 | 值 |
|------|-----|
| 路径 | `POST /api/forum/posts/{postId}/replies` |
| 调用页面 | `pages/forum-detail/index.js` |
| 是否已有 | ✅ 已实现 |

**请求体：**
```json
{
  "author": "张华",
  "avatar": "",
  "isAi": false,
  "content": "我的理解是..."
}
```

---

## 接口总览（快速索引）

| # | 方法 | 路径 | 状态 | 调用方 |
|---|------|------|------|--------|
| 1 | POST | `/api/student/login` | ✅ 已有 | login |
| 2 | GET | `/api/profile/{userId}` | ✅ 已有 | home, profile |
| 3 | GET | `/api/profile/summary` | ❌ 新增 | portrait |
| 4 | GET | `/api/profile/trends?range=` | ❌ 新增 | portrait |
| 5 | GET | `/api/profile/knowledge-map` | ❌ 新增 | portrait, knowledge-map |
| 6 | POST | `/api/profile/record_test` | ✅ 已有 | mistake-book |
| 7 | GET | `/api/analytics/interactions` | ✅ 已有 | home |
| 8 | GET | `/api/chat/history` | ✅ 已有 | chat |
| 9 | POST | `/api/chat` | ✅ 已有 | chat |
| 10 | POST | `/api/journal/events` | ❌ 新增 | chat, mistake-book, knowledge-base, evaluator-detail |
| 11 | GET | `/api/journal/events` | ❌ 新增 | journal, home |
| 12 | GET | `/api/journal/events/day` | ❌ 新增 | journal-detail |
| 13 | GET | `/api/user/knowledge` | ✅ 已有 | knowledge-base |
| 14 | POST | `/api/user/knowledge/repositories` | ✅ 已有 | knowledge-base |
| 15 | DELETE | `/api/user/knowledge/documents/{id}` | ✅ 已有 | knowledge-base |
| 16 | POST | `/api/user/knowledge/upload` | ✅ 已有 | knowledge-base |
| 17 | GET | `/api/exams/student/{userId}/mistakes` | ✅ 已有 | mistake-book, profile |
| 18 | POST | `/api/exams/mistakes/{id}/ai-analysis` | ✅ 已有 | mistake-book |
| 19 | PATCH | `/api/exams/mistakes/{id}` | ✅ 已有 | mistake-book |
| 20 | POST | `/api/exams/mistakes` | ❌ 新增 | evaluator-result |
| 21 | GET | `/api/evaluator/quizzes` | ❌ 新增 | evaluator |
| 22 | POST | `/api/evaluator/attempts` | ❌ 新增 | evaluator |
| 23 | GET | `/api/evaluator/attempts/{id}` | ❌ 新增 | evaluator-detail |
| 24 | POST | `/api/evaluator/attempts/{id}/submit` | ❌ 新增 | evaluator-detail |
| 25 | GET | `/api/evaluator/attempts/{id}/result` | ❌ 新增 | evaluator-result |
| 26 | GET | `/api/forum/posts` | ✅ 已有 | course, forum-detail |
| 27 | POST | `/api/forum/posts/{id}/replies` | ✅ 已有 | forum-detail |

**统计：已有 14 个 ✅ | 待实现 13 个 ❌**

---

## 更新日志

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-07-08 | v1.1 | 对齐方案A：统一 ApiResponse<T>、分页 items/nextCursor、ISO 时间、正式域名建议；前端 request 已统一解包 |
| 2026-07-08 | v1.0 | 初始版本：覆盖认证、画像、AI导师、学纪、知识库、错题本、测评、论坛全部接口 |
