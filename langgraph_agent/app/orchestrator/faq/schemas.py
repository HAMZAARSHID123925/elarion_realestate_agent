"""
Structured output models for the FAQ / Workflow #3 subgraph.
Same pattern as maintenance/nodes/common.py -- Pydantic model +
llm.with_structured_output(Model), so nodes downstream get clean
fields instead of free text.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class IntentClassification(BaseModel):
    """Design doc section 2.1 -- single classification call, before the conditional edge."""
    intent: Literal["KNOWLEDGE", "PROPERTY", "MIXED", "UNCLEAR"] = Field(
        description=(
            "KNOWLEDGE: policy / rules / process questions (e.g. pet policy, move-out process, "
            "deposit rules, visitor rules, parking rules). "
            "PROPERTY: availability / budget / location / bedroom search queries. "
            "MIXED: both a policy question and a property search request in the same message. "
            "UNCLEAR: no clear policy or property signal -- needs a follow-up question."
        )
    )


class GroundednessCheck(BaseModel):
    """
    Used inside rag_retrieve_node as the LLM self-check half of the confidence gate
    (design doc section 4, 'Confidence Checking': similarity threshold + LLM self-check).
    """
    is_supported: Literal["yes", "no"] = Field(description="'yes' if the retrieved chunks fully support answering the query, 'no' otherwise.")
    confidence: Literal["high", "medium", "low"] = Field(description="Overall confidence the retrieved context grounds a correct answer.")
    reason: str = Field(description="One short sentence explaining the confidence level.")


class PropertySlotExtraction(BaseModel):
    """Extracts property search slots from the user's message. Feeds collect_property_slots_node."""
    location: Optional[str] = Field(default=None, description="City or area mentioned. Null if not mentioned.")
    property_type: Optional[Literal["apartment", "house", "condo", "studio", "plot", "commercial"]] = Field(
        default=None, description="Type of property. Null if not mentioned."
    )
    budget: Optional[str] = Field(default=None, description="Budget as stated by the user, e.g. '200 lakhs', '1.5 crore'. Null if not mentioned.")
    bedrooms: Optional[int] = Field(default=None, description="Number of bedrooms requested. Null if not mentioned.")
