import logging
from typing import Literal

from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)


def get_llm():
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


# Try to use the rate limiter from orchestrator if available
try:
    from app.orchestrator.rate_limiter import groq_queue
    HAS_GROQ_QUEUE = True
except ImportError:
    HAS_GROQ_QUEUE = False
    groq_queue = None


# In-memory fake dictionaries for Stage 1
FAKE_TENANT_DB = {
    "+923001234567": {"name": "Hamza Arshid", "unit": "Apt 4B"},
    "tenant@example.com": {"name": "John Doe", "unit": "House 12"}
}

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
    property_unit: str | None = Field(default=None, description="The property or unit number. Null if not mentioned.")
    issue_category: Literal["plumbing", "electrical", "hvac", "general", "security"] | None = Field(
        default=None,
        description=(
            "The category of the maintenance issue. Must be exactly one of: "
            "'plumbing' (leaks, pipes, drains, toilets, sinks, water heaters), "
            "'electrical' (outlets, wiring, breakers, lighting), "
            "'hvac' (heating, cooling, AC, furnace, ventilation), "
            "'security' (locks, doors, windows, alarms, access control), "
            "'general' (anything else — cabinets, appliances, cosmetic, structural, pests, misc repairs). "
            "Always map the tenant's description to the closest matching category, even if their "
            "wording is different (e.g. 'my cabinet door fell off' -> 'general'). Null only if no "
            "issue has been described yet at all."
        ),
    )
    issue_description: str | None = Field(default=None, description="Detailed description of the problem. Null if not mentioned.")
    urgency: Literal["low", "medium", "high"] | None = Field(default=None, description="The urgency level. MUST be exactly one of 'low', 'medium', or 'high'. DO NOT use 'EMERGENCY'. Default to 'low' for cosmetic issues like painting or minor touch-ups. Map any fire, flood, active danger, or life-threatening situation to 'high'. Null only if urgency has not been mentioned.")
    permission_to_enter: Literal["yes", "no", "unconfirmed"] | None = Field(default=None, description="Whether the tenant grants permission to enter. If asked but not clearly answered, use 'unconfirmed'. Null if not mentioned.")
    pets_present: Literal["yes", "no", "unconfirmed"] | None = Field(default=None, description="Whether there are pets. If asked but not clearly answered, use 'unconfirmed'. Null if not mentioned.")
