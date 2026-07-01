from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class UnifiedRequest(BaseModel):
    """
    Standard schema that EVERY input channel (VAPI, WhatsApp, Email) 
    must convert its data into before sending to Layer 2.
    """
    channel: str = Field(description="The channel the message came from (e.g., 'vapi', 'whatsapp', 'email')")
    user_id: str = Field(description="Unique identifier for the user on that channel (phone number, email, etc.)")
    raw_text: str = Field(description="The actual text content or transcript of the message")
    channel_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Any extra metadata specific to the channel")

class UnifiedResponse(BaseModel):
    """
    Standard schema that Layer 2 outputs. This 'Task' object can be passed 
    to Layer 3 workflows or returned to the user.
    """
    intent: str = Field(description="Classified intent (e.g., 'maintenance', 'leasing', 'general')")
    urgency: str = Field(description="Assessed urgency (e.g., 'low', 'medium', 'high')")
    extracted_entities: Dict[str, Any] = Field(default_factory=dict, description="Details extracted from the text")
    action_taken: str = Field(description="What the orchestrator decided to do (e.g., 'routed_to_maintenance', 'human_escalation', 'need_more_info')")
    response_message: Optional[str] = Field(default=None, description="Message to send back to the user, if applicable")
