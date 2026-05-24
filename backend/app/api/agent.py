import asyncio
import json
import uuid
import time
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.agent_runtime import (
    AgentRunRequest,
    WritePlanRequest,
    classify_intent,
    create_write_plan,
    stream_agent_events,
    stream_chat_events,
)
from app.services.http_client import get_client
from app.services.url_validator import validate_base_url
from app.exceptions import InvalidBaseURLError

logger = logging.getLogger("novelsmith.api.agent")

router = APIRouter()

RUNS: dict[str, AgentRunRequest] = {}
CHAT_RUNS: dict[str, AgentRunRequest] = {}
RUN_TIMESTAMPS: dict[str, float] = {}


class ProviderConfig(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""


class CreateRunRequest(BaseModel):
    prompt: str = Field(min_length=1)
    manuscript: str = ""
    project_brief: str = ""
    write_plan: dict[str, Any] | None = None
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    active_file_path: str = ""
    active_file_content: str = ""


class CreateRunResponse(BaseModel):
    run_id: str


def _cleanup_old_runs():
    now = time.time()
    expired = [rid for rid, t in RUN_TIMESTAMPS.items() if now - t > 600]
    if expired:
        logger.info(f"Cleaning up {len(expired)} expired runs")
        for rid in expired:
            RUNS.pop(rid, None)
            CHAT_RUNS.pop(rid, None)
            RUN_TIMESTAMPS.pop(rid, None)


@router.post("/runs", response_model=CreateRunResponse)
async def create_run(payload: CreateRunRequest) -> CreateRunResponse:
    _cleanup_old_runs()
    run_id = uuid.uuid4().hex
    RUNS[run_id] = AgentRunRequest(
        prompt=payload.prompt,
        manuscript=payload.manuscript,
        project_brief=payload.project_brief,
        base_url=payload.provider.base_url.strip(),
        api_key=payload.provider.api_key.strip(),
        model=payload.provider.model.strip(),
        write_plan=payload.write_plan,
        active_file_path=payload.active_file_path,
        active_file_content=payload.active_file_content,
    )
    RUN_TIMESTAMPS[run_id] = time.time()
    return CreateRunResponse(run_id=run_id)


@router.post("/plans")
async def plan_write(payload: CreateRunRequest) -> dict[str, Any]:
    return await create_write_plan(
        WritePlanRequest(
            prompt=payload.prompt,
            manuscript=payload.manuscript,
            project_brief=payload.project_brief,
            base_url=payload.provider.base_url.strip(),
            api_key=payload.provider.api_key.strip(),
            model=payload.provider.model.strip(),
            active_file_path=payload.active_file_path,
            active_file_content=payload.active_file_content,
        )
    )


@router.post("/intents")
async def detect_intent(payload: CreateRunRequest) -> dict[str, Any]:
    return await classify_intent(
        AgentRunRequest(
            prompt=payload.prompt,
            manuscript=payload.manuscript,
            project_brief=payload.project_brief,
            base_url=payload.provider.base_url.strip(),
            api_key=payload.provider.api_key.strip(),
            model=payload.provider.model.strip(),
            active_file_path=payload.active_file_path,
            active_file_content=payload.active_file_content,
        )
    )


@router.post("/chats", response_model=CreateRunResponse)
async def create_chat(payload: CreateRunRequest) -> CreateRunResponse:
    _cleanup_old_runs()
    run_id = uuid.uuid4().hex
    CHAT_RUNS[run_id] = AgentRunRequest(
        prompt=payload.prompt,
        manuscript=payload.manuscript,
        project_brief=payload.project_brief,
        base_url=payload.provider.base_url.strip(),
        api_key=payload.provider.api_key.strip(),
        model=payload.provider.model.strip(),
        active_file_path=payload.active_file_path,
        active_file_content=payload.active_file_content,
    )
    RUN_TIMESTAMPS[run_id] = time.time()
    return CreateRunResponse(run_id=run_id)


async def stream_events_helper(run_id: str, is_chat: bool) -> StreamingResponse:
    request = CHAT_RUNS.get(run_id) if is_chat else RUNS.get(run_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_source() -> AsyncIterator[str]:
        try:
            stream = stream_chat_events(request) if is_chat else stream_agent_events(request)
            async for event in stream:
                yield encode_sse(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Error in SSE event stream helper")
            yield encode_sse({"type": "error", "state": "error", "message": str(exc)})
        finally:
            CHAT_RUNS.pop(run_id, None)
            RUNS.pop(run_id, None)
            RUN_TIMESTAMPS.pop(run_id, None)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chats/{run_id}/events")
async def chat_events(run_id: str) -> StreamingResponse:
    return await stream_events_helper(run_id, is_chat=True)


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str) -> StreamingResponse:
    return await stream_events_helper(run_id, is_chat=False)


@router.post("/providers/test")
async def test_provider(provider: ProviderConfig) -> dict[str, Any]:
    if not provider.base_url or not provider.model:
        return {"ok": False, "message": "Base URL and model are required."}
    
    url = provider.base_url.strip()
    try:
        validate_base_url(url)
    except InvalidBaseURLError as e:
        return {"ok": False, "message": f"连接测试失败: {str(e)}"}

    client = get_client()
    try:
        # Check standard paths /models first to see if API works
        test_url = url.rstrip('/') + "/models"
        response = await client.get(
            test_url, 
            timeout=5.0, 
            headers={"Authorization": f"Bearer {provider.api_key}"}
        )
        if response.status_code in {404, 405}:
            # Fallback to the direct base URL
            response = await client.get(url, timeout=5.0)
        
        # Any response code under 500 implies connectivity (401 means credentials issues but server is there)
        if response.status_code < 500:
            return {"ok": True, "message": "连接测试成功！已成功连接到大模型接口。"}
        else:
            return {"ok": False, "message": f"服务器返回了错误状态码: {response.status_code}"}
    except httpx.HTTPError as e:
        return {"ok": False, "message": f"连接失败: {str(e)}"}
    except Exception as e:
        return {"ok": False, "message": f"未知错误: {str(e)}"}


def encode_sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
