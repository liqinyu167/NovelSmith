# NovelSmith 架构文档

## 整体架构

```
┌─────────────────────────────────────────────────┐
│                  用户浏览器                        │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              Nginx 反向代理                       │
│  / → 前端静态文件 (dist-web/)                    │
│  /api → FastAPI 后端                             │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              NovelSmith 后端                      │
│              Python FastAPI                       │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ 项目/章节 │  │ 卡片生成  │  │  工作流引擎     │ │
│  │   CRUD    │  │ JSON Schema│  │  (ANS Agent管线)│ │
│  └──────────┘  └──────────┘  └────────────────┘ │
│  ┌────────────────┐  ┌────────────────────┐     │
│  │  知识图谱       │  │  记忆系统           │     │
│  │  (SQLite KG)   │  │  (跨章节持久化)     │     │
│  └────────────────┘  └────────────────────┘     │
│  ┌──────────────────────────────────────────┐   │
│  │    AI Provider 抽象层                     │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐  │   │
│  │  │OpenAI│ │Grok  │ │Claude│ │自定义  │  │   │
│  │  │兼容  │ │(你的)│ │      │ │        │  │   │
│  │  └──────┘ └──────┘ └──────┘ └────────┘  │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              SQLite (无 Neo4j)                    │
│  ├── novelforge.db (项目/章节/卡片)              │
│  └── knowledge.db (知识图谱/记忆)                │
└─────────────────────────────────────────────────┘
```

## 分层说明

### 1. 前端 (Vue 3 + CodeMirror)

基于 NovelForge 的现有前端，去掉 Electron 专有代码，使用其 Web 构建配置 (`vite.config.web.ts`)。

| 页面 | 功能 |
|------|------|
| 写作台 | 主编辑器，支持卡片式创作 |
| 项目列表 | 管理多部小说 |
| 知识图谱 | 可视化角色/情节关系 |
| 工作流 | 选择/配置写作管线 |
| **后台设置** | **AI 提供商管理** |

### 2. 后台设置 —— AI 提供商管理

用户可在此配置 AI API：

**预设模板：**
| 模板名 | base_url | 请求格式 | 适用 |
|--------|----------|---------|------|
| OpenAI 兼容 | 自定义 | `/v1/chat/completions` | Grok、DeepSeek、GLM 等 |
| Anthropic | 自定义 | `/v1/messages` | Claude |
| Google | 自定义 | (Gemini SDK) | Gemini |

**关键设计：**
- 支持**多模型分配**：初稿用 grok-4.20-fast，润色用 Claude，知识抽取用同一个
- 配置存 SQLite，不存前端 localStorage
- 默认预制你的 Grok2API 配置
- 测试连接按钮验证 API 可用性

### 3. 工作流引擎 (来自 awesome-novel-studio)

把 ANS 的 18 个 Agent 管线化：

```
1. domain-researcher      → 领域调研
2. character-architect    → 角色架构
3. character-sculptor     → 角色细化
4. concept-builder        → 世界观构建
5. plot-hook-engineer     → 情节钩子
6. proposal-generator     → 章节提案
7. episode-architect      → 章节架构
8. episode-creator        → 章节创作
9. episode-rewriter       → 章节重写
10. continuity-bridge     → 连续性桥接
11. quality-verifier      → 质量审核
12. revision-analyst      → 修改分析
13. revision-executor     → 修改执行
14. revision-reviewer     → 修改复核
15. platform-optimizer    → 平台优化
16. rule-checker          → 规则检查
17. story-analyst         → 故事分析
18. alive-enhancer        → 活力增强
```

### 4. 结构化生成 (来自 NovelForge)

每个写作阶段用 JSON Schema 约束 AI 输出，保证：
- 角色卡片有统一的字段（姓名、性格、动机、弧光...）
- 章节大纲有固定的结构
- 知识图谱节点有标准格式

### 5. 知识图谱 (SQLite, 无 Neo4j)

NovelForge 已实现 SQLite-based KG，配置 `KNOWLEDGE_GRAPH_PROVIDER=sqlite` 即可。

追踪内容：
- 角色关系网
- 伏笔与呼应
- 剧情时间线
- 物品/地点关联

## AI 请求流程

```
用户写了一段 → 触发某个工作流节点
                   ↓
工作流引擎 → 组装 prompt（含当前章节+知识图谱上下文）
                   ↓
            AI Provider 层 → 调用配置的 API
                   ↓
            结构化 JSON 返回 → 存入数据库
                   ↓
            更新知识图谱 → 返回前端展示
```

## 使用你的 Grok2API

默认配置（后台可修改）：
```
API地址: http://127.0.0.1:8000/v1
API密钥: liqinyubaidao
模型: grok-4.20-fast
初稿用: grok-4.20-fast (便宜)
润色用: (可选配置其他)
```

## 技术栈

| 层 | 技术 | 来源 |
|----|------|------|
| 后端框架 | Python FastAPI | NovelForge |
| 数据库 | SQLite + SQLModel | NovelForge |
| 数据库迁移 | Alembic | NovelForge |
| AI 编排 | LangChain（可选） | NovelForge |
| 结构化生成 | JSON Schema / Pydantic | NovelForge |
| 工作流引擎 | 可视化节点编排 | NovelForge |
| 写作管线 | 18 Agent 流程 | awesome-novel-studio |
| 前端框架 | Vue 3 + Element Plus | NovelForge |
| 编辑器 | CodeMirror | NovelForge |
| 知识图谱 | SQLite (不依赖 Neo4j) | NovelForge |
