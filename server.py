"""
AWCEE Agent Server — FastAPI + claude_agent_sdk
Expose les agents kevinrgu via REST API + SSE streaming
AWCEE-V3 Next.js appelle ce serveur au lieu du runtime TypeScript
"""

import asyncio
import json
import os
import importlib
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AWCEE Agent Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── AGENT REGISTRY ────────────────────────────────────────────

AGENTS = {
    "agent-sourcing-manager": {"module": "agent_marc", "name": "Marc Marcello", "model": "sonnet"},
    "agent-executive-intelligence": {"module": "agent_igor", "name": "Igor", "model": "opus"},
    "agent-pac-expert": {"module": "agent_marie", "name": "Marie Dupont", "model": "sonnet"},
    "agent-sinistre-auto": {"module": "agent_lucas", "name": "Lucas Martin", "model": "sonnet"},
    "agent-daf": {"module": "agent_alexandre", "name": "Alexandre", "model": "sonnet"},
    "awcee-generalist": {"module": "agent_general", "name": "Agent General", "model": "haiku"},
}

def _load_agent_module(agent_id: str):
    """Load agent module and return get_options + SYSTEM_PROMPT."""
    cfg = AGENTS.get(agent_id)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    mod = importlib.import_module(cfg["module"])
    return mod


# ── MODELS ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    agent_id: str
    message: str
    session_id: str | None = None

class ChatResponse(BaseModel):
    agent_id: str
    agent_name: str
    response: str
    session_id: str
    cost_usd: float | None = None
    turns: int | None = None
    duration_ms: int | None = None


# ── ENDPOINTS ─────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "agents": len(AGENTS), "timestamp": datetime.utcnow().isoformat()}


@app.get("/agents")
async def list_agents():
    return [
        {"id": k, "name": v["name"], "model": v["model"]}
        for k, v in AGENTS.items()
    ]


@app.post("/agents/{agent_id}/chat", response_model=ChatResponse)
async def chat(agent_id: str, req: ChatRequest):
    """Send a message to an agent and get a response."""
    mod = _load_agent_module(agent_id)
    cfg = AGENTS[agent_id]
    session_id = req.session_id or f"ses_{int(datetime.utcnow().timestamp())}_{os.urandom(4).hex()}"

    from claude_agent_sdk import ClaudeSDKClient, ResultMessage

    opts = mod.get_options()
    response_text = ""
    cost_usd = None
    turns = 0
    duration_ms = 0

    try:
        async with ClaudeSDKClient(options=opts) as client:
            await client.query(req.message)
            async for msg in client.receive_response():
                if isinstance(msg, ResultMessage):
                    cost_usd = getattr(msg, 'total_cost_usd', None)
                    turns = getattr(msg, 'num_turns', 0)
                    duration_ms = getattr(msg, 'duration_ms', 0)
                else:
                    # Extract text from assistant messages
                    from claude_agent_sdk.types import AssistantMessage, TextBlock
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                response_text += block.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(
        agent_id=agent_id,
        agent_name=cfg["name"],
        response=response_text,
        session_id=session_id,
        cost_usd=cost_usd,
        turns=turns,
        duration_ms=duration_ms,
    )


@app.post("/agents/{agent_id}/stream")
async def stream_chat(agent_id: str, req: ChatRequest):
    """SSE streaming — compatible with AWCEE-V3 frontend EventSource."""
    mod = _load_agent_module(agent_id)
    cfg = AGENTS[agent_id]
    session_id = req.session_id or f"ses_{int(datetime.utcnow().timestamp())}_{os.urandom(4).hex()}"

    async def event_stream() -> AsyncGenerator[str, None]:
        from claude_agent_sdk import ClaudeSDKClient, ResultMessage
        from claude_agent_sdk.types import AssistantMessage, TextBlock, ToolUseBlock

        yield f"event: start\ndata: {json.dumps({'session_id': session_id, 'agent_id': agent_id, 'agent_name': cfg['name']})}\n\n"

        opts = mod.get_options()
        full_response = ""

        try:
            async with ClaudeSDKClient(options=opts) as client:
                await client.query(req.message)
                async for msg in client.receive_response():
                    if isinstance(msg, ResultMessage):
                        yield f"event: done\ndata: {json.dumps({'response': full_response, 'cost_usd': getattr(msg, 'total_cost_usd', None), 'turns': getattr(msg, 'num_turns', 0), 'duration_ms': getattr(msg, 'duration_ms', 0)})}\n\n"
                    elif isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                full_response += block.text
                                yield f"event: token\ndata: {json.dumps({'token': block.text})}\n\n"
                            elif isinstance(block, ToolUseBlock):
                                yield f"event: action\ndata: {json.dumps({'tool': block.name, 'status': 'running'})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ── RUN ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100, log_level="info")
