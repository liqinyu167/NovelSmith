# Hermes 源码接入记录

本项目参考的上游仓库：

- 仓库：`https://github.com/NousResearch/hermes-agent`
- 当前审计提交：`cae7537359c0ba8fceedc0a6423a4d9f30972100`
- License：MIT

Hermes 是完整的通用 Agent 框架，包含 CLI、TUI、Gateway、多平台消息、MCP、skills hub、credential pool、tool executor、approval gate、context compression、memory manager 等模块。它的源码规模较大，不适合直接整包塞进 NovelSmith。

NovelSmith 会采用“精简封装”的方式迁移 Hermes 架构：

1. 保留：意图路由、状态机、工具注册、审批门控、运行事件、上下文读取。
2. 删除：通用 skills hub、多平台 gateway、TUI、桌面/浏览器/语音/媒体生成等与小说 MVP 无关的模块。
3. 改造：把 Hermes 的通用工具执行模型收敛到小说写作工具，如读取项目记忆、生成写作计划、写入正文、审校一致性、更新角色事实。

当前已落地的 NovelSmith 分层：

- `backend/app/services/hermes_core.py`
  - `AgentDecision`
  - `AgentEvent`
  - `ToolRegistry`
  - `ApprovalGate`
  - `decide_intent`

后续会继续把现有 `agent_runtime.py` 拆分为：

- `intent_router.py`
- `tool_registry.py`
- `approval_runtime.py`
- `memory_runtime.py`
- `writer_runtime.py`

复制或改造 Hermes 源码时必须保留 MIT License 声明。

## Codex 开发知识库

NovelSmith 内部的 Hermes 二次开发知识库已经整理到：

```text
docs/codex-hermes-knowledge.md
```

以后涉及 Agent Loop、工具调用、Provider、Memory、Skill、Plugin、状态气泡、正文编辑工具等开发时，优先阅读该文件，再按其中索引进入上游源码或官方文档。
