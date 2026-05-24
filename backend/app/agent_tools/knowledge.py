"""
NovelSmith 工具 — 知识库工具组

工具列表：
- read_project_context   读取项目上下文（brief + 知识库摘要）
- search_knowledge       全文搜索知识库内容
- get_card_content       读取指定卡片（角色/世界观/场景）完整内容
"""
from __future__ import annotations

import json
import logging

from app.agent_tools.registry import register_tool, ToolContext

logger = logging.getLogger("novelsmith.tools.knowledge")


# ─────────────────────────────────────────────
# read_project_context
# ─────────────────────────────────────────────

@register_tool(
    name="read_project_context",
    description=(
        "Read the current project context: project brief, manuscript statistics, "
        "and a compiled summary of the knowledge base (characters, world settings, timeline). "
        "Always call this first before writing to understand the current state."
    ),
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
)
async def _read_project_context(args: dict, ctx: ToolContext) -> dict:
    try:
        from app.services.workspace_manager import compile_knowledge
        knowledge_context = compile_knowledge()
    except Exception as e:
        logger.warning(f"Failed to compile knowledge: {e}")
        knowledge_context = {}

    clean = ctx.manuscript.strip()
    excerpt = clean[-500:] if clean else "当前正文为空。"

    context = {
        "tool": "read_project_context",
        "project_brief": ctx.project_brief or "暂无项目记忆",
        "manuscript_chars": len(clean),
        "manuscript_excerpt": excerpt,
        "knowledge_base": knowledge_context,
    }
    result_str = json.dumps(context, ensure_ascii=False)
    ctx.pending_events.append({
        "type": "tool_result",
        "state": "preparing",
        "name": "read_project_context",
        "content": result_str,
    })

    # 生成可读摘要
    char_count = len(knowledge_context.get("characters", {}))
    world_count = len(knowledge_context.get("world", {}))
    summary_parts = []
    if char_count:
        summary_parts.append(f"{char_count} 个角色卡")
    if world_count:
        summary_parts.append(f"{world_count} 个世界观设定")
    if not summary_parts:
        summary_parts.append("知识库为空")
    ctx.pending_events.append({
        "type": "status",
        "state": "preparing",
        "label": f"读取了项目上下文（{'、'.join(summary_parts)}）",
    })
    return context


# ─────────────────────────────────────────────
# search_knowledge
# ─────────────────────────────────────────────

@register_tool(
    name="search_knowledge",
    description=(
        "Search the knowledge base for information matching a query. "
        "Returns matching content from character profiles, world settings, and other knowledge files."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，例如角色名、地点名、概念名。",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
)
async def _search_knowledge(args: dict, ctx: ToolContext) -> dict:
    from pathlib import Path
    from app.services.workspace_manager import WORKSPACE_ROOT
    import os

    query = str(args.get("query") or "").strip().lower()
    if not query:
        return {"ok": False, "error": "query 不能为空"}

    results = []
    workspace_root = Path(WORKSPACE_ROOT)
    knowledge_dir = workspace_root / "knowledge"

    if not knowledge_dir.exists():
        return {"ok": True, "results": [], "message": "知识库目录不存在"}

    for dirpath, _, filenames in os.walk(knowledge_dir):
        for fname in filenames:
            if not fname.endswith((".md", ".txt")):
                continue
            fpath = Path(dirpath) / fname
            try:
                text = fpath.read_text(encoding="utf-8")
                if query in text.lower():
                    rel = str(fpath.relative_to(workspace_root)).replace("\\", "/")
                    # 提取包含关键词的段落
                    lines = text.split("\n")
                    matched_lines = [
                        l.strip() for l in lines
                        if query in l.lower() and l.strip()
                    ][:3]
                    results.append({
                        "path": rel,
                        "matches": matched_lines,
                    })
            except Exception:
                continue

    logger.info(f"search_knowledge: query='{query}', found {len(results)} files")
    return {"ok": True, "query": query, "results": results}


# ─────────────────────────────────────────────
# get_card_content
# ─────────────────────────────────────────────

@register_tool(
    name="get_card_content",
    description=(
        "Get the full content of a specific knowledge card by type and name. "
        "Use this to read a specific character card, world setting, or scene card."
    ),
    parameters={
        "type": "object",
        "properties": {
            "card_type": {
                "type": "string",
                "enum": ["character", "world", "location", "outline"],
                "description": "卡片类型：character（角色）/ world（世界观）/ location（场景）/ outline（提纲）",
            },
            "name": {
                "type": "string",
                "description": "卡片名称，例如'林藏'、'修真体系'。",
            },
        },
        "required": ["card_type", "name"],
        "additionalProperties": False,
    },
)
async def _get_card_content(args: dict, ctx: ToolContext) -> dict:
    from pathlib import Path
    from app.services.workspace_manager import WORKSPACE_ROOT

    card_type = str(args.get("card_type") or "").strip()
    name = str(args.get("name") or "").strip()

    type_to_dir = {
        "character": "knowledge/characters",
        "world": "knowledge/world",
        "location": "knowledge/locations",
        "outline": "knowledge",
    }
    subdir = type_to_dir.get(card_type)
    if not subdir:
        return {"ok": False, "error": f"未知卡片类型: {card_type}"}

    workspace_root = Path(WORKSPACE_ROOT)
    search_dir = workspace_root / subdir

    if not search_dir.exists():
        return {"ok": False, "error": f"目录不存在: {subdir}"}

    # 模糊匹配文件名
    for fpath in search_dir.glob("*.md"):
        if name.lower() in fpath.stem.lower():
            try:
                content = fpath.read_text(encoding="utf-8")
                rel = str(fpath.relative_to(workspace_root)).replace("\\", "/")
                return {"ok": True, "path": rel, "content": content}
            except Exception as e:
                return {"ok": False, "error": str(e)}

    return {"ok": False, "error": f"未找到名为 '{name}' 的 {card_type} 卡片"}
