from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal


AgentAction = Literal["chat", "write"]
AgentState = Literal[
    "idle",
    "classifying",
    "tool_use",
    "planning",
    "awaiting_approval",
    "executing",
    "done",
    "failed",
]
ApprovalState = Literal["not_required", "pending", "approved", "rejected"]


@dataclass
class AgentEvent:
    type: str
    state: AgentState
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentDecision:
    action: AgentAction
    reason: str
    requires_approval: bool


@dataclass
class ToolSpec:
    name: str
    description: str
    mutates_manuscript: bool
    handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "mutates_manuscript": tool.mutates_manuscript,
            }
            for tool in self._tools.values()
        ]


class ApprovalGate:
    def __init__(self) -> None:
        self._approvals: dict[str, ApprovalState] = {}

    def request(self, run_id: str) -> ApprovalState:
        self._approvals[run_id] = "pending"
        return "pending"

    def approve(self, run_id: str) -> None:
        self._approvals[run_id] = "approved"

    def reject(self, run_id: str) -> None:
        self._approvals[run_id] = "rejected"

    def state(self, run_id: str) -> ApprovalState:
        return self._approvals.get(run_id, "not_required")


def decide_intent(prompt: str) -> AgentDecision:
    strong_write_words = ["续写", "改写", "润色", "扩写", "生成正文", "插入", "补一段", "写一段", "写入"]
    weak_write_words = ["写", "开头", "结尾", "章节"]
    question_words = ["怎么", "为什么", "讨论", "分析", "配置", "状态", "能不能", "是什么", "建议", "架构", "？", "?"]

    if any(word in prompt for word in strong_write_words):
        return AgentDecision(action="write", reason="检测到明确正文写入意图", requires_approval=True)
    if any(word in prompt for word in weak_write_words) and not any(word in prompt for word in question_words):
        return AgentDecision(action="write", reason="检测到写作请求", requires_approval=True)
    return AgentDecision(action="chat", reason="普通对话或工具咨询", requires_approval=False)
