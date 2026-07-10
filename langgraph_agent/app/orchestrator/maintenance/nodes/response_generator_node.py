from typing import Dict, Any

from app.orchestrator.maintenance.state import MaintenanceState


async def response_generator_node(state: MaintenanceState) -> Dict[str, Any]:
    """Confirmation back to caller."""
    if state.get("ticket_creation_status") == "error":
        return {
            "final_response": "I'm having trouble saving this right now due to a system error, but a team member will follow up shortly regarding your request."
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
