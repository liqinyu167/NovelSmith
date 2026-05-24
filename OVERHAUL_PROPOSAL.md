# NovelSmith 大改题案 v2.0
> 参考 InkOS / awesome-novel-studio / NovelForge，结合 HermesAgent 架构的系统性升级方案

**文档日期：** 2026-05-24  
**状态：** 草案，待评审  
**优先级标注：** 🔴 高 / 🟡 中 / 🟢 低

---

## 一、现状分析

### 1.1 当前架构

```
frontend/src/
├── App.vue                    # 顶层组合：3 列布局
├── components/
│   ├── KnowledgePanel.vue     # 左栏：文件树 + 知识库
│   ├── EditorArea.vue         # 中栏：正文编辑器（Markdown + 卡片）
│   ├── AgentPanel.vue         # 右栏：对话气泡 + 工具调用显示
│   ├── ChatMessage.vue        # 单条气泡渲染
│   ├── FileTree.vue           # 文件树组件
│   ├── TopBar.vue             # 顶部栏（书名 + 配置入口）
│   └── PanelResizer.vue       # 面板拖拽分割线
├── composables/
│   ├── useAgent.ts            # Agent 主循环、SSE 流
│   ├── useChat.ts             # 消息列表、状态机
│   ├── useEditor.ts           # 正文、字数、滚轮缩放
│   ├── useKnowledge.ts        # 知识库（章节列表等）
│   ├── useLayout.ts           # 面板宽度、拖拽
│   ├── useSettings.ts         # Provider 配置、projectBrief
│   └── useWorkspace.ts        # 文件读写、文件树
backend/app/
├── main.py                    # FastAPI 路由
├── api/                       # RESTful 路由层
└── services/
    └── agent_runtime.py       # Agent 核心（tool_calls + SSE）
```

### 1.2 当前优势

| 能力 | 现状 |
|------|------|
| 布局 | 3 列拖拽分割，设计语言成熟 |
| 流式输出 | SSE + EventSource，气泡逐字渲染 |
| 工具调用 | `append_to_manuscript` / `update_workspace_file` |
| 写入确认流 | Plan → 确认 → 执行，已有基础 |
| 文件管理 | 左侧文件树，支持 Markdown 浏览 |

### 1.3 当前痛点 / 缺口

| 编号 | 问题 | 影响 |
|------|------|------|
| G-01 | 工具注册中心不完整，工具难以扩展 | Agent 能力无法横向生长 |
| G-02 | 右侧 Agent 只有一种对话模式，缺乏角色/功能路由 | 无法区分"写作 Agent"vs"编辑 Agent"vs"审核 Agent" |
| G-03 | 无角色卡片 / 世界观卡片系统 | 长篇一致性崩溃 |
| G-04 | 无 Pipeline 概念（提案→设计→写作→润色→审核） | 用户完全手动驱动 |
| G-05 | 无上下文注入 DSL | Agent 无法精准引用卡片内容 |
| G-06 | 无工作流系统 | 无法自动化创作流程 |
| G-07 | Memory 层单一（仅 projectBrief + manuscript） | 长章节上下文溢出 |
| G-08 | 无审核 / Audit 流 | 质量控制全靠用户 |
| G-09 | Provider 配置仅 localStorage，无能力探测 | 工具调用模型兼容性未知 |

---

## 二、三大开源项目精华提取

### 2.1 InkOS（自主多 Agent 小说写作）

**核心亮点：**
- **人工审核关卡（Human Review Gates）**：Agent 写完章节后，强制暂停等待人类确认，不自动连续跑完全书
- **多 Agent 协作**：Writer → Auditor → Reviser 分工，不同 Agent 专注不同任务
- **自主性**：Agent 有计划-执行-反思循环，不仅仅是"问一答一"

**我们要借鉴的：**
1. 审核关卡机制（已有 `pendingConfirm` 雏形，需强化）
2. Agent 角色路由：根据任务类型选派不同提示词

### 2.2 awesome-novel-studio（18 专家 Agent + 10 技能）

**核心亮点：**

| 功能 | 说明 |
|------|------|
| `/propose` | 生成 3 个小说提案，用户选一个 |
| `/design-big` | 全书设计（世界观 + 角色 + 情节钩子） |
| `/design-small` | 25 集详细设计 |
| `/create` | 逐集写作 |
| `/polish` | 4 轴润色（VOICE / TITLE / ALIVE / LOGIC） |
| 连续性桥接 | 每集开始自动注入前 2 集的时间线/伏笔/角色状态 |
| 角色音表 | 语气、句尾词、肢体语言模板，每集自动校验 |
| guard_rails | 数字/时间线守护规则 |

**我们要借鉴的：**
1. Slash 命令体系（`/propose`, `/design`, `/create`, `/polish`）→ 映射到 Agent 技能
2. "三堵墙"解法（角色崩塌 / 故事崩溃 / 数字错误）→ 连续性 Agent + 审核 Agent
3. 全书流水线概念 → Pipeline 状态机

### 2.3 NovelForge（卡片 + Schema + 工作流）

**核心亮点：**

| 功能 | 说明 |
|------|------|
| Schema 驱动卡片 | 每类卡片有结构定义，AI 生成时字段级校验 |
| @DSL 上下文注入 | `@角色.王小明` 精准引用卡片字段 |
| 代码式工作流 | Python 风格语句，顺序/等待/异步，比 DAG 更 AI 友好 |
| 工作流 Agent | 用自然语言写/改工作流代码 |
| 灵感工作台 | 自由卡片，跨项目引用，不干扰正式项目 |
| 连续性审核 | 生成前预览，确认后写回 |
| 字数控制双模式 | Prompt 约束 vs 多轮预算控制 |

**我们要借鉴的：**
1. 卡片系统（角色卡、世界观卡、章节提纲卡）→ 左侧面板增加卡片区
2. @DSL 注入 → Agent prompt 组装时自动展开
3. 工作流基础架构 → 后端 Python 代码式任务链
4. 字数控制双模式 → 生成参数面板

---

## 三、大改方向总览

### 3.1 设计语言约束（不动的部分）

> **铁律：3 列布局（左-知识库、中-编辑器、右-Agent）的视觉框架不变。**
> 所有新功能必须在这三个区域内扩展，或以浮层/抽屉形式叠加，不改变主骨架。

具体不变内容：
- TopBar 固定在顶部
- 左侧 KnowledgePanel 文件树样式
- 中间 EditorArea 的纸张式编辑器
- 右侧 AgentPanel 的气泡聊天流
- PanelResizer 的拖拽分割条
- 整体深色/暗色主题调色板（`styles.css` 中的 CSS 变量体系）

---

### 3.2 升级全景图

```
┌──────────────────────────────────────────────────────────────────────┐
│  TopBar: [书名] [Pipeline 进度指示器]   [Model 状态] [设置]          │
├────────────┬─────────────────────────────────┬───────────────────────┤
│            │                                 │                       │
│ 左侧面板   │      中间编辑区                 │    右侧 Agent 面板    │
│ ──────── │ ──────────────────────────────│ ─────────────────── │
│ [文件树]  │  [纸张编辑器]                   │  [Agent 角色选择器]   │
│           │  ↑ 现有功能保留                 │  [斜杠命令快捷栏]     │
│ [卡片库]  │                                 │  [气泡对话流]         │
│ ├角色卡   │  [字数/进度统计]                │  [工具调用摘要]       │
│ ├世界观卡 │                                 │  [确认/拒绝操作卡]    │
│ ├章节提纲 │  [章节 Diff 预览层]             │  [工作流状态栏]       │
│ └审核记录 │  (写入前对比，可接受/拒绝)      │                       │
│           │                                 │  [输入框 + 发送]      │
└────────────┴─────────────────────────────────┴───────────────────────┘
```

---

## 四、具体改造方案（按优先级）

---

### 🔴 P0：工具注册中心重构（Hermes 对齐）

**目标：** 后端工具从硬编码散落变为结构化注册，新增工具只需一个文件。

**参考：** Hermes `tools/registry.py` + `toolsets.py`

**新增文件：**
```
backend/app/
├── agent_tools/
│   ├── __init__.py
│   ├── registry.py          # 工具注册中心
│   ├── manuscript.py        # append_to_manuscript, replace_selection, insert_at_cursor
│   ├── workspace.py         # update_workspace_file, read_workspace_file, list_workspace
│   ├── knowledge.py         # read_project_context, search_knowledge, update_card
│   ├── chapter.py           # summarize_chapter, get_chapter_outline
│   └── audit.py             # create_audit_record, get_audit_history
```

**registry.py 接口设计：**
```python
# backend/app/agent_tools/registry.py
from typing import Callable, Any

_registry: dict[str, dict] = {}

def register_tool(name: str, description: str, parameters: dict):
    """装饰器：注册工具 schema"""
    def decorator(fn: Callable):
        _registry[name] = {
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            },
            "handler": fn
        }
        return fn
    return decorator

def get_toolset(names: list[str]) -> list[dict]:
    """返回指定名称的工具 schema 列表"""
    return [_registry[n]["schema"] for n in names if n in _registry]

async def dispatch(name: str, args: dict, context: Any) -> Any:
    """派发工具调用"""
    if name not in _registry:
        raise ValueError(f"Unknown tool: {name}")
    return await _registry[name]["handler"](args, context)
```

**工具调用链路（对齐 Hermes）：**
```
用户消息
  → agent_runtime.py 组装 system prompt + tools schema
  → 模型返回 tool_calls
  → registry.dispatch(name, args, context)
  → 工具执行，返回 result
  → SSE 推送 tool_result 事件
  → 前端 handleChatEvent 更新气泡 + 编辑器
```

**前端工具结果展示增强（useAgent.ts）：**

每种工具调用结果都应该在气泡流里有可读摘要：

| 工具 | 当前 | 改为 |
|------|------|------|
| `append_to_manuscript` | "写入约 N 字" | "已写入第 X 章：[摘要前 50 字]…" |
| `update_workspace_file` | "修改了文件" | "已更新 角色卡/王小明.md → 年龄:25→26" |
| `read_project_context` | 沉默 | "读取了项目上下文（世界观 + 3 个角色卡）" |
| `create_audit_record` | 无 | "审核完成：[章节] PASS/ISSUES [N 项问题]" |

---

### 🔴 P0：Agent 角色路由系统

**目标：** 右侧 AgentPanel 支持切换"Agent 角色"，不同角色有不同系统提示词和工具集。

**参考：** InkOS 的多 Agent 分工 + awesome-novel-studio 的专家 Agent

**Agent 角色定义（6 种）：**

```typescript
// frontend/src/types.ts 新增
export type AgentRole = 
  | "general"      // 通用助手（当前默认）
  | "writer"       // 写作 Agent：专注正文续写，工具：append_to_manuscript, replace_selection
  | "designer"     // 设计 Agent：世界观/角色/提纲，工具：update_card, create_card
  | "editor"       // 编辑 Agent：润色/扩写，工具：replace_selection, insert_at_cursor  
  | "auditor"      // 审核 Agent：章节质量，工具：create_audit_record
  | "workflow"     // 工作流 Agent：生成/修改工作流代码
```

**右侧面板顶部增加角色选择器：**

```
┌─────────────────────────────────────────────┐
│  Agent   [通用 ▾] [写作] [设计] [编辑] [审核] │
│  当前：写作 Agent · 专注正文续写              │
└─────────────────────────────────────────────┘
```

设计约束：角色选择器用现有的 CSS 变量体系设计，用小标签形式，不改变整体布局高度。

**后端路由对应：**
```python
# backend/app/api/agent.py
@router.post("/api/agent/chats")
async def create_chat(req: ChatRequest):
    role = req.agent_role or "general"
    system_prompt = build_system_prompt(role, req)
    tools = get_toolset_for_role(role)
    ...

def get_toolset_for_role(role: str) -> list[dict]:
    mapping = {
        "general":  ["read_project_context", "append_to_manuscript", "update_workspace_file"],
        "writer":   ["read_project_context", "append_to_manuscript", "replace_selection", 
                     "insert_at_cursor", "get_chapter_outline"],
        "designer": ["read_project_context", "update_card", "create_card", "list_workspace"],
        "editor":   ["read_project_context", "replace_selection", "insert_at_cursor"],
        "auditor":  ["read_project_context", "create_audit_record", "get_audit_history"],
        "workflow": ["read_project_context", "list_workspace"],
    }
    return get_toolset(mapping.get(role, mapping["general"]))
```

---

### 🔴 P0：Slash 命令体系（awesome-novel-studio 借鉴）

**目标：** 右侧输入框支持 `/` 触发命令，Agent 识别并路由到对应 Pipeline 步骤。

**参考：** awesome-novel-studio 的完整 Pipeline 命令

**命令列表：**

| 命令 | 说明 | 映射 Agent 角色 |
|------|------|----------------|
| `/propose` | 生成 3 个小说提案（类型/世界观/主角） | 设计 Agent |
| `/design` | 全书大设计（世界观+角色+情节架构） | 设计 Agent |
| `/outline [N集]` | 生成 N 集详细提纲 | 设计 Agent |
| `/write` | 续写当前章节正文 | 写作 Agent |
| `/write [N字]` | 续写指定字数 | 写作 Agent |
| `/polish` | 对选中文本润色（VOICE/LOGIC/FLOW） | 编辑 Agent |
| `/expand` | 扩写选中段落 | 编辑 Agent |
| `/audit` | 审核当前章节（连续性+角色一致性） | 审核 Agent |
| `/card [类型] [名称]` | 创建指定类型卡片 | 设计 Agent |
| `/bridge` | 生成连续性桥接（当前章回顾摘要） | 写作 Agent |
| `/help` | 显示命令列表 | 通用 |

**前端实现（AgentPanel.vue 输入框）：**
```typescript
// 输入框监听 / 触发命令面板
const slashCommands = [
  { cmd: '/propose',  label: '生成提案',    icon: '💡', role: 'designer' },
  { cmd: '/design',   label: '全书设计',    icon: '🗺️', role: 'designer' },
  { cmd: '/outline',  label: '章节提纲',    icon: '📋', role: 'designer' },
  { cmd: '/write',    label: '续写正文',    icon: '✍️', role: 'writer'   },
  { cmd: '/polish',   label: '润色文字',    icon: '✨', role: 'editor'   },
  { cmd: '/audit',    label: '审核章节',    icon: '🔍', role: 'auditor'  },
  { cmd: '/bridge',   label: '连续性桥接',  icon: '🌉', role: 'writer'   },
  { cmd: '/card',     label: '创建卡片',    icon: '📇', role: 'designer' },
]
// 当用户输入 "/" 时，弹出命令浮层（绝对定位，不影响布局）
```

**后端接收斜杠命令并解析：**
```python
# backend/app/services/command_parser.py
SLASH_COMMANDS = {
    "/propose": {"role": "designer", "skill": "novel_proposal"},
    "/design":  {"role": "designer", "skill": "full_design"},
    "/outline": {"role": "designer", "skill": "episode_outline"},
    "/write":   {"role": "writer",   "skill": "chapter_write"},
    "/polish":  {"role": "editor",   "skill": "text_polish"},
    "/audit":   {"role": "auditor",  "skill": "chapter_audit"},
    "/bridge":  {"role": "writer",   "skill": "continuity_bridge"},
}

def parse_slash_command(prompt: str) -> dict | None:
    for cmd, meta in SLASH_COMMANDS.items():
        if prompt.strip().lower().startswith(cmd):
            args = prompt[len(cmd):].strip()
            return {**meta, "args": args, "original": prompt}
    return None
```

---

### 🟡 P1：左侧面板升级——卡片库（NovelForge 借鉴）

**目标：** 左侧 KnowledgePanel 在文件树下方增加"卡片库"区域，支持角色/世界观/章节提纲等结构化卡片。

**设计约束：** 卡片库是文件树的下方折叠区，不替换文件树，二者共存。

**卡片类型（v1 范围）：**

```typescript
// 新增 CardType
export type CardType = 
  | "character"   // 角色卡
  | "worldview"   // 世界观卡
  | "location"    // 场景卡
  | "outline"     // 章节提纲卡
  | "audit"       // 审核结果卡
```

**角色卡 Schema（对齐 NovelForge Schema-first）：**
```json
{
  "type": "character",
  "name": "王小明",
  "fields": {
    "age": 25,
    "identity": "特工/伪装成快递员",
    "voice_pattern": "简洁、不废话、偶尔冷幽默",
    "sentence_endings": ["。", "？", "..."],
    "physical_tags": ["左手腕旧伤", "总是戴帽子"],
    "current_arc": "卧底任务第三阶段",
    "alive": true,
    "last_appeared": "第十二章"
  }
}
```

**左侧面板新布局（KnowledgePanel.vue）：**
```
┌─────────────────────────────────┐
│  📁 文件树                [+] [⊡]│  ← 现有功能保留
│  ├ 第一章.md                     │
│  └ ...                          │
├─────────────────────────────────┤
│  📇 卡片库              [+] [▾] │  ← 新增折叠区
│  ├ 👤 角色 (3)                   │
│  │  ├ 王小明                     │
│  │  └ 李萌                       │
│  ├ 🌍 世界观 (1)                  │
│  ├ 📍 场景 (2)                    │
│  └ 📋 提纲 (1)                   │
└─────────────────────────────────┘
```

**卡片 CRUD 路由（后端）：**
```
POST   /api/cards                    # 创建卡片
GET    /api/cards?type=character     # 列表
GET    /api/cards/{id}               # 详情
PUT    /api/cards/{id}               # 更新
DELETE /api/cards/{id}               # 删除
GET    /api/cards/{id}/history       # 审核历史
```

**存储：** SQLite（卡片表），后期可对接 workspace 文件系统（卡片 ↔ .json 文件双向同步）。

---

### 🟡 P1：@DSL 上下文注入（NovelForge 借鉴）

**目标：** 在 Agent prompt 组装时，自动展开 `@` 引用，将卡片内容注入上下文，无需用户手动粘贴。

**参考：** NovelForge 的 `@DSL` 精准引用

**语法设计：**
```
@角色.王小明           → 展开完整角色卡 JSON
@角色.王小明.voice    → 仅展开 voice_pattern 字段
@世界观.修真体系       → 展开世界观卡
@提纲.第一章           → 展开章节提纲卡
@前N章                 → 最近 N 章摘要（连续性桥接）
@当前章               → 当前正文内容
```

**前端输入框集成：**
- 用户在右侧输入框输入 `@` 时，弹出卡片选择浮层
- 选中后插入 `@角色.王小明` 标记
- 发送前由 prompt 预处理器展开

**后端展开逻辑（prompt_builder.py）：**
```python
# backend/app/services/prompt_builder.py
import re

DSL_PATTERN = re.compile(r'@(角色|世界观|场景|提纲|前(\d+)章|当前章)\.?([^\s,，。]*)?')

async def expand_dsl(prompt: str, project_id: str, db) -> str:
    """展开 @DSL 引用，将卡片内容嵌入 prompt"""
    matches = DSL_PATTERN.finditer(prompt)
    expansions = {}
    for m in matches:
        tag = m.group(0)
        card_type = m.group(1)
        card_name = m.group(3)
        content = await fetch_card_content(card_type, card_name, project_id, db)
        expansions[tag] = content
    for tag, content in expansions.items():
        prompt = prompt.replace(tag, f"\n[{tag}]\n{content}\n[/{tag}]\n")
    return prompt
```

---

### 🟡 P1：连续性桥接系统（awesome-novel-studio 借鉴）

**目标：** 每次写作前，自动注入"前 N 章的关键信息摘要"，防止角色崩塌和情节断裂。

**参考：** awesome-novel-studio 的 `continuity-bridge`

**桥接内容包含：**
1. 时间线：最近 N 章的事件序列
2. 伏笔追踪：已埋未解的伏笔列表
3. 角色状态：主要角色的当前情绪/位置/目标
4. 数字约束：货币、年龄、日期等需要一致的数字

**实现：**
```python
# backend/app/services/continuity_bridge.py
async def build_continuity_bridge(
    chapters: list[str],  # 最近 N 章正文
    character_cards: list[dict],
    n: int = 2
) -> str:
    """调用 LLM 提取并格式化连续性信息"""
    recent = chapters[-n:]
    # 构建提取 prompt，返回结构化 JSON
    bridge = await llm_extract_bridge(recent, character_cards)
    return format_bridge_to_markdown(bridge)
```

**触发时机：**
- 用户执行 `/write` 命令时自动注入
- 用户执行 `/audit` 时作为对比基准
- 可在设置中关闭（对短篇小说无需）

---

### 🟡 P1：审核 Agent 流（InkOS 借鉴）

**目标：** 每写完一章，可以触发 Auditor Agent 进行质量审核，结果记录在卡片库中。

**参考：** InkOS 的人工审核关卡 + NovelForge 的审核结果卡片

**审核 4 轴（对齐 awesome-novel-studio 的 VOICE/TITLE/ALIVE/LOGIC）：**

| 审核轴 | 说明 | 检查项 |
|--------|------|--------|
| VOICE | 角色声音一致性 | 对白语气是否符合角色音表 |
| ALIVE | 角色状态一致性 | 已死亡角色是否出现、角色当前目标是否符合 |
| LOGIC | 情节逻辑 | 因果链、时间线、数字一致性 |
| FLOW  | 叙事流畅度 | 节奏、过渡、场景切换 |

**审核流程：**
```
用户执行 /audit 或 Agent 自动触发
  → 审核 Agent 读取当前章节 + 角色卡 + 前 2 章桥接
  → 按 4 轴生成审核草稿
  → 前端显示"审核预览"浮层（不是气泡，是独立面板）
  → 用户确认 → 写入审核结果卡片（存 SQLite）
  → 气泡显示审核摘要
```

**审核结果卡 Schema：**
```json
{
  "type": "audit",
  "chapter": "第十二章",
  "timestamp": "2026-05-24T10:00:00",
  "axes": {
    "VOICE": {"score": 8, "issues": []},
    "ALIVE": {"score": 10, "issues": []},
    "LOGIC": {"score": 7, "issues": ["第3段：时间矛盾，应是'第二天'而非'当天'"]},
    "FLOW": {"score": 9, "issues": []}
  },
  "overall": "PASS",
  "suggestions": [...]
}
```

---

### 🟡 P1：章节 Diff 写入预览（NovelForge 借鉴）

**目标：** Agent 写入正文前，中间编辑区显示 Diff 预览，用户可接受/拒绝/局部接受。

**参考：** NovelForge 的"草稿预览 → 确认保存"流程

**当前状态：** 已有 `pendingPlan` + 确认/取消按钮（在气泡里）。

**升级方向：**

1. **Diff 视图集成到 EditorArea：** 当 `isAwaitingConfirm` 为 true，EditorArea 切换到 Diff 模式，绿色高亮新增内容，红色划线删除内容。
2. **操作卡从气泡移到编辑区头部：** 确认/拒绝按钮显示在编辑区顶部固定工具栏，气泡保留摘要文字。
3. **局部接受：** 用户可以选中 Diff 中的某段文字"只接受这段"。

```typescript
// EditorArea.vue 新增 diff 模式
interface DiffLine {
  type: 'context' | 'added' | 'removed'
  content: string
}

const diffLines = computed<DiffLine[]>(() => {
  if (!props.pendingContent) return []
  return computeDiff(props.manuscript, props.pendingContent)
})
```

---

### 🟢 P2：工作流基础架构（NovelForge 借鉴）

**目标：** 支持用代码式语句定义自动化写作流程（如：新建项目→生成世界观→生成角色→写第一章）。

**参考：** NovelForge 的代码式工作流

**v1 极简范围（不做 DAG，直接做线性任务链）：**

```python
# 工作流定义格式（YAML）
name: "网文快速开局"
steps:
  - skill: novel_proposal   # 生成 3 个提案
    wait_confirm: true       # 等待用户选择
  - skill: full_design       # 全书大设计
    wait_confirm: false
  - skill: episode_outline   # 生成前 25 集提纲
    args: {episodes: 25}
    wait_confirm: true
  - skill: chapter_write     # 写第一章
    wait_confirm: true
```

**工作流状态栏（右侧 AgentPanel 底部小条）：**
```
┌─────────────────────────────────────────────┐
│  ⚡ 工作流：网文快速开局                     │
│  ● 生成提案 ✓  ● 全书设计 ⏳  ○ 写提纲  ○ 写作 │
│  [暂停] [中止]                               │
└─────────────────────────────────────────────┘
```

---

### 🟢 P2：Pipeline 进度指示器（TopBar）

**目标：** TopBar 增加轻量进度指示，让用户知道当前在全书创作的哪个阶段。

**阶段定义（5 段）：**

```
[提案] → [设计] → [提纲] → [创作] → [润色]
  ○          ○         ○         ⏳         ○
```

- 点击任意阶段 → 跳转到对应 slash 命令提示
- 显示方式：TopBar 右侧轻量标签，不占大面积

---

### 🟢 P2：Provider 能力探测（Hermes 架构对齐）

**目标：** 配置 Provider 时，自动检测模型是否支持 tool_calls、streaming、JSON mode。

**参考：** Hermes 的 `supports_tools` / `supports_streaming` 能力探测

**实现：**
```python
# backend/app/services/provider_probe.py
async def probe_provider(base_url: str, model: str, api_key: str) -> dict:
    """探测 Provider 能力"""
    caps = {
        "supports_streaming": False,
        "supports_tools": False,
        "supports_json_mode": False,
        "context_window": None
    }
    # 1. 测试 streaming 连接
    # 2. 发一个带 tools 的 dummy 请求，看是否报错
    # 3. 发 json_mode 请求
    return caps
```

**前端配置对话框增加"测试连接"按钮：**
- 点击 → 后端 probe → 返回能力标记
- 如果 `supports_tools: false` → 显示警告：当前模型不支持工具调用，Agent 功能受限
- 自动降级：对不支持 tools 的模型，使用 ReAct 文本格式模拟工具调用（参考 NovelForge 的 ReAct 模式）

---

### 🟢 P2：Memory 层分层（Hermes 架构对齐）

**目标：** 避免把所有内容堆进 system prompt，实现按需注入。

**参考：** Hermes 的多层记忆架构

**分层设计：**

```
Level 1（始终注入）：
  - projectBrief（作品设定总览，<500 token）
  - 当前角色卡摘要（仅主要角色，<200 token）

Level 2（按需注入，由 Agent 工具调用触发）：
  - read_project_context → 详细世界观/角色
  - get_chapter_outline → 章节提纲
  - search_knowledge(query) → 向量搜索（后期）

Level 3（连续性桥接，写作时注入）：
  - build_continuity_bridge → 前 N 章摘要
```

**好处：**
- 短对话（聊天模式）：只有 Level 1，节省 token
- 写作模式：自动注入 Level 1 + 3
- 深度设计模式：Level 1 + Agent 主动调用 Level 2

---

## 五、技术路线与落地次序

### 5.1 迭代计划

| 迭代 | 重点 | 预估工作量 | 成果验证 |
|------|------|-----------|----------|
| v2.0.0 | 工具注册中心 + Agent 角色路由 | 3-4 天 | 切换 Agent 角色后工具调用验证 |
| v2.1.0 | Slash 命令 + `/write` `/polish` | 2-3 天 | 命令弹层正常触发，写作流程跑通 |
| v2.2.0 | 卡片库（左侧面板）+ 卡片 CRUD API | 4-5 天 | 创建角色卡，Agent 可读取 |
| v2.3.0 | @DSL 注入 + 连续性桥接 | 3-4 天 | @角色.xxx 在 prompt 中正确展开 |
| v2.4.0 | 审核 Agent + 审核结果卡 | 3-4 天 | `/audit` 产出审核记录 |
| v2.5.0 | Diff 预览写入 | 2-3 天 | EditorArea 显示 Diff，可接受/拒绝 |
| v2.6.0 | Provider 探测 + ReAct 降级 | 2-3 天 | 非 tools 模型可用 |
| v2.7.0 | Pipeline 进度 + 工作流 v1 | 3-4 天 | TopBar 进度可视，YAML 工作流可跑 |

### 5.2 文件变更地图

#### 新增文件

```
backend/app/
├── agent_tools/
│   ├── __init__.py
│   ├── registry.py
│   ├── manuscript.py
│   ├── workspace.py
│   ├── knowledge.py
│   ├── chapter.py
│   └── audit.py
├── services/
│   ├── command_parser.py      # Slash 命令解析
│   ├── prompt_builder.py      # DSL 展开 + prompt 组装
│   ├── continuity_bridge.py   # 连续性桥接
│   ├── provider_probe.py      # Provider 能力探测
│   └── workflow_runner.py     # 工作流执行引擎
├── models/
│   └── card.py                # SQLAlchemy Card 模型
└── api/
    ├── cards.py               # 卡片 CRUD 路由
    └── workflow.py            # 工作流 API

frontend/src/
├── components/
│   ├── CardPanel.vue          # 卡片库面板（嵌入 KnowledgePanel）
│   ├── CardEditor.vue         # 卡片编辑浮层
│   ├── SlashCommandPicker.vue # 斜杠命令弹层
│   ├── AgentRolePicker.vue    # Agent 角色切换器
│   ├── DiffPreview.vue        # Diff 预览层（嵌入 EditorArea）
│   ├── AuditResultCard.vue    # 审核结果气泡
│   └── WorkflowStatusBar.vue  # 工作流状态条
└── composables/
    ├── useCards.ts            # 卡片库状态
    ├── useSlashCommands.ts    # 命令解析
    └── useWorkflow.ts         # 工作流状态
```

#### 修改文件（最小影响原则）

```
frontend/src/
├── types.ts                   # 新增 AgentRole, CardType, AuditResult 等类型
├── App.vue                    # 注入 useCards, useSlashCommands
├── components/
│   ├── KnowledgePanel.vue     # 底部追加 CardPanel 区域
│   ├── AgentPanel.vue         # 顶部追加 AgentRolePicker + SlashCommandPicker
│   └── EditorArea.vue         # 顶部追加 DiffPreview + Diff 工具栏
└── composables/
    └── useAgent.ts            # 传入 agentRole，增加 @DSL 展开

backend/app/
├── main.py                    # 注册新路由
├── api/agent.py               # 接入角色路由 + command_parser
└── services/agent_runtime.py  # 接入 registry.dispatch + prompt_builder
```

---

## 六、Hermes 架构对齐检查表

参照 `docs/codex-hermes-knowledge.md`，逐项对齐：

| Hermes 能力 | 当前 NovelSmith | v2.0 目标 |
|------------|----------------|-----------|
| Tool Registry | 分散在 agent_runtime.py | `agent_tools/registry.py` 统一注册 |
| Toolsets（角色化工具集） | 无 | 按 AgentRole 动态组装工具集 |
| Skills | 无 | Slash 命令 = 技能路由 |
| Memory 分层 | 单层 projectBrief | Level 1/2/3 按需注入 |
| Provider 能力探测 | 无 | `provider_probe.py` |
| Plugin 体系 | 无 | 预留 `plugins/novelsmith-*` 目录结构 |
| 工具调用摘要 | 简单 | 每种工具可读化摘要 |
| 写入确认流 | 基础版 | Diff 预览 + 局部接受 |
| ReAct 降级 | 无 | 非 tools 模型兼容 |
| Agent Loop 多轮 | 单轮 | 审核 Agent 支持多轮审改 |

---

## 七、不做的事（范围控制）

为了维持前端设计语言的稳定性，以下功能在此次大改中**不纳入**：

| 不做项 | 原因 |
|--------|------|
| 重写 3 列布局框架 | 成熟设计不动 |
| 替换 Vue + Vite 技术栈 | 无必要 |
| 引入 Neo4j 知识图谱 | SQLite 够用，后期升级 |
| 完整 DAG 工作流编辑器 | 代码式工作流先行 |
| 移动端适配 | 当前以 PC 为主 |
| 多人协作 / 云同步 | 本地优先，后期扩展 |
| 完整向量检索 | 全文搜索优先，向量后期 |

---

## 八、风险与缓解

| 风险 | 可能性 | 影响 | 缓解策略 |
|------|--------|------|----------|
| 卡片系统 API 接口设计不稳定，前后端频繁联调 | 中 | 中 | 先定 TypeScript 类型，后端跟着对齐 |
| DSL 展开后 prompt 过长触发 context 限制 | 中 | 高 | 展开时做 token 预算，超出时截断 + 警告 |
| 审核 Agent 产出不稳定（格式错误） | 高 | 中 | 审核结果用 JSON mode / 结构化输出，添加重试 |
| 工作流多步骤中途失败 | 中 | 高 | 每步保存 checkpoint，支持从断点恢复 |
| ReAct 降级模式与标准 tool_calls 行为不一致 | 高 | 中 | 封装统一的 ToolCallAdapter，前端无感 |

---

## 九、参考链接汇总

| 项目 | 地址 | 核心借鉴 |
|------|------|----------|
| InkOS | https://github.com/Narcooo/inkos | 多 Agent 协作、人工审核关卡 |
| awesome-novel-studio | https://github.com/MJbae/awesome-novel-studio | Pipeline 命令体系、连续性桥接、4 轴审核 |
| NovelForge | https://github.com/RhythmicWave/NovelForge | 卡片系统、@DSL、代码式工作流 |
| Hermes Agent | https://github.com/NousResearch/hermes-agent | Tool Registry、Skills、Memory 分层 |
| Hermes 文档 | https://hermes-agent.nousresearch.com/docs/ | 架构指导 |
| Hermes 本地源码 | G:\\Codex\\Curiosity\\_upstream\\hermes-agent | 源码参考 |

---

*题案草稿，供架构评审与排期讨论使用。具体实现细节在各迭代启动前进一步细化。*
