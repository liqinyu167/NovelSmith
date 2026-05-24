import asyncio
import json
import re
import logging
from collections.abc import AsyncIterator

import httpx
from pydantic import BaseModel

from app.services.hermes_core import decide_intent
from app.services.http_client import get_client
from app.services.url_validator import validate_base_url
from app.exceptions import (
    NovelSmithError,
    ProviderNotConfiguredError,
    ProviderConnectionError,
    InvalidBaseURLError,
    PlanGenerationError,
)

logger = logging.getLogger("novelsmith.agent_runtime")


class AgentRunRequest(BaseModel):
    prompt: str
    manuscript: str = ""
    project_brief: str = ""
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    write_plan: dict | None = None
    active_file_path: str = ""
    active_file_content: str = ""


class WritePlanRequest(AgentRunRequest):
    pass


async def classify_intent(request: AgentRunRequest) -> dict:
    if not request.base_url or not request.model or not request.api_key:
        logger.info("Provider config missing, falling back to heuristic intent classification")
        return heuristic_intent(request.prompt)

    try:
        validate_base_url(request.base_url)
    except InvalidBaseURLError as e:
        logger.warning(f"Invalid base URL during intent classification: {e}")
        return heuristic_intent(request.prompt)

    messages = [
        {
            "role": "system",
            "content": (
                "Classify a user message in a Chinese novel-writing app. Return JSON only. "
                "Schema: {action:'chat'|'write', reason:string}. "
                "CRITICAL: If the user wants to add, modify, update, delete, rewrite, or append character settings, world concepts, outline chapters list, threads, or timeline events, you MUST classify it as action='chat'. Editing knowledge base, settings, outlines, or timeline must be 'chat'. "
                "Use action='write' ONLY and SOLELY when the user explicitly wants to generate, write, continue, or rewrite novel manuscript prose (小说正文/草稿/章节内容)."
            ),
        },
        {"role": "user", "content": request.prompt},
    ]
    payload = {
        "model": request.model,
        "messages": messages,
        "temperature": 0,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    try:
        logger.info(f"Classifying intent for prompt: {request.prompt[:50]}")
        data = await openai_chat_json(request, payload)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        parsed = json.loads(content)
        action = "write" if parsed.get("action") == "write" else "chat"
        reason = str(parsed.get("reason") or "")
        logger.info(f"Intent classified as: {action} (reason: {reason})")
        return {"action": action, "reason": reason}
    except Exception as e:
        logger.exception("LLM intent classification failed, falling back to heuristic")
        return heuristic_intent(request.prompt)


async def create_write_plan(request: WritePlanRequest) -> dict:
    if not request.base_url or not request.model or not request.api_key:
        raise ProviderNotConfiguredError()

    validate_base_url(request.base_url)

    messages = [
        {
            "role": "system",
            "content": (
                "You are NovelSmith Director Agent. Before writing, produce a concise Chinese JSON plan for a novel-writing action. "
                "Return JSON only. Schema: "
                "{intent:string,target:string,summary:string,steps:string[],constraints:string[],risks:string[],estimated_length:string,write_position:string,requires_confirmation:boolean}."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Project brief:\n{request.project_brief or 'No project brief yet.'}\n\n"
                f"Current manuscript excerpt:\n{request.manuscript[-2000:] or 'Empty chapter.'}\n\n"
                f"User instruction:\n{request.prompt}\n\n"
                "Create a write plan. Do not write the manuscript yet."
            ),
        },
    ]
    payload = {
        "model": request.model,
        "messages": messages,
        "temperature": 0.35,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    
    logger.info("Creating write plan via LLM")
    try:
        data = await openai_chat_json(request, payload)
    except httpx.HTTPError as e:
        logger.exception("HTTP error generating write plan")
        raise PlanGenerationError(f"生成写作计划失败: 网络或API错误 ({str(e)})")
    except Exception as e:
        logger.exception("Unexpected error generating write plan")
        raise PlanGenerationError(f"生成写作计划失败: {str(e)}")

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    try:
        plan = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Failed to decode JSON from plan generation, falling back to demo plan")
        plan = demo_write_plan(request)
        plan["summary"] = content.strip() or plan["summary"]
    return normalize_write_plan(plan, request)


async def stream_agent_events(request: AgentRunRequest) -> AsyncIterator[dict]:
    if not request.base_url or not request.model or not request.api_key:
        yield {"type": "error", "state": "error", "message": missing_provider_message()}
        return

    try:
        validate_base_url(request.base_url)
    except InvalidBaseURLError as e:
        yield {"type": "error", "state": "error", "message": str(e)}
        return

    yield status("planning", "读取当前正文与项目记忆")
    yield status("preparing", "组装写作上下文")
    yield status("connecting", f"连接模型 {request.model}")
    yield status("writing", "模型正在生成正文")

    try:
        async for token in stream_openai_compatible(request):
            yield {"type": "manuscript_delta", "state": "writing", "text": token}
    except Exception as e:
        logger.exception("Error during manuscript streaming")
        yield {"type": "error", "state": "error", "message": f"生成正文时出错: {str(e)}"}
        return

    yield {"type": "done", "state": "done"}


async def stream_chat_events(request: AgentRunRequest) -> AsyncIterator[dict]:
    if not request.base_url or not request.model or not request.api_key:
        yield {"type": "error", "state": "error", "message": missing_provider_message()}
        return

    try:
        validate_base_url(request.base_url)
    except InvalidBaseURLError as e:
        yield {"type": "error", "state": "error", "message": str(e)}
        return

    yield status("preparing", "读取项目记忆与当前正文状态")
    context = build_context_tool_result(request)
    yield {"type": "tool_result", "state": "preparing", "name": "read_project_context", "content": context}

    yield status("connecting", f"连接模型 {request.model}")
    messages = [
        {
            "role": "system",
            "content": (
                "You are NovelSmith Director Agent, a helpful co-writing assistant. You can chat normally in Chinese and help with novel planning, settings, characters, style, and workflow.\n"
                "You have four tools to assist you:\n"
                "1. `append_to_manuscript`: Call this when the user explicitly asks you to write, continue, rewrite, polish, expand, or insert novel正文.\n"
                "2. `update_workspace_file`: Call this when the user asks you to modify, update, create, or add settings, character info, world details, outline or current view files. Ensure you write the FULL updated file content for the file.\n"
                "3. `read_workspace_file`: Call this to read the complete content of a specific file in the workspace.\n"
                "4. `list_workspace_files`: Call this to recursively list all files in the current workspace directory.\n\n"
                "CRITICAL SPECIFICATION: Character profiles (in `knowledge/characters/`) and world settings (in `knowledge/world/`) are stored as single `.md` files (NOT `.json` files) with YAML front-matter headers containing their structure fields (like name, role, tags, score, etc.). For example:\n"
                "---\n"
                "name: 姓名\n"
                "role: 主角/反派/...\n"
                "tags: [标签1, 标签2]\n"
                "score: 设定分值\n"
                "abilities: 信息渗透\n"
                "...\n"
                "---\n"
                "# 角色卡：姓名\n"
                "背景与设定细节描述...\n\n"
                "When you modify or create character profiles or world settings, you MUST read and write the `.md` file, preserving or extending the YAML front-matter fields as metadata. Never attempt to read or write `.json` files under `knowledge/characters/` or `knowledge/world/`.\n\n"
                "If the user is currently viewing/editing a file, its path and content will be provided in the user message. You can directly edit it using `update_workspace_file` with the correct path."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Active file context (User is currently viewing/editing this file):\n"
                f"Path: {request.active_file_path or 'None'}\n"
                f"Content:\n{request.active_file_content or 'None'}\n\n"
                f"Tool context:\n{context}\n\n"
                f"Project brief:\n{request.project_brief or 'No project brief yet.'}\n\n"
                f"User message:\n{request.prompt}"
            ),
        },
    ]

    max_loops = 10
    loop_count = 0
    total_wrote_any = False

    while loop_count < max_loops:
        loop_count += 1
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": 0.65,
            "stream": False,
            "tools": [
                append_manuscript_tool_schema(),
                update_workspace_file_schema(),
                read_workspace_file_schema(),
                list_workspace_files_schema()
            ],
            "tool_choice": "auto",
        }
        try:
            logger.info(f"LLM Tool Loop {loop_count} request started.")
            data = await openai_chat_json(request, payload)
        except httpx.HTTPStatusError as exc:
            logger.warning(f"HTTP status error {exc.response.status_code} in Loop {loop_count}, checking fallback")
            if total_wrote_any:
                logger.info("Tool calling already succeeded in previous loop, ignoring follow-up error in subsequent loop.")
                break
            if loop_count == 1 and exc.response.status_code in {400, 422}:
                if decide_intent(request.prompt).action == "write":
                    yield status("writing", "模型工具协议不可用，切换内置正文编辑器")
                    try:
                        async for token in stream_openai_compatible(request):
                            yield {"type": "manuscript_delta", "state": "writing", "text": token}
                    except Exception as e:
                        logger.exception("Error in fallback stream_openai_compatible")
                        yield {"type": "error", "state": "error", "message": str(e)}
                        return
                    yield {"type": "assistant_delta", "state": "writing", "text": "已写入正文编辑区。"}
                    yield {"type": "done", "state": "done"}
                    return
                yield status("writing", "模型工具协议不可用，切换普通对话")
                try:
                    async for token in stream_openai_compatible_messages(request, messages, temperature=0.65):
                        yield {"type": "assistant_delta", "state": "writing", "text": token}
                except Exception as e:
                    logger.exception("Error in fallback stream_openai_compatible_messages")
                    yield {"type": "error", "state": "error", "message": str(e)}
                    return
                yield {"type": "done", "state": "done"}
                return
            else:
                logger.exception("HTTP error in Tool Loop")
                yield {"type": "error", "state": "error", "message": f"请求大模型失败: {str(exc)}"}
                return
        except Exception as e:
            logger.exception("Unexpected error in Tool Loop")
            if total_wrote_any:
                logger.info("Tool calling already succeeded in previous loop, ignoring follow-up error in subsequent loop.")
                break
            yield {"type": "error", "state": "error", "message": f"请求大模型失败: {str(e)}"}
            return

        message = data.get("choices", [{}])[0].get("message", {})
        tool_calls = message.get("tool_calls") or []
        content = str(message.get("content") or "").strip()

        # Fill missing tool call IDs to prevent 400 Bad Request on some API providers
        for idx, tool_call in enumerate(tool_calls):
            if not tool_call.get("id"):
                tool_call["id"] = f"call_{loop_count}_{idx}_{tool_call.get('function', {}).get('name', 'tool')}"

        # Append assistant message with tool_calls for API compliance
        content_val = message.get("content")
        if content_val is not None:
            if not str(content_val).strip() and tool_calls:
                content_val = None

        assistant_msg = {
            "role": "assistant",
            "content": content_val
        }
        if message.get("reasoning_content"):
            assistant_msg["reasoning_content"] = message["reasoning_content"]
        elif message.get("thinking_content"):
            assistant_msg["reasoning_content"] = message["thinking_content"]

        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        if not tool_calls:
            if content:
                yield {"type": "assistant_delta", "state": "writing", "text": content}
            else:
                if loop_count == 1:
                    yield {"type": "assistant_delta", "state": "writing", "text": "未检测到特定指令或工具调用请求。"}
            break

        for tool_call in tool_calls:
            call_id = tool_call.get("id")
            function = tool_call.get("function") or {}
            name = function.get("name")

            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}

            if name == "append_to_manuscript":
                raw_text = str(arguments.get("text") or "").strip()
                text = clean_manuscript_text(raw_text)
                summary = clean_tool_summary(str(arguments.get("summary") or ""), raw_text, text)
                logger.info(f"Executing append_to_manuscript: chars={len(text)}, summary={summary}")
                if not text:
                    tool_result_str = json.dumps({"ok": False, "error": "内容为空"}, ensure_ascii=False)
                else:
                    total_wrote_any = True
                    yield status("writing", "调用正文编辑器 append_to_manuscript")
                    yield {
                        "type": "tool_result",
                        "state": "writing",
                        "name": "append_to_manuscript",
                        "content": json.dumps({"chars": len(text), "position": "chapter_end", "summary": summary}, ensure_ascii=False),
                    }
                    yield {"type": "manuscript_delta", "state": "writing", "text": text}
                    yield {"type": "assistant_delta", "state": "writing", "text": summary}
                    tool_result_str = json.dumps({"ok": True, "chars": len(text), "summary": summary}, ensure_ascii=False)

                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": tool_result_str
                })

            elif name == "update_workspace_file":
                file_path = str(arguments.get("path") or "").strip()
                file_content = str(arguments.get("content") or "")
                logger.info(f"Executing update_workspace_file: path={file_path}, chars={len(file_content)}")

                if not file_path:
                    tool_result_str = json.dumps({"ok": False, "error": "路径为空"}, ensure_ascii=False)
                else:
                    try:
                        from app.services.workspace_manager import ensure_safe_path, parse_yaml_front_matter, serialize_yaml_front_matter
                        
                        normalized_path = file_path.replace("\\", "/").strip("/")
                        
                        # Intercept json write and redirect to .md front-matter
                        if ("knowledge/characters/" in normalized_path or "knowledge/world/" in normalized_path) and normalized_path.endswith(".json"):
                            p = Path(normalized_path)
                            base_name = p.stem
                            parent_dir = p.parent
                            md_rel_path = f"{parent_dir}/{base_name}.md"
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
                            
                            # Clean up old json
                            json_safe_path = ensure_safe_path(normalized_path)
                            if json_safe_path.exists():
                                json_safe_path.unlink()
                                
                            file_path = md_rel_path
                            file_content = serialized
                            
                        # If writing to direct .md, merge front-matter if missing
                        elif ("knowledge/characters/" in normalized_path or "knowledge/world/" in normalized_path) and normalized_path.endswith(".md"):
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
                                    logger.warning(f"Failed to merge existing front-matter in agent update: {e}")
                            else:
                                md_safe_path.write_text(file_content, encoding="utf-8")
                        else:
                            safe_path = ensure_safe_path(file_path)
                            safe_path.parent.mkdir(parents=True, exist_ok=True)
                            safe_path.write_text(file_content, encoding="utf-8")

                        total_wrote_any = True
                        yield status("writing", f"Agent已修改文件: {file_path}")
                        yield {
                            "type": "tool_result",
                            "state": "writing",
                            "name": "update_workspace_file",
                            "content": json.dumps({"ok": True, "path": file_path, "chars": len(file_content)}, ensure_ascii=False)
                        }
                        yield {"type": "assistant_delta", "state": "writing", "text": f"\n\n[Agent 协同修改了文件 `{file_path}`]"}
                        tool_result_str = json.dumps({"ok": True, "path": file_path, "chars": len(file_content)}, ensure_ascii=False)
                    except Exception as e:
                        logger.exception("Agent update_workspace_file tool failed")
                        yield {"type": "error", "state": "error", "message": f"Agent 修改工作区文件失败: {str(e)}"}
                        return

                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": tool_result_str
                })

            elif name == "read_workspace_file":
                file_path = str(arguments.get("path") or "").strip()
                logger.info(f"Executing read_workspace_file: path={file_path}")
                if not file_path:
                    res = {"ok": False, "error": "路径为空"}
                else:
                    try:
                        from app.services.workspace_manager import ensure_safe_path, parse_yaml_front_matter
                        normalized_path = file_path.replace("\\", "/").strip("/")
                        
                        # Intercept json read and redirect to .md front-matter parsing
                        if ("knowledge/characters/" in normalized_path or "knowledge/world/" in normalized_path) and normalized_path.endswith(".json"):
                            p = Path(normalized_path)
                            base_name = p.stem
                            parent_dir = p.parent
                            md_rel_path = f"{parent_dir}/{base_name}.md"
                            md_safe_path = ensure_safe_path(md_rel_path)
                            
                            if md_safe_path.exists():
                                try:
                                    md_text = md_safe_path.read_text(encoding="utf-8")
                                    metadata, _ = parse_yaml_front_matter(md_text)
                                    content = json.dumps(metadata, ensure_ascii=False, indent=2)
                                    res = {"ok": True, "content": content}
                                except Exception as e:
                                    res = {"ok": False, "error": str(e)}
                            else:
                                res = {"ok": False, "error": f"File not found: {md_rel_path}"}
                        else:
                            safe_path = ensure_safe_path(file_path)
                            if safe_path.exists():
                                if safe_path.is_dir():
                                    res = {"ok": False, "error": f"Path '{file_path}' is a directory, not a file."}
                                else:
                                    content = safe_path.read_text(encoding="utf-8")
                                    res = {"ok": True, "content": content}
                            else:
                                res = {"ok": False, "error": f"File not found: {file_path}"}
                    except Exception as e:
                        res = {"ok": False, "error": str(e)}

                tool_result_str = json.dumps(res, ensure_ascii=False)
                yield {
                    "type": "tool_result",
                    "state": "writing",
                    "name": "read_workspace_file",
                    "content": tool_result_str
                }
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": tool_result_str
                })

            elif name == "list_workspace_files":
                logger.info("Executing list_workspace_files")
                try:
                    import os
                    from pathlib import Path
                    from app.services.workspace_manager import WORKSPACE_ROOT
                    files = []
                    for root, _, filenames in os.walk(WORKSPACE_ROOT):
                        for f in filenames:
                            full_p = Path(root) / f
                            rel_p = str(full_p.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
                            # Filter out character/world json files from listing
                            if ("knowledge/characters/" in rel_p or "knowledge/world/" in rel_p) and rel_p.endswith(".json"):
                                continue
                            files.append(rel_p)
                    res = {"ok": True, "files": files}
                except Exception as e:
                    res = {"ok": False, "error": str(e)}

                tool_result_str = json.dumps(res, ensure_ascii=False)
                yield {
                    "type": "tool_result",
                    "state": "writing",
                    "name": "list_workspace_files",
                    "content": tool_result_str
                }
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": tool_result_str
                })
            else:
                logger.warning(f"Unknown tool call name received: {name}")
                tool_result_str = json.dumps({"ok": False, "error": f"Unknown tool: {name}"}, ensure_ascii=False)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name or "unknown",
                    "content": tool_result_str
                })

    if messages and messages[-1].get("role") == "tool":
        # Force a final completion to summarize/respond based on current accumulated tool outputs
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": 0.65,
            "stream": False,
        }
        try:
            logger.info("Forcing final completion after reaching max loops / tool calls.")
            data = await openai_chat_json(request, payload)
            content = str(data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            if content:
                yield {"type": "assistant_delta", "state": "writing", "text": content}
        except Exception as e:
            logger.exception("Failed to generate final completion after tool loops")

    yield {"type": "done", "state": "done"}



def missing_provider_message() -> str:
    return "Hermes Agent 未连接 API：请先在右上角配置 Base URL、Model 和 API Key。"


def append_manuscript_tool_schema() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "append_to_manuscript",
            "description": "Append polished Chinese novel manuscript text to the current chapter editor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "正文内容。只包含可以直接进入小说正文编辑器的中文小说文本，不要解释。",
                    },
                    "summary": {
                        "type": "string",
                        "description": "给用户看的简短中文说明，例如：已续写并写入正文。",
                    },
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        },
    }


def update_workspace_file_schema() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "update_workspace_file",
            "description": "Create or update the contents of a specific workspace file (such as a character profile .md/.json, or world setting, or outline).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对于工作区的相对路径。例如: 'knowledge/characters/林藏.md' 或 'knowledge/characters/林藏.json' 或 'chapters/01_第一章：雾中来信.md'"
                    },
                    "content": {
                        "type": "string",
                        "description": "更新后的完整文件内容（如果是 .json，必须是合法的 JSON 格式字符串；如果是 .md，则是合法的 Markdown 字符串）。"
                    }
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            }
        }
    }


def clean_manuscript_text(text: str) -> str:
    value = text.strip()
    value = re.sub(r"<\|end_+of_+thinking\|>", "", value, flags=re.IGNORECASE)
    value = re.sub(r"<\|/?think\|>", "", value, flags=re.IGNORECASE)
    value = re.sub(r"<think>.*?</think>", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.split(r"<\s*\|+\s*DSML\s*\|+", value, maxsplit=1, flags=re.IGNORECASE)[0]
    value = re.split(r"parameter\s+name=[\"']summary[\"']", value, maxsplit=1, flags=re.IGNORECASE)[0]
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def clean_tool_summary(summary: str, raw_text: str, cleaned_text: str) -> str:
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


async def stream_openai_compatible(request: AgentRunRequest) -> AsyncIterator[str]:
    plan_block = json.dumps(request.write_plan or {}, ensure_ascii=False, indent=2)
    # Truncate manuscript to last 4000 characters
    truncated_manuscript = request.manuscript[-4000:] if request.manuscript else "Empty chapter."
    messages = [
        {
            "role": "system",
            "content": (
                "You are NovelSmith Director Agent, a Chinese long-form fiction writing agent. "
                "Write polished Chinese novel prose only for the manuscript stream. "
                "Continue or create the chapter based on the user instruction. "
                "Avoid explanations inside the manuscript."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Project brief:\n{request.project_brief or 'No project brief yet.'}\n\n"
                f"Current manuscript:\n{truncated_manuscript}\n\n"
                f"Approved write plan:\n{plan_block}\n\n"
                f"User instruction:\n{request.prompt}\n\n"
                "Now execute the approved plan and write the next manuscript section in Chinese Markdown. "
                "Do not explain the plan. Output manuscript prose only."
            ),
        },
    ]
    async for token in stream_openai_compatible_messages(request, messages, temperature=0.85):
        yield token


async def stream_openai_compatible_messages(
    request: AgentRunRequest, messages: list[dict], temperature: float
) -> AsyncIterator[str]:
    payload = {"model": request.model, "messages": messages, "temperature": temperature, "stream": True}
    url = f"{request.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {request.api_key}",
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }

    client = get_client()
    try:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    break
                try:
                    packet = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = packet.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP Status Error in stream {exc.response.status_code} for URL {url}. Response body: {exc.response.text}")
        raise


async def openai_chat_json(request: AgentRunRequest, payload: dict) -> dict:
    url = f"{request.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {request.api_key}",
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }
    client = get_client()
    try:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP Status Error {exc.response.status_code} for URL {url}. Response body: {exc.response.text}")
        raise


def demo_write_plan(request: AgentRunRequest) -> dict:
    return normalize_write_plan(
        {
            "intent": "生成小说正文",
            "target": request.prompt,
            "summary": "根据当前项目记忆和用户指令，追加一段有画面感的正文。",
            "steps": ["读取当前正文末尾", "延续既有语气", "生成一段可直接进入章节的正文"],
            "constraints": ["只输出正文", "保持中文小说语体", "不改写已有正文"],
            "risks": ["项目设定较少，可能需要后续补充角色 and 世界观细节"],
            "estimated_length": "约 300-800 字",
            "write_position": "当前章节末尾",
            "requires_confirmation": True,
        },
        request,
    )


def normalize_write_plan(plan: dict, request: AgentRunRequest) -> dict:
    return {
        "intent": str(plan.get("intent") or "生成小说正文"),
        "target": str(plan.get("target") or request.prompt),
        "summary": str(plan.get("summary") or "准备根据你的指令写入正文。"),
        "steps": ensure_string_list(plan.get("steps"), ["整理上下文", "生成正文", "写入当前章节"]),
        "constraints": ensure_string_list(plan.get("constraints"), ["只写正文", "不覆盖已有内容"]),
        "risks": ensure_string_list(plan.get("risks"), ["如设定不足，生成内容可能需要二次调整"]),
        "estimated_length": str(plan.get("estimated_length") or "约 300-800 字"),
        "write_position": str(plan.get("write_position") or "当前章节末尾"),
        "requires_confirmation": True,
    }


def ensure_string_list(value: object, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or fallback
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return fallback


def heuristic_intent(prompt: str) -> dict:
    decision = decide_intent(prompt)
    return {"action": decision.action, "reason": decision.reason}


def build_context_tool_result(request: AgentRunRequest) -> str:
    clean = request.manuscript.strip()
    excerpt = clean[-500:] if clean else "当前正文为空。"
    
    # 引入 compile_knowledge 获取当前所有角色、设定、时间线、线索等编译后数据作为上帝视角的 Context
    try:
        from app.services.workspace_manager import compile_knowledge
        knowledge_context = compile_knowledge()
    except Exception as e:
        logger.warning(f"Failed to compile knowledge for agent context: {e}")
        knowledge_context = {}

    return json.dumps(
        {
            "tool": "read_project_context",
            "project_brief": request.project_brief or "暂无项目记忆",
            "manuscript_chars": len(clean),
            "manuscript_excerpt": excerpt,
            "knowledge_base": knowledge_context,
        },
        ensure_ascii=False,
    )


def read_workspace_file_schema() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "read_workspace_file",
            "description": "Read the complete content of a specific file in the workspace (such as a character profile .md/.json, or world setting, or timeline.json, outline.json, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对于工作区的相对路径。例如: 'knowledge/characters/林藏.json' 或 'knowledge/timeline.json' 或 'chapters/01_第一章：雾中来信.md'"
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            }
        }
    }


def list_workspace_files_schema() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "list_workspace_files",
            "description": "List all files present in the current workspace directory recursively.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            }
        }
    }


def status(state: str, label: str) -> dict[str, str]:
    return {"type": "status", "state": state, "label": label}

