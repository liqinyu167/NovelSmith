# NovelSmith

NovelSmith 是一个本地优先的 AI 小说写作 Agent 工作台。

它的目标不是做一个普通聊天框，而是把 AI 写作变成可控流程：用户在右侧与总管智能体沟通，中间保留干净的小说正文编辑区，左侧通过汉堡菜单切换正文、大纲、设定、角色、记忆等工作区。

当前 MVP 已打通：

- OpenAI-compatible API 接入
- 普通对话与写作意图识别
- Hermes/Codex 风格的计划卡
- 用户确认后再写入正文
- SSE 流式输出
- 本地 demo 模式
- 正文编辑区缩放

后续方向见 [ROADMAP.md](ROADMAP.md)。

## 本地运行

### 后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8765
```

### 前端

```powershell
cd frontend
npm install
npm run dev
```

打开：

```text
http://localhost:5173
```

## API 配置

当前版本使用 OpenAI-compatible Chat Completions 协议。

可接入示例：

- OpenAI: `https://api.openai.com/v1`
- DeepSeek: `https://api.deepseek.com/v1`
- Ollama: `http://localhost:11434/v1`
- 其他兼容 `/chat/completions` 的中转或本地模型服务

需要配置：

- `Base URL`
- `Model`
- `API Key`

API Key 目前只保存在浏览器 localStorage 中，并在每次请求时发送给本地后端。后续会迁移到后端加密存储。

如果没有配置 API，后端会使用本地 demo 文本，方便测试前端和流式写入链路。

## Agent 工作流

NovelSmith 的总管智能体会先判断用户意图：

- 普通对话：直接在右侧回复，可读取当前项目记忆、正文长度、正文摘录等上下文。
- 写作意图：先生成结构化写作计划卡，等待用户确认。
- 确认写入：用户点击“确认写入”后，后端才调用模型并流式写入中间正文。
- 取消写入：不会修改正文。

这样可以避免 AI 擅自改稿，也让每一次正文变更都有计划、有确认、有过程记录。

## 当前技术栈

- 前端：Vue 3 + Vite + TypeScript
- 后端：FastAPI + httpx
- 通信：REST + Server-Sent Events
- 模型协议：OpenAI-compatible Chat Completions

## 下一步

优先方向：

- SQLite 持久化项目、章节、消息、运行记录
- 工具系统标准化
- 写作记忆与角色卡
- 差异化改写与回滚
- 一致性审校 Agent
- Docker Compose 本地部署
