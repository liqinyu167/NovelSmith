"""
NovelSmith 工具 — 工作区文件工具组

工具列表：
- update_workspace_file   创建或更新工作区文件
- read_workspace_file     读取工作区文件内容
- list_workspace_files    列出工作区所有文件
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from app.agent_tools.registry import register_tool, ToolContext

logger = logging.getLogger("novelsmith.tools.workspace")


# ─────────────────────────────────────────────
# update_workspace_file
# ─────────────────────────────────────────────

@register_tool(
    name="update_workspace_file",
    description=(
        "Create or update the contents of a specific workspace file "
        "(character profile .md, world setting, outline, chapters, etc.). "
        "Always write the FULL updated file content."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "相对于工作区的相对路径。"
                    "例如: 'knowledge/characters/林藏.md' 或 'chapters/01_第一章.md'"
                ),
            },
            "content": {
                "type": "string",
                "description": "更新后的完整文件内容（Markdown 字符串）。",
            },
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    },
)
async def _update_workspace_file(args: dict, ctx: ToolContext) -> dict:
    from app.services.workspace_manager import (
        ensure_safe_path,
        parse_yaml_front_matter,
        serialize_yaml_front_matter,
    )
    file_path = str(args.get("path") or "").strip()
    file_content = str(args.get("content") or "")

    if not file_path:
        return {"ok": False, "error": "路径为空"}

    normalized_path = file_path.replace("\\", "/").strip("/")

    try:
        # 拦截 knowledge 目录下的 .json 写入，重定向到 .md front-matter
        if (
            ("knowledge/characters/" in normalized_path or "knowledge/world/" in normalized_path)
            and normalized_path.endswith(".json")
        ):
            p = Path(normalized_path)
            md_rel_path = f"{p.parent}/{p.stem}.md"
            md_safe_path = ensure_safe_path(md_rel_path)
            try:
                metadata = json.loads(file_content) if isinstance(file_content, str) else file_content
            except Exception:
                metadata = {}
            existing_body = ""
            if md_safe_path.exists():
                try:
                    _, existing_body = parse_yaml_front_matter(md_safe_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            serialized = serialize_yaml_front_matter(metadata, existing_body)
            md_safe_path.write_text(serialized, encoding="utf-8")
            json_safe_path = ensure_safe_path(normalized_path)
            if json_safe_path.exists():
                json_safe_path.unlink()
            file_path = md_rel_path
            file_content = serialized

        # 知识库 .md 写入：合并 front-matter（如果新内容没有 front-matter 头）
        elif (
            ("knowledge/characters/" in normalized_path or "knowledge/world/" in normalized_path)
            and normalized_path.endswith(".md")
        ):
            md_safe_path = ensure_safe_path(normalized_path)
            if not file_content.strip().startswith("---") and md_safe_path.exists():
                try:
                    existing_text = md_safe_path.read_text(encoding="utf-8")
                    existing_meta, _ = parse_yaml_front_matter(existing_text)
                    if existing_meta:
                        merged = serialize_yaml_front_matter(existing_meta, file_content)
                        md_safe_path.write_text(merged, encoding="utf-8")
                        file_content = merged
                except Exception as e:
                    logger.warning(f"Failed to merge front-matter: {e}")
                    md_safe_path.write_text(file_content, encoding="utf-8")
            else:
                md_safe_path.write_text(file_content, encoding="utf-8")

        else:
            safe_path = ensure_safe_path(file_path)
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(file_content, encoding="utf-8")

        logger.info(f"update_workspace_file: wrote {len(file_content)} chars to {file_path}")
        ctx.pending_events.append({
            "type": "tool_result",
            "state": "writing",
            "name": "update_workspace_file",
            "content": json.dumps({"ok": True, "path": file_path, "chars": len(file_content)}, ensure_ascii=False),
        })
        ctx.pending_events.append({
            "type": "assistant_delta",
            "state": "writing",
            "text": f"\n\n[Agent 协同修改了文件 `{file_path}`，共 {len(file_content)} 字]",
        })
        return {"ok": True, "path": file_path, "chars": len(file_content)}

    except Exception as e:
        logger.exception(f"update_workspace_file failed: {file_path}")
        return {"ok": False, "error": str(e)}


# ─────────────────────────────────────────────
# read_workspace_file
# ─────────────────────────────────────────────

@register_tool(
    name="read_workspace_file",
    description=(
        "Read the complete content of a specific file in the workspace. "
        "Use to check existing content before modifying."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "相对于工作区的相对路径。"
                    "例如: 'knowledge/characters/林藏.md' 或 'chapters/01_第一章.md'"
                ),
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    },
)
async def _read_workspace_file(args: dict, ctx: ToolContext) -> dict:
    from app.services.workspace_manager import ensure_safe_path, parse_yaml_front_matter

    file_path = str(args.get("path") or "").strip()
    if not file_path:
        return {"ok": False, "error": "路径为空"}

    normalized_path = file_path.replace("\\", "/").strip("/")
    try:
        # 拦截 json 读取，重定向到 .md
        if (
            ("knowledge/characters/" in normalized_path or "knowledge/world/" in normalized_path)
            and normalized_path.endswith(".json")
        ):
            p = Path(normalized_path)
            md_rel_path = f"{p.parent}/{p.stem}.md"
            md_safe_path = ensure_safe_path(md_rel_path)
            if md_safe_path.exists():
                md_text = md_safe_path.read_text(encoding="utf-8")
                metadata, _ = parse_yaml_front_matter(md_text)
                return {"ok": True, "content": json.dumps(metadata, ensure_ascii=False, indent=2)}
            return {"ok": False, "error": f"File not found: {md_rel_path}"}

        safe_path = ensure_safe_path(file_path)
        if not safe_path.exists():
            return {"ok": False, "error": f"File not found: {file_path}"}
        if safe_path.is_dir():
            return {"ok": False, "error": f"'{file_path}' 是目录，不是文件。"}
        content = safe_path.read_text(encoding="utf-8")
        return {"ok": True, "content": content}
    except Exception as e:
        logger.exception(f"read_workspace_file failed: {file_path}")
        return {"ok": False, "error": str(e)}


# ─────────────────────────────────────────────
# list_workspace_files
# ─────────────────────────────────────────────

@register_tool(
    name="list_workspace_files",
    description="Recursively list all files in the current workspace directory.",
    parameters={
        "type": "object",
        "properties": {
            "subdir": {
                "type": "string",
                "description": "可选：只列出指定子目录下的文件，例如 'knowledge/characters'。",
            },
        },
        "required": [],
        "additionalProperties": False,
    },
)
async def _list_workspace_files(args: dict, ctx: ToolContext) -> dict:
    from app.services.workspace_manager import WORKSPACE_ROOT

    subdir = str(args.get("subdir") or "").strip().strip("/")
    try:
        root = Path(WORKSPACE_ROOT)
        if subdir:
            root = root / subdir
            if not root.exists():
                return {"ok": False, "error": f"子目录不存在: {subdir}"}
        files = []
        for dirpath, _, filenames in os.walk(root):
            for f in filenames:
                full_p = Path(dirpath) / f
                rel_p = str(full_p.relative_to(Path(WORKSPACE_ROOT))).replace("\\", "/")
                # 过滤知识库下的 json 文件（已被 .md 替代）
                if (
                    ("knowledge/characters/" in rel_p or "knowledge/world/" in rel_p)
                    and rel_p.endswith(".json")
                ):
                    continue
                files.append(rel_p)
        return {"ok": True, "files": sorted(files)}
    except Exception as e:
        logger.exception("list_workspace_files failed")
        return {"ok": False, "error": str(e)}
