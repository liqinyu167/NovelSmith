# NovelSmith

NovelSmith 是一个本地优先的 AI 小说写作 Agent 工作台。

它的目标不是做一个普通的聊天框，而是将 AI 写作转化为可控的、结构化的工作流：用户在右侧面板与总管智能体（Director Agent）沟通，中间保留干净的小说正文与卡片编辑器，左侧则集成了可视化文件树和卡片知识库（设定、角色、记忆等工作区）。

---

## 🌟 核心特色与 v2.0 重构成果

在最新的 **v2.0 架构升级**中，NovelSmith 完成了向模块化和自主型 Agent 写作架构的演进：

1. **一键拉起启动**：新增了 `start_novelsmith.bat` 一键脚本，可同时拉起前端及后端服务。
2. **多层级文件工作区 (V2)**：左侧面板集成了全新的可视化 Workspace 树，支持多文件、多章节以及设定卡片的快速新建、修改、删除和本地目录管理，打破了传统的单文本限制。
3. **Hermes 模块化工具注册中心**：重构了后端工具调用逻辑（对齐 HermesAgent 规范），所有 Agent 行为均通过 `agent_tools/registry.py` 标准化注册，目前包括：
   - `workspace` 工具集：读取和修改项目中的任意文件。
   - `manuscript` 工具集：正文精准写入、光标定位插入等。
   - `knowledge` 工具集：加载与搜寻小说背景知识、人物背景卡等。
4. **设计重构蓝图**：沉淀了完整的系统级大改题案 [`OVERHAUL_PROPOSAL.md`](OVERHAUL_PROPOSAL.md)，深度参考 InkOS（多 Agent 审核关卡）、awesome-novel-studio（命令与 Pipeline）、NovelForge（Schema 卡片与 @DSL 注入）的思想，指导了后续的全面演进。

---

## 🚀 快速启动

你可以使用一键启动脚本，或分别手动拉起服务。

### 方式一：一键启动（推荐）

在 Windows 环境下，直接双击根目录下的：
```text
start_novelsmith.bat
```
它会自动在后台打开两个命令行窗口，分别拉起后端服务 (Uvicorn, 8765 端口) 和前端服务 (Vite, 5173 端口)。

打开浏览器访问：
```text
http://localhost:5173
```

---

### 方式二：手动分步启动

#### 1. 后端服务

首次运行请先安装虚拟环境与依赖：
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
然后启动 Uvicorn 开发者服务器：
```powershell
uvicorn app.main:app --reload --port 8765
```

#### 2. 前端服务

首次运行需安装 npm 依赖：
```powershell
cd frontend
npm install
```
然后启动 Vite 服务：
```powershell
npm run dev
```

---

## ⚙️ 模型与 API 配置

当前版本使用 OpenAI-compatible Chat Completions 协议，支持多种大语言模型。

### 兼容模型推荐：
* **OpenAI**: `https://api.openai.com/v1`
* **DeepSeek**: `https://api.deepseek.com/v1`
* **Ollama**: `http://localhost:11434/v1` (推荐本地部署的 qwen2.5 / llama3 系列模型)
* 以及其他兼容 `/chat/completions` 的国产或本地大模型。

### 参数配置项：
1. 点击系统右上角的设置图标（齿轮）打开配置面板。
2. 配置 `Base URL`、`Model` 及 `API Key`。
3. *注：API Key 目前仅保存在本地浏览器的 `localStorage` 中，并在流式请求时发送给本地后端服务，不会上传到任何第三方云服务器。*

*如果没有配置 API，系统会降级为**演示模式 (Demo Mode)**，提供内置的小说章节及流式写入交互流程，方便测试。*

---

## 🛠️ 下一步开发路标

详情请查看 [`ROADMAP.md`](ROADMAP.md)，后续演进重点包括：

* [ ] **Agent 角色选择器 (AgentRole)**：支持 General, Writer, Designer, Editor, Auditor 等多角色，切换不同 Prompt 和工具集。
* [ ] **斜杠命令 (Slash Commands)**：在输入框使用 `/write`, `/design`, `/polish`, `/audit` 等快捷路由。
* [ ] **@DSL 卡片精准引用**：允许在右侧输入框使用 `@角色.xxx` 自动注入对应卡片字段到 LLM 上下文中。
* [ ] **正文 Diff 预览写入**：在智能体修改正文时，先以 Diff 高亮形式呈现，经人类审查并“接受/拒绝”后再写回文件。
* [ ] **SQLite 数据持久化**：管理项目历史消息流、运行记录与审核日志。
