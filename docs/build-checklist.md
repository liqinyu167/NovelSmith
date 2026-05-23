# NovelSmith 构建清单 (Codex 用)

> 项目: https://github.com/liqinyu167/NovelSmith
>
> 设计题案: (暂无独立文件，参考 README.md 和 ARCHITECTURE.md)
>
> 路线图参考: ROADMAP.md
>
> 架构参考: ARCHITECTURE.md

---

## 一句话启动指令

在 `backend/` 下搭建 FastAPI + SQLite 内核：JWT 邀请码认证 + AI Provider 管理（可配置多模型）+ 项目/章节/卡片 CRUD + 写作引擎（大纲/正文生成/润色/扩写）。前端在 `frontend/` 下搭 Vue 3 + CodeMirror 6 编辑器，UI 风格深色主题 + 紫色强调。先跑通本地内核（不依赖 AI 也能做 CRUD），再接入 AI 能力。详细架构见 ARCHITECTURE.md，阶段划分见 ROADMAP.md。

---

## 后端文件清单

```
backend/
├── main.py                 # FastAPI 入口
├── run_backend.py          # 本地启动脚本
├── requirements.txt        # 依赖
├── alembic.ini
├── alembic/
└── app/
    ├── __init__.py
    ├── core/
    │   ├── config.py       # 配置管理
    │   ├── security.py     # JWT / 密码哈希
    │   └── database.py     # 数据库会话
    ├── models/
    │   ├── user.py
    │   ├── project.py
    │   ├── chapter.py
    │   ├── card.py
    │   └── ai_provider.py
    ├── api/
    │   ├── deps.py         # 依赖注入（当前用户等）
    │   ├── router.py       # 路由聚合
    │   └── endpoints/
    │       ├── auth.py
    │       ├── projects.py
    │       ├── chapters.py
    │       ├── cards.py
    │       ├── ai_providers.py
    │       ├── generation.py
    │       └── admin.py
    └── services/
        ├── ai/
        │   ├── provider.py       # Provider 抽象基类
        │   ├── openai_compat.py  # OpenAI 兼容实现
        │   ├── anthropic.py      # Anthropic 实现
        │   └── templates.py      # 预设模板列表
        ├── generation.py         # 生成业务逻辑
        ├── card_service.py       # 卡片服务
        └── consistency.py        # 一致性检查
```

## 前端文件清单

```
frontend/
└── src/
    ├── App.vue
    ├── main.ts
    ├── router/
    │   └── index.ts
    ├── stores/
    │   ├── auth.ts
    │   ├── project.ts
    │   └── editor.ts
    ├── api/
    │   ├── client.ts      # axios 封装 + JWT 拦截器
    │   └── endpoints.ts   # API 调用
    ├── views/
    │   ├── LoginView.vue
    │   ├── RegisterView.vue
    │   ├── ProjectsView.vue
    │   ├── ProjectDetail.vue
    │   ├── WriterView.vue      # 写作台（核心）
    │   ├── CardsView.vue
    │   └── SettingsView.vue
    ├── components/
    │   ├── MarkdownEditor.vue  # CodeMirror 6
    │   ├── ReferencePanel.vue  # 参考卡片侧栏
    │   ├── AIToolbar.vue      # AI 操作栏
    │   └── ...
    └── assets/
        └── styles/
            └── main.css       # 深色主题
```

## 构建顺序建议

```
Day 1:  backend 骨架 — main.py + config + database + models
Day 2:  认证 — JWT + 邀请码注册/登录 API
Day 3:  核心 CRUD — 项目/章节/卡片 API
Day 4:  AI Provider 管理 + 预设模板 + 测试连接
Day 5:  写作引擎 — 大纲/正文/润色/扩写服务
Day 6:  frontend 骨架 — Vue 3 + Vite + router + stores
Day 7:  登录/注册/项目列表页
Day 8:  写作台 — CodeMirror 编辑器 + 参考面板 + AI 工具栏
Day 9:  卡片库 + 设置页
Day 10: 联调 + docker-compose + 部署
```
