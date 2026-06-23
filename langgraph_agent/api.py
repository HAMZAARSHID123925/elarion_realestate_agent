import os
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# Load .env file
load_dotenv()

import sys

# Add the project root to sys.path so that mcp_servers can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the compiled graph
from app.graph import graph
from app.state import ConversationState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="ELARION Real Estate Agent API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    state: Dict[str, Any] = {}

class ChatResponse(BaseModel):
    voice_response: Optional[str]
    state: Dict[str, Any]

def _serialize_message(msg: BaseMessage) -> Dict[str, Any]:
    """Serialize a LangChain message to a dict."""
    return {"type": msg.type, "content": msg.content}

def _deserialize_message(msg_dict: Dict[str, Any]) -> BaseMessage:
    """Deserialize a dict to a LangChain message."""
    if msg_dict["type"] == "human":
        return HumanMessage(content=msg_dict["content"])
    elif msg_dict["type"] == "ai":
        return AIMessage(content=msg_dict["content"])
    else:
        # Fallback for other message types
        return BaseMessage(content=msg_dict["content"], type=msg_dict["type"])

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Process a chat message using the LangGraph agent.
    """
    try:
        # Rebuild ConversationState from request
        state_dict = request.state
        
        # Deserialize messages
        messages_data = state_dict.get("messages", [])
        deserialized_messages = [_deserialize_message(m) if isinstance(m, dict) else m for m in messages_data]
        
        # Append new HumanMessage
        if request.message:
            deserialized_messages.append(HumanMessage(content=request.message))
            
        # Prepare input state for the graph
        input_state = ConversationState(
            conversation_id=request.conversation_id,
            user_name=state_dict.get("user_name"),
            location=state_dict.get("location"),
            user_goal=state_dict.get("user_goal"),
            budget=state_dict.get("budget"),
            property_type=state_dict.get("property_type"),
            messages=deserialized_messages,
            conversation_summary=state_dict.get("conversation_summary"),
            is_conversation_complete=state_dict.get("is_conversation_complete", False),
            next_step=state_dict.get("next_step"),
            property_search_result=state_dict.get("property_search_result"),
            voice_response=state_dict.get("voice_response")
        )
        
        # Invoke the graph
        result_state = graph.invoke(input_state)
        
        # Serialize messages for the response
        serialized_messages = [_serialize_message(m) for m in result_state.get("messages", [])]
        
        # Build the final response state dict
        final_state = {
            "conversation_id": result_state.get("conversation_id"),
            "user_name": result_state.get("user_name"),
            "location": result_state.get("location"),
            "user_goal": result_state.get("user_goal"),
            "budget": result_state.get("budget"),
            "property_type": result_state.get("property_type"),
            "messages": serialized_messages,
            "conversation_summary": result_state.get("conversation_summary"),
            "is_conversation_complete": result_state.get("is_conversation_complete", False),
            "next_step": result_state.get("next_step"),
            "property_search_result": result_state.get("property_search_result"),
            "voice_response": result_state.get("voice_response")
        }
        
        voice_response = result_state.get("voice_response")
        
        # If the graph didn't generate a voice_response directly but there's a new AIMessage
        if not voice_response and result_state.get("messages"):
            last_message = result_state["messages"][-1]
            if last_message.type == "ai":
                voice_response = last_message.content
                
        return ChatResponse(
            voice_response=voice_response,
            state=final_state
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
