# NovelSmith 架构文档

> **首席架构师视角** · MVP 阶段 · 极简向导式 AI 长篇小说生成器

---

## 一、产品定位

| 维度 | 说明 |
|------|------|
| **产品** | 在线 AI 长篇小说生成器（Web） |
| **用户** | 作者本人 + 少数朋友（小范围 MVP） |
| **核心理念** | 极简向导式流程，不搞复杂节点编排 |
| **差异化** | awesome-novel-studio 的出版级一致性 × NovelForge 的结构化卡片 |
| **当前阶段** | MVP · 邀请码注册 · 单机或小团队部署 |

---

## 二、系统架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                      用户浏览器 (Vue 3 SPA)                    │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────────────┐   │
│  │ 写作台   │ │ 项目管理  │ │ 卡片库  │ │ 后台设置         │   │
│  │(Markdown)│ │          │ │        │ │ ├ AI 提供商      │   │
│  │         │ │          │ │        │ │ └ 账号设置       │   │
│  └────┬────┘ └────┬─────┘ └───┬────┘ └──────────────────┘   │
└───────┼───────────┼───────────┼─────────────────────────────┘
        │           │           │
┌───────▼───────────▼───────────▼─────────────────────────────┐
│              Nginx 反向代理                                    │
│  / → 前端静态资源                                             │
│  /api → FastAPI 后端                                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   NovelSmith API (FastAPI)                    │
│                                                              │
│  ┌────────────┐ ┌──────────┐ ┌────────────────────────────┐ │
│  │  Auth 模块  │ │ 项目管理  │ │     写作引擎                │ │
│  │ JWT + 邀请码│ │ CRUD     │ │  ├── 章节管理              │ │
│  └────────────┘ └──────────┘ │  ├── 卡片系统 (结构化生成)   │ │
│                              │  └── 记忆/一致性检查         │ │
│  ┌──────────────────────────────────────────────────────┐   │ │
│  │              AI Provider 抽象层                       │   │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │   │ │
│  │  │ OpenAI 兼容   │ │ Anthropic    │ │ 自定义        │  │   │ │
│  │  │ Grok/DeepSeek │ │ Claude       │ │ (预留扩展)    │  │   │ │
│  │  │ Qwen/GLM     │ │              │ │              │  │   │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘  │   │ │
│  └──────────────────────────────────────────────────────┘   │ │
│                                                              │ │
│  ┌──────────────────────────────────────────────────────┐   │ │
│  │              卡片 Schema 注册中心                      │   │ │
│  │  核心卡片：项目设定 | 角色卡片 | 章节大纲 | 段落卡片   │   │ │
│  └──────────────────────────────────────────────────────┘   │ │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                     PostgreSQL / SQLite                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐ │
│  │  users   │ │ projects │ │ chapters │ │     cards      │ │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├────────────────┤ │
│  │invite_codes│ │  project_│ │chapter_ │ │ card_content  │ │
│  │          │ │ settings │ │ versions │ │ (JSON)        │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           ai_providers (用户可配)                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块设计

### 3.1 认证系统

```python
# 核心模型
class User(SQLModel, table=True):
    id: int = primary_key
    email: str = unique
    nickname: str
    password_hash: str
    invite_code: str           # 注册时使用的邀请码
    is_active: bool = True
    created_at: datetime
    last_login: datetime | None

class InviteCode(SQLModel, table=True):
    id: int = primary_key
    code: str = unique          # 邀请码
    created_by: int              # 谁生成的
    used_by: int | None          # 谁用了
    expires_at: datetime
    max_uses: int = 1
```

**流程：**
1. 管理员（你）在后台生成邀请码
2. 朋友拿邀请码注册 → JWT 登录
3. 每个用户数据隔离（project.user_id 外键）

### 3.2 AI Provider 管理

```python
class AIProvider(SQLModel, table=True):
    id: int = primary_key
    user_id: int                 # 每个用户自己配
    name: str                    # 显示名，如"我的 Grok"
    provider_type: str           # openai_compatible | anthropic
    base_url: str                # API 地址
    api_key: str                 # 密钥（加密存储）
    default_model: str           # 默认模型名
    is_active: bool = True
    created_at: datetime

class AIProviderTemplate:
    """预设模板，不入库"""
    id: str                      # grok | deepseek | openai | claude | qwen
    name: str
    provider_type: str
    base_url: str
    default_model: str
```

**预设模板（写死在前端/后端）：**

| 模板 | provider_type | base_url | default_model |
|------|-------------|----------|--------------|
| Grok (你的本地) | openai_compatible | `http://127.0.0.1:8000/v1` | `grok-4.20-fast` |
| DeepSeek | openai_compatible | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | openai_compatible | `https://api.openai.com/v1` | `gpt-4o` |
| Anthropic | anthropic | `https://api.anthropic.com/v1` | `claude-sonnet-4` |
| Qwen | openai_compatible | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |

**多模型分配策略：**
```
初稿生成 → 模型 A（便宜，如 grok-4.20-fast）
润色优化 → 模型 B（更强，如 Claude）
知识抽取 → 模型 A（轻量任务可共用）
```
用户可在后台为不同任务指定不同 Provider。

### 3.3 写作引擎（核心资产）

**向导式流程（不是自由编排，而是引导步骤）：**

```
Step 1: 项目设定
  ├── 小说标题 / 类型（玄幻/科幻/言情...）
  ├── 世界观一句话设定
  └── AI 辅助生成世界观卡片

Step 2: 角色设定
  ├── 手动添加角色
  ├── AI 辅助生成角色卡片（基于世界观）
  └── 角色关系图谱

Step 3: 章节大纲
  ├── 设定总章节数
  ├── 逐章 AI 生成大纲
  └── 手动调整顺序/内容

Step 4: 创作章节
  ├── 选中一章 → AI 生成初稿
  ├── 在 Markdown 编辑器中手动修改
  └── 续写 / 润色 / 扩写

Step 5: 审阅
  ├── 一致性检查（角色名/情节线）
  └── 批量导出
```

### 3.4 卡片系统

```python
class CardSchema(SQLModel, table=True):
    """卡片 Schema 注册表"""
    id: int = primary_key
    name: str                    # project_setting | character | chapter_outline | paragraph
    display_name: str
    schema_json: str             # JSON Schema 定义
    is_builtin: bool = True      # 内置不可删

class Card(SQLModel, table=True):
    id: int = primary_key
    project_id: int
    card_type: str               # 关联 CardSchema.name
    title: str
    content: str                 # 结构化的 JSON 内容
    sort_order: float
    parent_card_id: int | None   # 父子关系（章节→段落）
    created_at: datetime
    updated_at: datetime
```

**核心卡片类型（MVP）：**

| 卡片类型 | 用途 | 生成方式 |
|---------|------|---------|
| `project_setting` | 小说设定 | 创建项目时 AI 辅助 |
| `character` | 角色信息 | 手动 / AI 辅助 |
| `chapter_outline` | 章节大纲 | AI 生成 + 手动调 |
| `paragraph` | 段落正文 | AI 生成长篇正文 |

### 3.5 Markdown 编辑器

- 使用 **CodeMirror 6**（与 NovelForge 一致）或 **md-editor-v3**
- 支持实时预览
- 写作时右侧显示当前章节的参考卡片（角色/设定）

---

## 四、数据库表设计 (MVP)

```
users
├── id (PK)
├── email (UK)
├── nickname
├── password_hash
├── invite_code
├── is_active
├── created_at
└── last_login

invite_codes
├── id (PK)
├── code (UK)
├── created_by (FK → users)
├── used_by (FK → users, nullable)
├── expires_at
└── max_uses

projects
├── id (PK)
├── user_id (FK → users)
├── title
├── genre              # 小说类型
├── world_setting      # 世界观一句话设定（JSON）
├── status             # draft | writing | completed
├── total_chapters
├── created_at
└── updated_at

chapters
├── id (PK)
├── project_id (FK → projects)
├── sort_order
├── title
├── status             # outline | drafting | done | revising
├── word_count
├── created_at
└── updated_at

cards
├── id (PK)
├── project_id (FK → projects)
├── chapter_id (FK → chapters, nullable)
├── card_type          # project_setting | character | chapter_outline | paragraph
├── title
├── content            # JSON
├── sort_order
├── parent_card_id (FK → cards, nullable)
├── created_at
└── updated_at

ai_providers
├── id (PK)
├── user_id (FK → users)
├── name
├── provider_type      # openai_compatible | anthropic
├── base_url
├── api_key            # 加密
├── default_model
├── is_active
├── created_at
└── updated_at

generation_tasks       # 用于跟踪生成状态 + 速率限制
├── id (PK)
├── user_id (FK → users)
├── project_id (FK → projects)
├── card_id (FK → cards, nullable)
├── task_type           # generate_outline | write_chapter | revise | expand
├── model_used
├── prompt_tokens
├── completion_tokens
├── status              # pending | running | done | failed
├── error_message
├── created_at
└── completed_at
```

---

## 五、API 设计

### 认证
```
POST   /api/auth/register        # 邀请码注册
POST   /api/auth/login           # 登录 → JWT
POST   /api/auth/refresh         # 刷新 token
GET    /api/auth/me              # 当前用户信息
```

### 项目
```
GET    /api/projects             # 项目列表
POST   /api/projects             # 新建项目
GET    /api/projects/{id}        # 项目详情
PUT    /api/projects/{id}        # 更新项目
DELETE /api/projects/{id}        # 删除项目
```

### 章节
```
GET    /api/projects/{id}/chapters          # 章节列表
POST   /api/projects/{id}/chapters          # 新建章节
PUT    /api/chapters/{id}                    # 更新章节（标题/排序）
DELETE /api/chapters/{id}                    # 删除章节
POST   /api/chapters/{id}/generate          # AI 生成章节内容
```

### 卡片
```
GET    /api/projects/{id}/cards             # 卡片列表（type 参数过滤）
POST   /api/projects/{id}/cards             # 新建卡片
PUT    /api/cards/{id}                      # 更新卡片
DELETE /api/cards/{id}                      # 删除卡片
POST   /api/cards/{id}/generate            # AI 生成卡片内容
```

### AI 提供商
```
GET    /api/ai/providers                    # 当前用户的提供商列表
POST   /api/ai/providers                    # 添加提供商
PUT    /api/ai/providers/{id}               # 更新
DELETE /api/ai/providers/{id}               # 删除
POST   /api/ai/providers/test              # 测试连接
GET    /api/ai/templates                   # 获取预设模板列表
```

### 邀请码（管理员）
```
GET    /api/admin/invite-codes             # 查看邀请码
POST   /api/admin/invite-codes             # 生成邀请码
DELETE /api/admin/invite-codes/{id}        # 撤销
```

### 写作辅助
```
POST   /api/ai/generate/outline            # 生成章节大纲
POST   /api/ai/generate/chapter            # 生成章节正文
POST   /api/ai/revise/{card_id}            # 润色指定段落
POST   /api/ai/expand/{card_id}            # 扩写指定段落
POST   /api/ai/consistency-check           # 一致性检查
```

---

## 六、前端页面结构

```
/login                  # 登录页
/register               # 注册（需要邀请码）

/                       # 首页 → 项目列表
/projects/new           # 新建项目（向导 Step 1）
/projects/:id           # 项目详情（章节列表）
/projects/:id/settings  # 项目设定卡片

/projects/:id/chapters/:chapterId   # 写作台
  ├── Markdown 编辑器（左/中）
  ├── 参考卡片面板（右侧）
  ├── AI 辅助工具栏（底部）
  └── 章节导航（顶部）

/projects/:id/cards     # 卡片库（角色/设定一览）

/settings               # 后台设置
  ├── AI Providers      # AI 提供商管理
  ├── Account           # 账号信息
  └── Invite Codes      # 邀请码管理（管理员）
```

---

## 七、AI Provider 抽象层设计

```python
# backend/app/services/ai/provider.py

class AIProviderBase(ABC):
    """AI Provider 基类"""
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict | None = None,  # JSON Schema
    ) -> dict:
        ...

class OpenAICompatibleProvider(AIProviderBase):
    """兼容 OpenAI /v1/chat/completions 格式的提供商"""
    def __init__(self, base_url: str, api_key: str, default_model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.session = httpx.AsyncClient(timeout=120)

    async def chat(self, messages, model=None, **kwargs):
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            **kwargs
        }
        resp = await self.session.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload
        )
        return resp.json()

class AnthropicProvider(AIProviderBase):
    """适配 Anthropic /v1/messages 格式"""
    ...

class ProviderFactory:
    """根据 provider_type 创建对应的 Provider 实例"""
    @staticmethod
    def create(provider_config: AIProvider) -> AIProviderBase:
        if provider_config.provider_type == "openai_compatible":
            return OpenAICompatibleProvider(...)
        elif provider_config.provider_type == "anthropic":
            return AnthropicProvider(...)
        raise ValueError(f"Unknown provider type: {provider_config.provider_type}")
```

---

## 八、目录结构

```
NovelSmith/
├── docker-compose.yml          # 一键部署
├── Dockerfile.backend
├── Dockerfile.frontend
│
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── run_backend.py          # 本地启动
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   └── app/
│       ├── __init__.py
│       ├── core/
│       │   ├── config.py       # 配置管理
│       │   ├── security.py     # JWT / 密码
│       │   └── database.py     # 数据库会话
│       ├── models/
│       │   ├── user.py
│       │   ├── project.py
│       │   ├── chapter.py
│       │   ├── card.py
│       │   └── ai_provider.py
│       ├── api/
│       │   ├── deps.py         # 依赖注入（当前用户等）
│       │   ├── router.py       # 路由聚合
│       │   └── endpoints/
│       │       ├── auth.py
│       │       ├── projects.py
│       │       ├── chapters.py
│       │       ├── cards.py
│       │       ├── ai_providers.py
│       │       ├── generation.py
│       │       └── admin.py
│       └── services/
│           ├── ai/
│           │   ├── provider.py       # Provider 抽象
│           │   ├── openai_compat.py  # OpenAI 兼容实现
│           │   ├── anthropic.py      # Anthropic 实现
│           │   └── templates.py      # 预设模板列表
│           ├── generation.py         # 生成业务逻辑
│           ├── card_service.py       # 卡片服务
│           └── consistency.py        # 一致性检查
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── api/                # API 调用封装
│       ├── stores/             # Pinia 状态
│       │   ├── auth.ts
│       │   ├── project.ts
│       │   ├── editor.ts
│       │   └── aiProviders.ts
│       ├── views/
│       │   ├── Login.vue
│       │   ├── Register.vue
│       │   ├── Projects.vue
│       │   ├── ProjectDetail.vue
│       │   ├── ChapterEditor.vue  # 写作台
│       │   ├── Cards.vue
│       │   └── Settings.vue
│       ├── components/
│       │   ├── MarkdownEditor.vue
│       │   ├── CardPanel.vue
│       │   ├── AiToolbar.vue
│       │   └── WizardGuide.vue
│       ├── types/              # TypeScript 类型
│       └── utils/
│
├── .env.example                # 环境变量示例
├── docker-compose.yml
└── scripts/
    ├── seed_invite_codes.py    # 生成初始邀请码
    └── migrate.sh
```

---

## 九、部署方案

### Docker Compose（推荐）

```yaml
services:
  backend:
    build:
      dockerfile: Dockerfile.backend
    ports:
      - "54321:54321"
    env_file: .env
    volumes:
      - ./data:/app/data    # SQLite 持久化

  frontend:
    build:
      dockerfile: Dockerfile.frontend
    ports:
      - "5173:80"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - backend
      - frontend
```

### 你的服务器部署（直接跑，不用 Docker）

```
Nginx → / → 前端 dist 静态文件
      → /api → 反向代理到 127.0.0.1:54321

后端: systemd 管理 FastAPI 进程
数据库: SQLite（初期）
```

### 环境变量

```bash
# 数据库
DATABASE_URL=sqlite:///./data/novelsmith.db  # MVP 用 SQLite

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24h

# 管理员
ADMIN_EMAIL=your@email.com
ADMIN_PASSWORD=your-password

# 可选：默认 AI 提供商（方便预配置）
DEFAULT_AI_BASE_URL=http://127.0.0.1:8000/v1
DEFAULT_AI_API_KEY=liqinyubaidao
DEFAULT_AI_MODEL=grok-4.20-fast
```

---

## 十、风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| AI 输出过长超时 | 用户体验差 | 流式输出 (SSE) + 前端逐步展示 |
| API Key 泄露 | 安全 | 加密存储 + 前端不暴露密钥 |
| SQLite 并发写入 | 多人同时用冲突 | MVP 期用户少，WAL 模式可缓解 |
| 长篇小说上下文超限 | 质量下降 | 卡片摘要递送 + 关键记忆注入 |
| 邀请码被滥用 | 非目标用户涌入 | 限制 IP + 邀请码到期时间 |
| 前端构建太重 | 首次加载慢 | Vite 分包 + 路由懒加载 |

---

## 十一、MVP 开发阶段

### Phase 1: 骨架（Codex 构建）
- 后端：项目初始化 + SQLite + JWT 认证 + AI Provider CRUD
- 前端：登录注册 + 项目列表 + 后台设置页
- 部署：docker-compose + Nginx 配置

### Phase 2: 写作核心
- 卡片系统 + Markdown 编辑器
- AI 生成章节 / 润色 / 扩写
- 向导式流程（项目设定→角色→大纲→创作）

### Phase 3: 增强
- 一致性检查
- 导出功能
- 多人使用打磨
