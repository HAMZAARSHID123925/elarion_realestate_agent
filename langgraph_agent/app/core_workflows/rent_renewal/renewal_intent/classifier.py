"""
Renewal Intent Classifier — Phase 3, Workflow #4.

Understands natural-language tenant responses to renewal outreach.
Classifies responses into:
  - YES: Tenant wants to renew their lease.
  - NO: Tenant declines to renew and plans to vacate.
  - NEGOTIATION: Tenant wants to negotiate terms, rent, or lease duration.
  - UNCLEAR: Tenant's response is ambiguous, unrelated, or requires clarification.

Uses ChatGroq with structured outputs, backed by a deterministic keyword fallback.
"""
import os
import re
import logging
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

IntentType = Literal["YES", "NO", "UNCLEAR", "NEGOTIATION"]


class RenewalIntentResult(BaseModel):
    """Structured extraction of renewal intent from a tenant's response."""
    intent: IntentType = Field(
        description="Classified renewal intent: YES (wants renewal), NO (declines), NEGOTIATION (wants different terms/rent), UNCLEAR (ambiguous)"
    )
    confidence: float = Field(
        default=1.0,
        description="Confidence score between 0.0 and 1.0"
    )
    reasoning: str = Field(
        default="",
        description="Brief justification for the classification"
    )
    requested_term_months: Optional[int] = Field(
        default=None,
        description="Requested renewal duration in months (e.g. 6, 12, 24), if mentioned"
    )
    proposed_rent: Optional[float] = Field(
        default=None,
        description="Proposed or counter-offered monthly rent in PKR, if mentioned"
    )
    comments: Optional[str] = Field(
        default=None,
        description="Any specific tenant questions or comments"
    )


def _rule_based_fallback_classify(response_text: str) -> RenewalIntentResult:
    """
    Deterministic fallback rule engine for intent classification.
    Used when LLM or API keys are unavailable, or for offline evaluation.
    """
    text = (response_text or "").strip().lower()

    if not text:
        return RenewalIntentResult(
            intent="UNCLEAR",
            confidence=1.0,
            reasoning="Empty response received.",
        )

    # 1. Check for negotiation / terms bargaining
    negotiation_patterns = [
        r"\bdiscount\b", r"\blower rent\b", r"\breduce\b", r"\bnegotiat\w*\b",
        r"\bcheaper\b", r"\btoo high\b", r"\btoo expensive\b", r"\bcounter offer\b",
        r"\bcan you do\b", r"\bif the rent is\b", r"\brent increase\b",
        r"\bhow about\b", r"\bwhat if\b"
    ]
    for pattern in negotiation_patterns:
        if re.search(pattern, text):
            return RenewalIntentResult(
                intent="NEGOTIATION",
                confidence=0.90,
                reasoning=f"Detected negotiation phrasing matching pattern: '{pattern}'.",
            )

    # 2. Check for decline / non-renewal
    decline_patterns = [
        r"\bno\b", r"\bnot renewing\b", r"\bwon'?t renew\b", r"\bmoving out\b",
        r"\bleav\w*\b", r"\bvacat\w*\b", r"\brelocat\w*\b", r"\bfound another\b",
        r"\bmoving away\b", r"\bcannot stay\b", r"\bwill not continue\b"
    ]
    for pattern in decline_patterns:
        if re.search(pattern, text):
            return RenewalIntentResult(
                intent="NO",
                confidence=0.95,
                reasoning=f"Detected decline phrasing matching pattern: '{pattern}'.",
            )

    # 3. Check for positive renewal intent
    positive_patterns = [
        r"\byes\b", r"\brenew\b", r"\bstay\b", r"\bextend\b", r"\bcontinue\b",
        r"\bsign\b", r"\blove to stay\b", r"\bwant to continue\b", r"\bkeep living\b",
        r"\bwould like to renew\b", r"\bsure\b", r"\bdefinitely\b", r"\bcount me in\b",
        r"\bagree\b"
    ]
    for pattern in positive_patterns:
        if re.search(pattern, text):
            return RenewalIntentResult(
                intent="YES",
                confidence=0.95,
                reasoning=f"Detected positive renewal phrasing matching pattern: '{pattern}'.",
            )

    # 4. Fallback: Unclear / ambiguous
    return RenewalIntentResult(
        intent="UNCLEAR",
        confidence=0.75,
        reasoning="Tenant response did not contain clear affirmative, negative, or negotiation keywords.",
    )


async def classify_renewal_intent(
    tenant_response: str,
    lease_context: Optional[Dict[str, Any]] = None,
) -> RenewalIntentResult:
    """
    Classifies tenant renewal intent from natural language.

    Args:
        tenant_response: Natural language response from tenant.
        lease_context: Optional context dict (current_rent, property_address, etc.).

    Returns:
        RenewalIntentResult with classified intent, confidence, and reasoning.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.info("[Classifier] GROQ_API_KEY not set. Using deterministic rule-based classification.")
        return _rule_based_fallback_classify(tenant_response)

    try:
        from langchain_groq import ChatGroq
        from langchain_core.prompts import ChatPromptTemplate

        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        structured_llm = llm.with_structured_output(RenewalIntentResult)

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an AI Lease Operations Specialist for Elarion Property Management.\n"
             "Analyze the tenant's reply regarding their upcoming lease expiration and classify their intent.\n"
             "Strict Guidelines:\n"
             "- YES: Tenant confirms they want to renew, stay, or continue their tenancy.\n"
             "- NO: Tenant clearly declines renewal or states they are moving out / vacating.\n"
             "- NEGOTIATION: Tenant expresses interest in renewing but asks for a lower rent, discount, different duration, or custom terms.\n"
             "- UNCLEAR: Response is ambiguous, a general unrelated question, or insufficient to determine renewal plans.\n"
             "Extract any requested term duration or proposed rent amount if stated.\n"
             "Lease Context: {context}"),
            ("human", "Tenant Response: {response}"),
        ])

        formatted_context = str(lease_context or {})
        chain = prompt | structured_llm

        result: RenewalIntentResult = await chain.ainvoke({
            "context": formatted_context,
            "response": tenant_response,
        })
        logger.info(
            "LLM classified intent: intent=%s confidence=%.2f reasoning=%s",
            result.intent, result.confidence, result.reasoning
        )
        return result

    except Exception as e:
        logger.warning(
            "LLM intent classification failed (%s). Falling back to rule engine.",
            e, exc_info=True
        )
        return _rule_based_fallback_classify(tenant_response)
