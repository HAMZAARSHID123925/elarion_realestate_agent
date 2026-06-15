from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class ConversationState(TypedDict):
    conversation_id: str
    user_name: Optional[str]
    user_city: Optional[str]
    user_goal: Optional[str]
    messages: Annotated[list[BaseMessage], add_messages]
    conversation_summary: Optional[str]
    is_conversation_complete: bool
