import logging
from typing import Literal

from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)


import os

def get_llm():
    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    return ChatGroq(model=model_name, temperature=0, max_tokens=600)


# Try to use the rate limiter from orchestrator if available
try:
    from app.orchestrator.rate_limiter import groq_queue
    HAS_GROQ_QUEUE = True
except ImportError:
    HAS_GROQ_QUEUE = False
    groq_queue = None


MANDATORY_SLOTS = [
    "tenant_identity",
    "property_unit",
    "issue_category",
    "issue_description",
    "urgency",
    "permission_to_enter",
    "pets_present"
]


class MaintenanceExtraction(BaseModel):
    tenant_identity: str | None = Field(default=None, description="The name of the tenant. Null if not mentioned.")
    property_unit: str | None = Field(default=None, description="The property or unit number (e.g. Unit 204, U-204, 204). Null if not mentioned.")
    issue_category: str | None = Field(
        default=None,
        description=(
            "The category of the maintenance issue: "
            "'plumbing', 'electrical', 'hvac', 'security', 'general'. Null if not mentioned."
        ),
    )
    issue_description: str | None = Field(default=None, description="Detailed description of the problem. Null if not mentioned.")
    urgency: str | None = Field(default=None, description="The urgency level: 'low', 'medium', 'high'. Null if not mentioned.")
    permission_to_enter: str | None = Field(default=None, description="Whether the tenant grants permission to enter ('yes', 'no', 'unconfirmed'). Null if not mentioned.")
    pets_present: str | None = Field(default=None, description="Whether there are pets ('yes', 'no', 'unconfirmed'). Null if not mentioned.")
