# Codex Hermes 开发知识库

本文件是 NovelSmith 内部给 Codex 使用的 Hermes Agent 二次开发索引。以后涉及 Agent Loop、工具调用、模型 Provider、Memory、Skill、Plugin、前端状态流时，先查这里，再进入对应源码或官方文档。

## 官方入口

- 官方文档站：https://hermes-agent.nousresearch.com/docs/
- LLM 索引：https://hermes-agent.nousresearch.com/docs/llms.txt
- LLM 全量文档：https://hermes-agent.nousresearch.com/docs/llms-full.txt
- GitHub 仓库：https://github.com/NousResearch/hermes-agent
- CONTRIBUTING.md：https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md
- AGENTS.md：https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md

本地上游源码位置：

```text
G:\Codex\Curiosity\_upstream\hermes-agent
```

## 本地必读文件

```text
G:\Codex\Curiosity\_upstream\hermes-agent\README.md
G:\Codex\Curiosity\_upstream\hermes-agent\CONTRIBUTING.md
G:\Codex\Curiosity\_upstream\hermes-agent\AGENTS.md
G:\Codex\Curiosity\_upstream\hermes-agent\website\docs\developer-guide\architecture.md
G:\Codex\Curiosity\_upstream\hermes-agent\website\docs\developer-guide\agent-loop.md
G:\Codex\Curiosity\_upstream\hermes-agent\website\docs\developer-guide\prompt-assembly.md
G:\Codex\Curiosity\_upstream\hermes-agent\website\docs\developer-guide\tools-runtime.md
G:\Codex\Curiosity\_upstream\hermes-agent\website\docs\developer-guide\adding-tools.md
G:\Codex\Curiosity\_upstream\hermes-agent\website\docs\developer-guide\creating-skills.md
G:\Codex\Curiosity\_upstream\hermes-agent\website\docs\developer-guide\model-provider-plugin.md
G:\Codex\Curiosity\_upstream\hermes-agent\website\docs\developer-guide\memory-provider-plugin.md
G:\Codex\Curiosity\_upstream\hermes-agent\website\docs\developer-guide\context-engine-plugin.md
G:\Codex\Curiosity\_upstream\hermes-agent\website\docs\developer-guide\plugin-llm-access.md
G:\Codex\Curiosity\_upstream\hermes-agent\website\docs\guides\build-a-hermes-plugin.md
```

## 架构心智模型

Hermes 的核心不是“聊天接口”，而是一个循环：

```text
用户消息
  -> prompt_builder 组装系统提示、Skills、Memory、Context Files
  -> 模型请求，附带可用 tools
  -> 如果模型返回 tool_calls，执行工具并把结果写回消息流
  -> 继续模型循环，直到得到最终回答或达到迭代上限
  -> 持久化会话、记忆、可选技能沉淀
```

NovelSmith 要复刻的是这个 Agent 设计语言，而不是完整移植所有功能。当前重点：

- 右侧对话流承载状态机和工具结果。
- 工具调用必须能影响中间正文编辑器。
- 写入正文使用明确工具，如 `append_to_manuscript`。
- 普通聊天不应强制写作路由。
- 工具调用摘要要展示给用户，不要只显示“已完成”。
- API 未连接时要报错，不要本地假回复。

## 关键源码地图

### Core Agent Loop

```text
run_agent.py
model_tools.py
toolsets.py
tools/registry.py
agent/prompt_builder.py
agent/context_compressor.py
hermes_state.py
```

用途：

- `run_agent.py`：AIAgent 主循环，工具调用迭代、会话持久化。
- `model_tools.py`：工具发现和函数调用分发。
- `tools/registry.py`：工具注册中心，schema、handler、dispatch。
- `toolsets.py`：决定哪些工具暴露给 Agent。
- `agent/prompt_builder.py`：系统提示、Skills、Context、Memory 拼装。
- `hermes_state.py`：SQLite 会话存储、FTS 搜索。

### Skills

```text
skills/
optional-skills/
agent/skill_utils.py
agent/skill_preprocessing.py
agent/skill_commands.py
agent/skill_bundles.py
tools/skill_tools.py
```

开发判断：

- 能用说明文档、shell 命令、已有工具解决的能力，优先做 Skill。
- 需要 API Key、流式事件、二进制数据、严格执行逻辑的能力，才做 Tool。
- 通用能力放 `skills/`；重型、收费、较窄能力放 `optional-skills/`。

### Tools

```text
tools/
tools/registry.py
tools/terminal_tool.py
tools/web_tools.py
tools/delegate_tool.py
tools/code_execution_tool.py
tools/session_search_tool.py
```

Hermes 工具原则：

- 工具自注册，文件加载时调用 registry。
- 工具 schema 与 handler 尽量同文件。
- 工具被注册不等于暴露给 Agent，还要进入 toolset。
- Agent 级工具可能在 `run_agent.py` 里被拦截。

NovelSmith 对应实现：

```text
backend/app/services/agent_runtime.py
```

当前已经有 `append_to_manuscript` 的 OpenAI tools schema。以后新增工具，优先沿用：

```text
工具 schema -> 模型 tool_call -> 后端解析 -> SSE tool_result/manuscript_delta -> 前端气泡和编辑器同步
```

### Providers

```text
providers/
providers/base.py
plugins/model-providers/
hermes_cli/providers.py
hermes_cli/auth.py
```

设计要点：

- Hermes 支持 OpenAI-compatible API，也支持 provider plugin。
- Provider resolution 在初始化阶段完成。
- Provider config 不应硬编码密钥。
- `.env` 放 secrets；`config.yaml` 放非密钥配置。

NovelSmith 当前简化为浏览器 localStorage 的 Provider 配置：

```text
Base URL
Model
API Key
```

后续可以升级为：

- 本地配置文件加密保存。
- Provider preset 列表。
- 模型连通性测试。
- Provider 能力探测：是否支持 `tools`、是否支持 streaming、最大上下文。

### Plugins

```text
plugins/
plugins/model-providers/
plugins/memory/
plugins/context_engine/
plugins/web/
plugins/image_gen/
website/docs/guides/build-a-hermes-plugin.md
```

Hermes 倾向把本地扩展做成插件，减少改核心。新增工具或 provider 时优先走插件路线。

NovelSmith 可以借鉴但不必完全照搬：

- 短期：后端 Python 模块内注册工具。
- 中期：建立 `backend/app/agent_tools/` 注册中心。
- 长期：支持 `plugins/novelsmith-*` 目录，动态发现工具、知识库、Provider。

### Memory

```text
agent/memory_provider.py
plugins/memory/
website/docs/developer-guide/memory-provider-plugin.md
website/docs/user-guide/features/memory.md
```

Hermes 记忆分层：

- 会话历史：当前/历史对话。
- 用户画像：长期偏好。
- 项目上下文：Context Files。
- Procedural memory：Skills。
- Memory Provider：外部记忆后端。

NovelSmith 推荐分层：

- `projectBrief`：作品设定总览。
- `manuscript`：当前正文。
- `chatMessages`：右侧对话记录。
- `world/characters/timeline`：结构化知识库。
- 以后加向量检索或 SQLite FTS，不要一开始把所有内容塞 prompt。

## NovelSmith 二开路线

### 当前 Agent Runtime 应对齐 Hermes 的点

```text
backend/app/services/agent_runtime.py
frontend/src/App.vue
```

需要持续保持：

- 状态通过对话气泡展示。
- 工具调用结果也通过气泡展示。
- 写正文必须通过编辑器工具，而不是普通聊天文本。
- 工具结果要可读：写了多少字、写了什么、写到哪里。
- 模型协议残留必须清洗，例如 thinking/DSML/tool wrapper。
- 未配置 API 时返回错误。

### 下一步建议

1. 建立工具注册中心

```text
backend/app/services/tool_registry.py
backend/app/agent_tools/manuscript.py
backend/app/agent_tools/project_context.py
```

2. 把工具能力注入 prompt

```text
append_to_manuscript
read_project_context
replace_selection
insert_at_cursor
summarize_chapter
update_character_card
```

3. 引入写入审批

```text
模型生成 write proposal
前端显示 diff/摘要
用户确认
后端执行 editor tool
```

4. 引入项目知识库检索

```text
characters
worldbuilding
timeline
chapter_outline
style_guide
```

5. 加 Provider 能力探测

```text
supports_tools
supports_streaming
supports_json_mode
context_window
```

## 开发前检查清单

涉及 Hermes 架构时，Codex 先做：

1. 查本文件定位上游文档和源码。
2. 读对应 Hermes 文档页，不凭空猜架构。
3. 在 NovelSmith 里做最小可运行映射。
4. 保证前端状态气泡和工具结果可读。
5. 跑 `npm run build` 和后端 `py_compile`。
6. 如果改了运行时，重启 `127.0.0.1:8765` 后端。

## 已知差异

NovelSmith 不是完整 Hermes：

- 目前没有完整 `run_agent.py` 式多轮工具循环。
- 目前没有 SQLite 会话库。
- 目前没有 Skill 自动创建。
- 目前没有 Plugin 动态发现。
- 目前 Provider 配置在浏览器端保存，后续需要更安全的本地配置。

这些差异是刻意收敛，不是永久目标。先把写作 Agent 的工具调用体验打通，再逐步补齐 Hermes 式架构。
