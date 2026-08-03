from typing import Dict, Any

from app.core_workflows.maintenance.state import MaintenanceState


async def response_generator_node(state: MaintenanceState) -> Dict[str, Any]:
    """Confirmation back to caller."""
    if state.get("ticket_creation_status") == "error":
        error_reason = (state.get("ticket_creation_error") or "").lower()

        # ticket_creation_node sets this specific wording when tenant_id/unit_id never
        # resolved to a real DB record (e.g. name typed in chat doesn't match any tenant).
        # That's a different situation for the tenant than a DB/network outage, so it gets
        # a different, honest message instead of one generic line for every failure type.
        #
        # Neither message claims a human has been notified -- there is no automated human
        # handoff wired up anywhere in this project yet (escalation_node.py's TODO makes
        # this explicit). Claiming "I've handed this to a team member" would be false, so
        # both branches instead tell the tenant to reach out directly.
        if "could not verify tenant/unit" in error_reason:
            return {
                "final_response": (
                    "I wasn't able to match you to a unit in our records, so I couldn't "
                    "create a maintenance ticket automatically. Please contact our leasing "
                    "office directly so a team member can look into this for you."
                )
            }

        # Any other failure (DB/network outage, MCP timeout, etc.) -- genuinely a system
        # error on our side, not something the tenant did.
        return {
            "final_response": (
                "I'm currently facing a system issue and wasn't able to save your "
                "request. Please contact our office directly so someone can help you "
                "with this in the meantime."
            )
        }

    assignment_status = state.get("assignment_status")
    vendor = state.get("vendor_candidate") or {}

    if assignment_status == "ASSIGNED":
        return {
            "final_response": (
                f"Thank you. Your maintenance request has been created and assigned to "
                f"{vendor.get('name', 'a technician')}. They'll be in touch shortly."
            )
        }
    elif assignment_status == "NEEDS_MANUAL_ASSIGNMENT":
        return {
            "final_response": "Thank you. Your maintenance request has been created. Our coordinator will personally assign a technician and follow up shortly."
        }
    return {
        "final_response": "Thank you. Your maintenance request has been successfully created. Our team will be notified shortly."
    }
