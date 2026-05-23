# 开发规划

## Phase 1：基础设施搭建 (Codex 构建)

### 1.1 后端骨架
- [ ] FastAPI 项目初始化 (基于 NovelForge 的 backend/)
- [ ] SQLite 数据库 + SQLModel 模型
- [ ] Alembic 迁移
- [ ] AI Provider 后台管理 CRUD
- [ ] LangChain 多模型适配层

### 1.2 前端骨架
- [ ] Vue 3 + Element Plus 项目初始化
- [ ] Web 构建配置 (改造已有的 vite.config.web.ts)
- [ ] 后台设置页面 (AI 提供商管理 UI)
- [ ] 写作台基础布局

### 1.3 部署
- [ ] Nginx 配置
- [ ] systemd 服务
- [ ] 环境变量配置

## Phase 2：核心功能

### 2.1 写作引擎
- [ ] 卡片系统 (章节/角色/大纲)
- [ ] CodeMirror 编辑器集成
- [ ] 结构化 JSON Schema 生成

### 2.2 工作流
- [ ] 导入 ANS 的 3-5 个核心 Agent prompt
- [ ] 工作流节点编排
- [ ] 状态持久化

### 2.3 知识图谱
- [ ] SQLite KG 初始化
- [ ] 角色关系追踪
- [ ] 伏笔管理

## Phase 3：增强

- [ ] 全部 18 个 Agent prompt 导入
- [ ] 多项目支持
- [ ] 导出功能
- [ ] 模板市场
