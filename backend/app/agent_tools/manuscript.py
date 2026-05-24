"""
NovelSmith 工具 — 正文编辑器工具组

工具列表：
- append_to_manuscript   追加内容到当前正文
- replace_selection      替换指定文本段（用于润色/修改）
- insert_at_cursor       在光标处插入内容
"""
from __future__ import annotations

import re
import logging

from app.agent_tools.registry import register_tool, ToolContext

logger = logging.getLogger("novelsmith.tools.manuscript")


# ─────────────────────────────────────────────
# append_to_manuscript
# ─────────────────────────────────────────────

@register_tool(
    name="append_to_manuscript",
    description=(
        "Append polished Chinese novel manuscript text to the current chapter editor. "
        "Call this ONLY when the user explicitly asks to write, continue, rewrite, or insert novel prose (小说正文)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": (
                    "正文内容。只包含可以直接进入小说正文编辑器的中文小说文本，不要包含任何解释或注释。"
                ),
            },
            "summary": {
                "type": "string",
                "description": "给用户看的简短中文说明，例如：已续写第三章片段，约 600 字。",
            },
        },
        "required": ["text"],
        "additionalProperties": False,
    },
)
async def _append_to_manuscript(args: dict, ctx: ToolContext) -> dict:
    raw_text = str(args.get("text") or "").strip()
    text = _clean_manuscript_text(raw_text)
    summary_input = str(args.get("summary") or "")
    summary = _clean_tool_summary(summary_input, raw_text, text)
    if not text:
        return {"ok": False, "error": "正文内容为空"}
    logger.info(f"append_to_manuscript: chars={len(text)}")
    # 实际写入由 agent_runtime 监听 pending_events 处理
    ctx.pending_events.append({
        "type": "manuscript_delta",
        "state": "writing",
        "text": text,
    })
    ctx.pending_events.append({
        "type": "assistant_delta",
        "state": "writing",
        "text": summary,
    })
    return {
        "ok": True,
        "chars": len(text),
        "position": "chapter_end",
        "summary": summary,
    }


# ─────────────────────────────────────────────
# replace_selection
# ─────────────────────────────────────────────

@register_tool(
    name="replace_selection",
    description=(
        "Replace a specific text fragment in the manuscript with new content. "
        "Use this for polishing (润色), rewriting (改写), or targeted editing of existing prose."
    ),
    parameters={
        "type": "object",
        "properties": {
            "original": {
                "type": "string",
                "description": "要替换的原始文字片段（精确匹配）。",
            },
            "replacement": {
                "type": "string",
                "description": "替换后的新内容。",
            },
            "summary": {
                "type": "string",
                "description": "给用户看的简短说明，例如：已润色第二段对白，语气更自然。",
            },
        },
        "required": ["original", "replacement"],
        "additionalProperties": False,
    },
)
async def _replace_selection(args: dict, ctx: ToolContext) -> dict:
    original = str(args.get("original") or "").strip()
    replacement = str(args.get("replacement") or "").strip()
    summary = str(args.get("summary") or f"已替换约 {len(original)} 字的文本。")
    if not original:
        return {"ok": False, "error": "original 不能为空"}
    if original not in ctx.manuscript:
        return {"ok": False, "error": "未在正文中找到指定的 original 片段，请检查是否完全匹配。"}
    new_manuscript = ctx.manuscript.replace(original, replacement, 1)
    ctx.pending_events.append({
        "type": "manuscript_replace",
        "state": "writing",
        "original": original,
        "replacement": replacement,
    })
    ctx.pending_events.append({
        "type": "assistant_delta",
        "state": "writing",
        "text": summary,
    })
    logger.info(f"replace_selection: original={len(original)} chars → replacement={len(replacement)} chars")
    return {"ok": True, "summary": summary}


# ─────────────────────────────────────────────
# insert_at_cursor
# ─────────────────────────────────────────────

@register_tool(
    name="insert_at_cursor",
    description=(
        "Insert text at a specific position in the manuscript (before or after a landmark phrase). "
        "Use this for expansions (扩写) or inserting new paragraphs mid-chapter."
    ),
    parameters={
        "type": "object",
        "properties": {
            "anchor": {
                "type": "string",
                "description": "锚点文字（精确匹配），新内容将插入到此文字之后。",
            },
            "text": {
                "type": "string",
                "description": "要插入的新内容。",
            },
            "summary": {
                "type": "string",
                "description": "给用户看的说明，例如：已在第三段之后扩写了两个场景描写段落。",
            },
        },
        "required": ["anchor", "text"],
        "additionalProperties": False,
    },
)
async def _insert_at_cursor(args: dict, ctx: ToolContext) -> dict:
    anchor = str(args.get("anchor") or "").strip()
    text = _clean_manuscript_text(str(args.get("text") or ""))
    summary = str(args.get("summary") or f"已在指定位置插入约 {len(text)} 字。")
    if not anchor:
        return {"ok": False, "error": "anchor 不能为空"}
    if anchor not in ctx.manuscript:
        return {"ok": False, "error": "未在正文中找到 anchor，请检查是否完全匹配。"}
    new_content = ctx.manuscript.replace(anchor, anchor + "\n\n" + text, 1)
    ctx.pending_events.append({
        "type": "manuscript_replace",
        "state": "writing",
        "original": ctx.manuscript,
        "replacement": new_content,
    })
    ctx.pending_events.append({
        "type": "assistant_delta",
        "state": "writing",
        "text": summary,
    })
    logger.info(f"insert_at_cursor: anchor='{anchor[:30]}…', inserted {len(text)} chars")
    return {"ok": True, "summary": summary}


# ─────────────────────────────────────────────
# 内部辅助函数
# ─────────────────────────────────────────────

def _clean_manuscript_text(text: str) -> str:
    """清洗 LLM 可能混入的 thinking tag / DSML 标记等。"""
    value = text.strip()
    value = re.sub(r"<\|end_+of_+thinking\|>", "", value, flags=re.IGNORECASE)
    value = re.sub(r"<\|/?think\|>", "", value, flags=re.IGNORECASE)
    value = re.sub(r"<think>.*?</think>", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.split(r"<\s*\|+\s*DSML\s*\|+", value, maxsplit=1, flags=re.IGNORECASE)[0]
    value = re.split(r"parameter\s+name=[\"']summary[\"']", value, maxsplit=1, flags=re.IGNORECASE)[0]
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _clean_tool_summary(summary: str, raw_text: str, cleaned_text: str) -> str:
    """生成可读的工具结果摘要。"""
    value = summary.strip()
    if not value:
        match = re.search(r"parameter\s+name=[\"']summary[\"'][^>]*>(.*)$", raw_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
    value = re.sub(r"<[^>]+>", "", value).strip()
    if not value:
        preview = cleaned_text.replace("\n", " ").strip()[:48]
        value = f"已写入正文，约 {len(cleaned_text)} 字。开头：{preview}"
    elif "约" not in value and "字" not in value:
        value = f"{value}（约 {len(cleaned_text)} 字）"
    return value
