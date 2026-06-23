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

from app.graph import graph
from app.state import ConversationState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ELARION VAPI Agent API")

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

def _rebuild_state_from_messages(lc_messages: List[BaseMessage]) -> ConversationState:
    """
    Since VAPI doesn't store our complex custom state, we use the message history 
    and let the LangGraph re-infer the missing pieces if needed, or we just pass the history.
    """
    # Create an initial empty state with a dummy conversation_id
    state = ConversationState(
        conversation_id="vapi_call_123",
        messages=lc_messages[:-1] # All except the last one (which we will process)
    )
    return state

@app.post("/vapi/chat/completions")
async def vapi_chat_completions(request: Request):
    """
    OpenAI-compatible endpoint for VAPI Custom LLM.
    """
    body = await request.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    
    logger.info(f"Received VAPI request: stream={stream}, num_messages={len(messages)}")

    # Convert messages
    lc_messages = _parse_vapi_messages(messages)
    
    # We need to process the latest user message
    if not lc_messages or not isinstance(lc_messages[-1], HumanMessage):
        # Fallback empty state
        input_state = ConversationState(conversation_id="vapi", messages=[])
    else:
        latest_message = lc_messages[-1]
        input_state = ConversationState(
            conversation_id="vapi",
            messages=lc_messages
        )

    # In a production app, you might want to run `graph.astream_events` to stream tokens as they are generated.
    # Because Groq is extremely fast, we can `invoke` and then stream the result text if `stream=True`.
    
    try:
        # Invoke the LangGraph brain
        result_state = graph.invoke(input_state)
        
        # Extract the spoken response
        voice_response = result_state.get("voice_response")
        
        if not voice_response and result_state.get("messages"):
            last_message = result_state["messages"][-1]
            if last_message.type == "ai":
                voice_response = last_message.content
                
        if not voice_response:
            voice_response = "I'm not sure how to respond to that."
            
    except Exception as e:
        logger.error(f"Error processing VAPI request: {e}")
        voice_response = "I'm sorry, I encountered an error."

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
