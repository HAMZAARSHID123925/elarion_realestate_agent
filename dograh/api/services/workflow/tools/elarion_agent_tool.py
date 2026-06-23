import httpx
from typing import Any, Dict
from loguru import logger

# Global state store keyed by conversation_id to maintain state across turns
_STATE_STORE: Dict[str, Dict[str, Any]] = {}

def get_elarion_agent_tools() -> list[Dict[str, Any]]:
    """Get the Elarion Agent tool definitions for LLM function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "ask_elarion_agent",
                "description": "Send transcribed user speech to the Elarion Real Estate agent for processing.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "conversation_id": {
                            "type": "string",
                            "description": "Unique identifier for the conversation"
                        },
                        "message": {
                            "type": "string",
                            "description": "The exact user speech to process"
                        }
                    },
                    "required": ["conversation_id", "message"]
                }
            }
        }
    ]

async def ask_elarion_agent(conversation_id: str, message: str) -> str:
    """Send user speech to Elarion backend and return the voice_response."""
    logger.info(f"Asking Elarion Agent (conversation_id={conversation_id}): {message}")
    
    # Retrieve existing state or start fresh
    current_state = _STATE_STORE.get(conversation_id, {})
    
    payload = {
        "conversation_id": conversation_id,
        "message": message,
        "state": current_state
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("http://localhost:8001/chat", json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Save the updated state for next turn
            _STATE_STORE[conversation_id] = data.get("state", {})
            
            # Return just the voice response string back to Dograh
            return data.get("voice_response", "I'm sorry, I couldn't get a response right now.")
            
    except Exception as e:
        logger.error(f"Failed to communicate with Elarion endpoint: {e}")
        return "I'm sorry, but our services are currently unavailable. Please try again later."
