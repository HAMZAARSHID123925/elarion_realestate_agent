"""
Rent Renewal Workflow Nodes.
Handles lease expiration checks, standard 5% renewal offer generation, and tenant decision processing.
"""
import logging
from app.core_workflows.rent_renewal.state import RentRenewalState

logger = logging.getLogger(__name__)

def lease_check_node(state: RentRenewalState) -> dict:
    """Checks tenant lease details and calculates renewal terms."""
    logger.info("[Rent Renewal] Checking tenant lease status and calculating renewal terms...")
    current_rent = state.get("current_rent") or 75000.0
    # Standard 5% renewal increase
    offered_rent = round(current_rent * 1.05, 2)
    renewal_term = state.get("renewal_term_months") or 12

    user_text = ""
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        user_text = last_msg.get("content", "").lower() if isinstance(last_msg, dict) else str(last_msg).lower()

    tenant_decision = "pending"
    if "accept" in user_text or "agree" in user_text or "yes" in user_text:
        tenant_decision = "accepted"
    elif "reject" in user_text or "decline" in user_text or "no" in user_text or "move out" in user_text:
        tenant_decision = "rejected"
    elif "discount" in user_text or "lower" in user_text or "negotiate" in user_text:
        tenant_decision = "negotiating"

    return {
        "current_rent": current_rent,
        "offered_rent": offered_rent,
        "renewal_term_months": renewal_term,
        "tenant_decision": tenant_decision,
        "is_complete": False
    }

def renewal_offer_node(state: RentRenewalState) -> dict:
    """Presents the renewal offer to the tenant and formats decision summary."""
    logger.info("[Rent Renewal] Presenting lease renewal offer and formatting response...")
    decision = state.get("tenant_decision", "pending")
    offered_rent = state.get("offered_rent", 78750.0)
    current_rent = state.get("current_rent", 75000.0)
    term = state.get("renewal_term_months", 12)

    if decision == "accepted":
        response = f"Thank you! Your lease renewal for {term} months at PKR {offered_rent:,.2f}/month has been recorded. Our team will send the legal addendum shortly."
    elif decision == "rejected":
        response = f"We have recorded your decision not to renew. Our property manager will assist with the move-out inspection process."
    elif decision == "negotiating":
        response = f"Thank you for your feedback regarding the offered rate of PKR {offered_rent:,.2f}. Your negotiation request has been forwarded to the property owner for review."
    else:
        response = f"Your current lease is approaching renewal. We are pleased to offer a {term}-month renewal at PKR {offered_rent:,.2f}/month (previous: PKR {current_rent:,.2f}). Please reply ACCEPT to confirm or NEGOTIATE to discuss."

    return {
        "final_response": response,
        "is_complete": True
    }
