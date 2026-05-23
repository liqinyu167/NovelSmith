# NovelSmith

AI 长篇小说创作平台 —— 融合 awesome-novel-studio 的写作管线与 NovelForge 的技术引擎。

## 核心理念

> 把经过出版验证的 AI 写作流程，做成开箱即用的 Web 产品。

- **awesome-novel-studio** → 18 个 Agent 的写作管线，真实签约出版过小说
- **NovelForge** → 结构化生成引擎、知识图谱、记忆系统、工作流编排
- **你的 API** → 接入本地 Grok 或其他 OpenAI 兼容 API

## 快速开始

```bash
# 后端
cd backend
cp .env.example .env
# 编辑 .env 填入你的 API 地址和密钥
pip install -r requirements.txt
python run_backend.py

# 前端
cd frontend
npm install
npm run dev:web
```

## 项目结构

```
NovelSmith/
├── backend/          # Python FastAPI 后端
│   ├── app/          # 应用核心
│   │   ├── api/      # API 路由
│   │   ├── core/     # 配置、启动
│   │   ├── models/   # 数据模型
│   │   ├── services/ # 业务逻辑
│   │   └── workflows/# 工作流引擎
│   ├── alembic/      # 数据库迁移
│   └── requirements.txt
├── frontend/         # Vue 3 + CodeMirror
│   └── src/
│       ├── views/    # 页面
│       ├── components/ # UI 组件
│       ├── stores/   # 状态管理
│       └── api/      # API 调用
└── docs/             # 架构文档
```

## 架构

见 [ARCHITECTURE.md](ARCHITECTURE.md)。
