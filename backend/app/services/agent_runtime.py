import asyncio
import asyncio
import json
import re
from collections.abc import AsyncIterator

import httpx
from pydantic import BaseModel

from app.services.hermes_core import decide_intent


class AgentRunRequest(BaseModel):
    prompt: str
    manuscript: str = ""
    project_brief: str = ""
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    write_plan: dict | None = None


class WritePlanRequest(AgentRunRequest):
    pass


async def classify_intent(request: AgentRunRequest) -> dict:
    if not request.base_url or not request.model or not request.api_key:
        return heuristic_intent(request.prompt)

    messages = [
        {
            "role": "system",
            "content": (
                "Classify a user message in a Chinese novel-writing app. Return JSON only. "
                "Schema: {action:'chat'|'write', reason:string}. "
                "Use action='write' only when the user explicitly wants to create, continue, rewrite, polish, expand, or insert manuscript text. "
                "Use action='chat' for questions, discussion, settings, strategy, tool/context queries, and general conversation."
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
        data = await openai_chat_json(request, payload)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        parsed = json.loads(content)
        action = "write" if parsed.get("action") == "write" else "chat"
        return {"action": action, "reason": str(parsed.get("reason") or "")}
    except Exception:
        return heuristic_intent(request.prompt)


async def create_write_plan(request: WritePlanRequest) -> dict:
    if not request.base_url or not request.model or not request.api_key:
        raise RuntimeError(missing_provider_message())

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
    data = await openai_chat_json(request, payload)
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    try:
        plan = json.loads(content)
    except json.JSONDecodeError:
        plan = demo_write_plan(request)
        plan["summary"] = content.strip() or plan["summary"]
    return normalize_write_plan(plan, request)


async def stream_agent_events(request: AgentRunRequest) -> AsyncIterator[dict]:
    if not request.base_url or not request.model or not request.api_key:
        yield {"type": "error", "state": "error", "message": missing_provider_message()}
        return

    yield status("planning", "读取当前正文与项目记忆")
    await asyncio.sleep(0.12)
    yield status("preparing", "组装写作上下文")
    yield status("connecting", f"连接模型 {request.model}")
    await asyncio.sleep(0.05)
    yield status("writing", "模型正在生成正文")

    async for token in stream_openai_compatible(request):
        yield {"type": "manuscript_delta", "state": "writing", "text": token}

    yield {"type": "done", "state": "done"}


async def stream_chat_events(request: AgentRunRequest) -> AsyncIterator[dict]:
    if not request.base_url or not request.model or not request.api_key:
        yield {"type": "error", "state": "error", "message": missing_provider_message()}
        return

    yield status("preparing", "读取项目记忆与当前正文状态")
    context = build_context_tool_result(request)
    yield {"type": "tool_result", "state": "preparing", "name": "read_project_context", "content": context}

    yield status("connecting", f"连接模型 {request.model}")
    messages = [
        {
            "role": "system",
            "content": (
                "You are NovelSmith Director Agent. You can chat normally in Chinese and help with novel planning, settings, characters, style, and workflow. "
                "You have one editor tool named append_to_manuscript. "
                "When the user explicitly asks you to write, continue, rewrite, polish, expand, or insert novel正文, you MUST call append_to_manuscript with polished Chinese manuscript text. "
                "Do not put manuscript prose in a normal chat answer when an editor tool call is appropriate. "
                "For discussion, questions, planning, or critique, answer normally without tools. Be concise and useful."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Tool context:\n{context}\n\n"
                f"Project brief:\n{request.project_brief or 'No project brief yet.'}\n\n"
                f"User message:\n{request.prompt}"
            ),
        },
    ]
    payload = {
        "model": request.model,
        "messages": messages,
        "temperature": 0.65,
        "stream": False,
        "tools": [append_manuscript_tool_schema()],
        "tool_choice": "auto",
    }
    try:
        data = await openai_chat_json(request, payload)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code not in {400, 422}:
            raise
        if decide_intent(request.prompt).action == "write":
            yield status("writing", "模型工具协议不可用，切换内置正文编辑器")
            async for token in stream_openai_compatible(request):
                yield {"type": "manuscript_delta", "state": "writing", "text": token}
            yield {"type": "assistant_delta", "state": "writing", "text": "已写入正文编辑区。"}
            yield {"type": "done", "state": "done"}
            return
        yield status("writing", "模型工具协议不可用，切换普通对话")
        async for token in stream_openai_compatible_messages(request, messages, temperature=0.65):
            yield {"type": "assistant_delta", "state": "writing", "text": token}
        yield {"type": "done", "state": "done"}
        return
    message = data.get("choices", [{}])[0].get("message", {})
    tool_calls = message.get("tool_calls") or []

    if tool_calls:
        wrote_any = False
        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            if function.get("name") != "append_to_manuscript":
                continue
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}
            raw_text = str(arguments.get("text") or "").strip()
            text = clean_manuscript_text(raw_text)
            summary = clean_tool_summary(str(arguments.get("summary") or ""), raw_text, text)
            if not text:
                continue
            wrote_any = True
            yield status("writing", "调用正文编辑器 append_to_manuscript")
            yield {
                "type": "tool_result",
                "state": "writing",
                "name": "append_to_manuscript",
                "content": json.dumps({"chars": len(text), "position": "chapter_end", "summary": summary}, ensure_ascii=False),
            }
            for chunk in chunk_text(text, 12):
                await asyncio.sleep(0.02)
                yield {"type": "manuscript_delta", "state": "writing", "text": chunk}
            for chunk in chunk_text(summary, 12):
                await asyncio.sleep(0.015)
                yield {"type": "assistant_delta", "state": "writing", "text": chunk}
        if not wrote_any:
            yield {"type": "error", "state": "error", "message": "模型请求了编辑工具，但没有提供可写入的正文。"}
            return
        yield {"type": "done", "state": "done"}
        return

    content = str(message.get("content") or "").strip()
    if not content:
        content = "模型没有返回内容，也没有调用正文编辑工具。"
    for token in chunk_text(content, 12):
        await asyncio.sleep(0.015)
        yield {"type": "assistant_delta", "state": "writing", "text": token}
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
                f"Current manuscript:\n{request.manuscript or 'Empty chapter.'}\n\n"
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
    headers = {"Authorization": f"Bearer {request.api_key}"}

    timeout = httpx.Timeout(connect=20, read=120, write=20, pool=20)
    async with httpx.AsyncClient(timeout=timeout) as client:
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


async def openai_chat_json(request: AgentRunRequest, payload: dict) -> dict:
    url = f"{request.base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {request.api_key}"}
    timeout = httpx.Timeout(connect=20, read=90, write=20, pool=20)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def demo_write_plan(request: AgentRunRequest) -> dict:
    return normalize_write_plan(
        {
            "intent": "生成小说正文",
            "target": request.prompt,
            "summary": "根据当前项目记忆和用户指令，追加一段有画面感的正文。",
            "steps": ["读取当前正文末尾", "延续既有语气", "生成一段可直接进入章节的正文"],
            "constraints": ["只输出正文", "保持中文小说语体", "不改写已有正文"],
            "risks": ["项目设定较少，可能需要后续补充角色和世界观细节"],
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
    return json.dumps(
        {
            "tool": "read_project_context",
            "project_brief": request.project_brief or "暂无项目记忆",
            "manuscript_chars": len(clean),
            "manuscript_excerpt": excerpt,
        },
        ensure_ascii=False,
    )


def status(state: str, label: str) -> dict[str, str]:
    return {"type": "status", "state": state, "label": label}


def chunk_text(text: str, size: int) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)]
