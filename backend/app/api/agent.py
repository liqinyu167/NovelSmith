import asyncio
import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

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

router = APIRouter()

RUNS: dict[str, AgentRunRequest] = {}
CHAT_RUNS: dict[str, AgentRunRequest] = {}


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


class CreateRunResponse(BaseModel):
    run_id: str


@router.post("/runs", response_model=CreateRunResponse)
async def create_run(payload: CreateRunRequest) -> CreateRunResponse:
    run_id = uuid.uuid4().hex
    RUNS[run_id] = AgentRunRequest(
        prompt=payload.prompt,
        manuscript=payload.manuscript,
        project_brief=payload.project_brief,
        base_url=payload.provider.base_url.strip(),
        api_key=payload.provider.api_key.strip(),
        model=payload.provider.model.strip(),
        write_plan=payload.write_plan,
    )
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
        )
    )


@router.post("/chats", response_model=CreateRunResponse)
async def create_chat(payload: CreateRunRequest) -> CreateRunResponse:
    run_id = uuid.uuid4().hex
    CHAT_RUNS[run_id] = AgentRunRequest(
        prompt=payload.prompt,
        manuscript=payload.manuscript,
        project_brief=payload.project_brief,
        base_url=payload.provider.base_url.strip(),
        api_key=payload.provider.api_key.strip(),
        model=payload.provider.model.strip(),
    )
    return CreateRunResponse(run_id=run_id)


@router.get("/chats/{run_id}/events")
async def chat_events(run_id: str) -> StreamingResponse:
    request = CHAT_RUNS.get(run_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Chat run not found")

    async def event_source() -> AsyncIterator[str]:
        try:
            async for event in stream_chat_events(request):
                yield encode_sse(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            yield encode_sse({"type": "error", "state": "error", "message": str(exc)})
        finally:
            CHAT_RUNS.pop(run_id, None)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str) -> StreamingResponse:
    request = RUNS.get(run_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_source() -> AsyncIterator[str]:
        try:
            async for event in stream_agent_events(request):
                yield encode_sse(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            yield encode_sse({"type": "error", "message": str(exc)})
        finally:
            RUNS.pop(run_id, None)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/providers/test")
async def test_provider(provider: ProviderConfig) -> dict[str, Any]:
    if not provider.base_url or not provider.model:
        return {"ok": False, "message": "Base URL and model are required."}
    return {"ok": True, "message": "Provider config shape is valid."}


def encode_sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
