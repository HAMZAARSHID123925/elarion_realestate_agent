from typing import Dict, Any

from app.orchestrator.maintenance.state import MaintenanceState


async def request_builder_node(state: MaintenanceState) -> Dict[str, Any]:
    """Assembles validated slots into payload."""
    payload = {
        # Prefer resolved DB IDs; fall back to conversation-extracted values
        "tenant_id": state.get("db_tenant_id") or state.get("tenant_identity"),
        "unit_id": state.get("db_unit_id") or state.get("property_unit"),
        "category": state.get("issue_category"),
        "description": state.get("issue_description"),
        "urgency": state.get("urgency"),
        "permission_to_enter": state.get("permission_to_enter"),
        "pets_present": state.get("pets_present")
    }
    return {"ticket_payload": payload}
