import asyncio
import json
from collections.abc import AsyncIterator

import httpx
from pydantic import BaseModel


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
        return demo_write_plan(request)

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
    yield status("planning", "读取当前正文与项目记忆")
    await asyncio.sleep(0.12)
    yield status("preparing", "组装写作上下文")

    if not request.base_url or not request.model or not request.api_key:
        async for event in stream_demo():
            yield event
        return

    yield status("connecting", f"连接模型 {request.model}")
    await asyncio.sleep(0.05)
    yield status("writing", "模型正在生成正文")

    async for token in stream_openai_compatible(request):
        yield {"type": "manuscript_delta", "state": "writing", "text": token}

    yield {"type": "done", "state": "done"}


async def stream_chat_events(request: AgentRunRequest) -> AsyncIterator[dict]:
    yield status("preparing", "读取项目记忆与当前正文状态")
    context = build_context_tool_result(request)
    yield {"type": "tool_result", "state": "preparing", "name": "read_project_context", "content": context}

    if not request.base_url or not request.model or not request.api_key:
        text = "我可以先和你讨论创作方向、设定、角色、结构，也可以在你明确要求写入正文时进入确认流程。当前没有配置 API，所以这是本地演示回复。"
        for chunk in chunk_text(text, 10):
            await asyncio.sleep(0.04)
            yield {"type": "assistant_delta", "state": "writing", "text": chunk}
        yield {"type": "done", "state": "done"}
        return

    yield status("connecting", f"连接模型 {request.model}")
    messages = [
        {
            "role": "system",
            "content": (
                "You are NovelSmith Director Agent. You can chat normally in Chinese and help with novel planning, settings, characters, style, and workflow. "
                "Do not write into the manuscript unless the user explicitly asks to write/continue/rewrite/polish/insert manuscript text. "
                "When answering, be concise and useful. You have tool context about the current project."
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
    async for token in stream_openai_compatible_messages(request, messages, temperature=0.65):
        yield {"type": "assistant_delta", "state": "writing", "text": token}
    yield {"type": "done", "state": "done"}


async def stream_demo() -> AsyncIterator[dict]:
    yield status("demo", "未配置 API，正在使用本地演示文本")
    sample = (
        "\n\n雨从旧城区的天桥缝隙里落下来，像一整座城市没有说出口的秘密。\n\n"
        "林烬把那封信握在掌心。纸面很干，干得不像刚从雨夜里来，"
        "封口处却沾着一点银色的蜡，里面压着他自己的指纹。\n\n"
        "信上只有一行字：\n\n"
        "> 十年后的你已经失败。今晚不要回家。\n\n"
        "他抬起头，街对面的霓虹灯忽然全部熄灭。黑暗里，有人用他的声音轻轻笑了一下。\n"
    )
    for chunk in chunk_text(sample, 8):
        await asyncio.sleep(0.055)
        yield {"type": "manuscript_delta", "state": "writing", "text": chunk}
    yield {"type": "done", "state": "done"}


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
    strong_write_words = ["续写", "改写", "润色", "扩写", "生成正文", "插入", "补一段", "写一段", "写入"]
    weak_write_words = ["写", "开头", "结尾", "章节"]
    question_words = ["怎么", "为什么", "讨论", "分析", "配置", "状态", "能不能", "是什么", "建议", "架构", "？", "?"]
    if any(word in prompt for word in strong_write_words):
        return {"action": "write", "reason": "检测到明确写作/写入意图"}
    if any(word in prompt for word in weak_write_words) and not any(word in prompt for word in question_words):
        return {"action": "write", "reason": "检测到写作请求"}
    return {"action": "chat", "reason": "普通对话或工具咨询"}


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
