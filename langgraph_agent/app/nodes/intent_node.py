import logging
from typing import Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

logger = logging.getLogger(__name__)

class ExtractionSchema(BaseModel):
    """Schema for extracting real estate requirements from user input."""
    user_name: str | None = Field(default=None, description="The name of the user")
    location: str | None = Field(default=None, description="The city or location the user is interested in")
    budget: str | None = Field(default=None, description="The budget of the user for the property")
    property_type: str | None = Field(default=None, description="The type of property, e.g., house, apartment, plot")

def intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Receptionist Node (intent_node)
    
    1. Responsibilities:
       - Act like a professional real estate receptionist.
       - Collect all required information (user_name, location, budget, property_type).
       - Maintain conversation naturally.
       - Ask only for missing information, one piece at a time.
       - Update state fields.
       
    2. Input State:
       - messages: The conversation history.
       - user_name, location, budget, property_type: Extracted data so far.
       
    3. Output State:
       - Returns a dictionary with updated fields (e.g., location, budget).
       - Appends a new AIMessage to messages if a follow-up question is generated.
       - Sets next_step = "property_search" when all fields are successfully collected.
       
    4. Decision Logic:
       - Extracts entities from the latest user message via an LLM structured output.
       - Identifies which required fields are missing.
       - If any field is missing, uses the LLM to generate a natural, polite question asking for the FIRST missing field.
       - If all fields exist, returns next_step="property_search" and does not ask another question.
    """
    messages = state.get("messages", [])
    if not messages:
        # Fallback if graph is invoked with no messages
        return {"messages": [AIMessage(content="Hello! I'm your professional real estate assistant. How can I help you today?")]}

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # Extract information from the latest user message
        latest_message = messages[-1].content if messages[-1].type == "human" else ""
        updates: Dict[str, Any] = {}
        
        if latest_message:
            structured_llm = llm.with_structured_output(ExtractionSchema)
            extracted = structured_llm.invoke(
                f"Extract any real estate requirements from this message. "
                f"Only extract if explicitly mentioned.\nMessage: {latest_message}"
            )
            
            # Map extracted values to the state updates if they are new
            if extracted.user_name and not state.get("user_name"):
                updates["user_name"] = extracted.user_name
            if extracted.location and not state.get("location"):
                updates["location"] = extracted.location
            if extracted.budget and not state.get("budget"):
                updates["budget"] = extracted.budget
            if extracted.property_type and not state.get("property_type"):
                updates["property_type"] = extracted.property_type

        # Assess current completeness
        current_name = updates.get("user_name", state.get("user_name"))
        current_location = updates.get("location", state.get("location"))
        current_budget = updates.get("budget", state.get("budget"))
        current_property_type = updates.get("property_type", state.get("property_type"))
        
        missing_fields = []
        if not current_property_type: missing_fields.append("property type (e.g., house, apartment)")
        if not current_location: missing_fields.append("city or location")
        if not current_budget: missing_fields.append("budget")
        if not current_name: missing_fields.append("name")
        
        if not missing_fields:
            # All required fields collected
            updates["next_step"] = "property_search"
            return updates
            
        # Generate a conversational question for the FIRST missing field
        field_to_ask = missing_fields[0]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a professional and polite real estate receptionist. "
             "A user wants help with real estate. You need to ask them about their: {field_to_ask}. "
             "Ask ONLY for this specific information. Do not ask multiple questions at once. "
             "Maintain a natural, helpful conversation based on the context so far."),
            MessagesPlaceholder(variable_name="messages")
        ])
        
        chain = prompt | llm
        response = chain.invoke({
            "field_to_ask": field_to_ask,
            "messages": messages
        })
        
        updates["messages"] = [response]
        return updates
        
    except Exception as e:
        logger.error(f"Error in intent_node: {e}")
        return {"messages": [AIMessage(content="I'm sorry, I encountered an issue processing your request. Could you please repeat that?")]}
