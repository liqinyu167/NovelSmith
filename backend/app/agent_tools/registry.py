"""
NovelSmith 工具注册中心 — 对齐 HermesAgent tools/registry.py 设计

用法：
    @register_tool("my_tool", "描述", {...parameters schema...})
    async def my_tool_handler(args: dict, context: ToolContext) -> dict:
        ...

    # 获取工具 schema 列表
    schemas = get_toolset(["my_tool", "other_tool"])

    # 派发工具调用
    result = await dispatch("my_tool", {"key": "val"}, context)
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field

logger = logging.getLogger("novelsmith.tool_registry")

# ────────────────────────────────────────────────
# Context 对象：工具执行时可访问的运行时上下文
# ────────────────────────────────────────────────

@dataclass
class ToolContext:
    """工具执行上下文，从 AgentRunRequest 填充。"""
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    manuscript: str = ""
    project_brief: str = ""
    active_file_path: str = ""
    active_file_content: str = ""
    agent_role: str = "general"
    # SSE 事件推送列表（工具执行时可 append 额外事件）
    pending_events: list[dict] = field(default_factory=list)


# ────────────────────────────────────────────────
# 注册表内部存储
# ────────────────────────────────────────────────

_registry: dict[str, dict[str, Any]] = {}


def register_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
) -> Callable:
    """
    装饰器工厂：注册一个工具。

    示例::

        @register_tool(
            name="append_to_manuscript",
            description="...",
            parameters={...},
        )
        async def _handler(args, ctx):
            ...
    """
    def decorator(fn: Callable[[dict, ToolContext], Awaitable[dict]]) -> Callable:
        if name in _registry:
            logger.warning(f"Tool '{name}' is being re-registered, overwriting previous definition.")
        _registry[name] = {
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            },
            "handler": fn,
        }
        logger.debug(f"Registered tool: {name}")
        return fn
    return decorator


def get_toolset(names: list[str]) -> list[dict[str, Any]]:
    """
    返回指定名称的工具 schema 列表（传给 LLM 的 tools 参数）。
    未知名称静默跳过并记录警告。
    """
    result = []
    for n in names:
        if n in _registry:
            result.append(_registry[n]["schema"])
        else:
            logger.warning(f"Toolset requested unknown tool: '{n}', skipping.")
    return result


def get_all_tool_names() -> list[str]:
    """返回所有已注册工具的名称列表。"""
    return list(_registry.keys())


async def dispatch(
    name: str,
    args: dict[str, Any],
    context: ToolContext,
) -> dict[str, Any]:
    """
    派发工具调用到对应 handler。

    Returns:
        handler 返回的结果 dict。

    Raises:
        KeyError: 工具名不存在于注册表。
        Exception: handler 执行时抛出的异常。
    """
    if name not in _registry:
        logger.error(f"Dispatch failed: unknown tool '{name}'")
        return {"ok": False, "error": f"Unknown tool: {name}"}
    try:
        result = await _registry[name]["handler"](args, context)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        logger.exception(f"Tool '{name}' handler raised an exception")
        return {"ok": False, "error": str(e)}


def is_registered(name: str) -> bool:
    """检查工具是否已注册。"""
    return name in _registry
