# NovelSmith 开发路线图

> MVP 阶段：极简向导式 AI 长篇小说生成器

---

## Phase 1：骨架搭建（Codex 构建）

### 后端
- [ ] FastAPI 项目初始化 + SQLite + Alembic
- [ ] JWT 认证 + 邀请码注册
- [ ] AI Provider CRUD（预设模板 + 自定义）
- [ ] 项目/章节/卡片基础 CRUD
- [ ] AI Provider 抽象层（OpenAI 兼容 + Anthropic）
- [ ] 生成引擎：章节大纲 / 正文生成 / 润色 / 扩写
- [ ] 管理员邀请码管理

### 前端
- [ ] Vue 3 + Vite + TypeScript + Pinia 初始化
- [ ] 登录 / 注册页
- [ ] 项目列表页
- [ ] 写作台（Markdown 编辑器 + 参考卡片面板 + AI 工具栏）
- [ ] 卡片库页面
- [ ] 后台设置（AI Providers + 账号 + 邀请码管理）
- [ ] 新建项目向导

### 部署
- [ ] Dockerfile (backend + frontend)
- [ ] docker-compose.yml
- [ ] Nginx 配置
- [ ] 环境变量文档

## Phase 2：核心写作体验打磨
- [ ] 流式输出 (SSE) 逐步展示
- [ ] AI 辅助角色生成
- [ ] 一致性检查
- [ ] 导出功能 (Markdown / EPUB)

## Phase 3：增强
- [ ] 响应式移动端适配
- [ ] 更多卡片类型
- [ ] 模板市场
