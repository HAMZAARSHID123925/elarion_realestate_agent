import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage

load_dotenv()

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.pipeline import handle_request
from app.checkpointer import close_checkpointer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ELARION VAPI Agent API")


@app.get("/health")
async def health_check():
    # Added per item 5.13 of the production readiness review ("add basic
    # uptime monitoring") -- whatsapp_server.py already had this; vapi_server.py
    # didn't, which meant docker-compose / any external monitor had nothing
    # to poll to know this process was alive.
    return {"status": "healthy"}


def _parse_vapi_messages(messages: List[Dict[str, Any]]) -> List[BaseMessage]:
    """Convert OpenAI-format messages from VAPI to Langchain format."""
    lc_messages = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        elif role == "system":
            lc_messages.append(SystemMessage(content=content))
    return lc_messages

@app.post("/vapi/chat/completions")
async def vapi_chat_completions(request: Request):
    """
    OpenAI-compatible endpoint for VAPI Custom LLM.

    Now routes through the master pipeline (app/pipeline.py) instead of talking
    to Workflow 1 (property search) directly -- this is what actually connects
    VAPI to the Layer 2 orchestrator and, through it, to maintenance/FAQ/property
    search rather than being locked into property search alone.
    """
    body = await request.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    # VAPI includes a stable call id on every request for a given phone call --
    # this becomes the pipeline's thread_id, so the checkpointer treats every
    # turn of the same call as one continuous conversation. Falls back to a
    # fixed id only for manual/local testing without a real VAPI call object.
    call_id = body.get("call", {}).get("id") or "vapi-dev-session"

    logger.info(f"Received VAPI request: stream={stream}, num_messages={len(messages)}, call_id={call_id}")

    # Convert messages, pull out just this turn's user text -- the pipeline's
    # checkpointer (keyed by call_id) supplies prior-turn memory, so we don't
    # need to resend/re-parse the full transcript on every request the way
    # Workflow 1 alone used to require.
    lc_messages = _parse_vapi_messages(messages)
    user_text = ""
    if lc_messages and isinstance(lc_messages[-1], HumanMessage):
        user_text = lc_messages[-1].content

    try:
        voice_response = await handle_request(
            channel="vapi",
            user_id=call_id,
            raw_text=user_text,
            channel_metadata={"session_id": call_id},
        )
    except Exception as e:
        logger.error(f"Error processing VAPI request: {e}")
        voice_response = "I'm sorry, I encountered an error."

    if not voice_response:
        voice_response = "I'm not sure how to respond to that."

    if stream:
        async def generate_sse():
            chunk_id = "chatcmpl-vapi"
            # VAPI wants standard OpenAI SSE chunks
            # We split the response into chunks to simulate streaming
            words = voice_response.split(" ")
            for i, word in enumerate(words):
                content = word + " " if i < len(words) - 1 else word
                chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0.01) # small delay for stream pacing
            
            # Final chunk
            final_chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
            
        return StreamingResponse(generate_sse(), media_type="text/event-stream")
    else:
        # Non-streaming response
        return {
            "id": "chatcmpl-vapi",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": voice_response
                },
                "finish_reason": "stop"
            }]
        }

@app.on_event("shutdown")
async def _on_shutdown():
    await close_checkpointer()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
