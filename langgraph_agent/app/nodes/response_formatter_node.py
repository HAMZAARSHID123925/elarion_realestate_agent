import logging
import json
from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

def response_formatter_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Response Formatter Node
    
    1. Responsibilities:
       - Takes property_search_result from state.
       - Uses Groq to convert the raw JSON/dict into a natural, friendly, 
         voice-optimized spoken response.
       - Outputs plain spoken sentences (no markdown, symbols, bullet points).
       
    2. Input State:
       - property_search_result: The result from the MCP tool.
       
    3. Output State:
       - voice_response: The final spoken text.
       - is_conversation_complete: Set to True.
    """
    search_result = state.get("property_search_result")
    
    updates: Dict[str, Any] = {
        "is_conversation_complete": True
    }
    
    try:
        if not search_result:
            updates["voice_response"] = "I'm sorry, but the property search service is temporarily unavailable."
            updates["messages"] = [AIMessage(content=updates["voice_response"])]
            return updates

        status = search_result.get("status")
        
        if status == "error":
            updates["voice_response"] = "I'm sorry, but the property search service is temporarily unavailable."
            updates["messages"] = [AIMessage(content=updates["voice_response"])]
            return updates
            
        count = search_result.get("count", 0)
        
        if count == 0:
            updates["voice_response"] = "I'm sorry, but I couldn't find any properties matching your exact criteria right now. Would you like to try searching with a different budget or in another location?"
            updates["messages"] = [AIMessage(content=updates["voice_response"])]
            return updates
            
        # We have results
        properties = search_result.get("properties", [])
        
        # Limit to top 3
        top_properties = properties[:3]
        
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        
        system_prompt = """You are a professional, friendly real estate receptionist making a voice call.
Your task is to take the JSON data about properties and read them naturally to the user.

CRITICAL VOICE RULES:
- ABSOLUTELY NO MARKDOWN (*, #, -, [], etc.)
- NO BULLET POINTS
- NO SYMBOLS
- Write exactly as you would speak it out loud. Use words for punctuation if needed, but mostly rely on commas and periods.
- Mention the total count of properties found.
- Describe at most 3 properties (title, price, and contact person).
- Read numbers naturally (e.g., 'one hundred and eighty lakhs').
- End with a friendly question: 'Which one interests you?'

Here is the data:
{property_data}
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt)
        ])
        
        chain = prompt | llm
        
        response = chain.invoke({
            "property_data": json.dumps({"count": count, "properties": top_properties})
        })
        
        voice_text = response.content.replace("*", "").replace("#", "").replace("-", "").replace("[", "").replace("]", "")
        
        updates["voice_response"] = voice_text
        updates["messages"] = [AIMessage(content=voice_text)]
        
        return updates
        
    except Exception as e:
        logger.error(f"Error in response_formatter_node: {e}")
        updates["voice_response"] = "I'm sorry, but the property search service is temporarily unavailable."
        updates["messages"] = [AIMessage(content=updates["voice_response"])]
        return updates
