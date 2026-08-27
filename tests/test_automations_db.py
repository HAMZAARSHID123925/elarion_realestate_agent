"""
Database Integration Tests for Automations & Audit Logging.

Tests PostgreSQL database read, update, create, and audit trail operations for automations.
"""
import os
import sys
import asyncio
import pytest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.automation_repository import automation_repository
from database.audit_repository import audit_repository


@pytest.mark.asyncio
async def test_list_automations_db():
    """Verifies fetching initial seed automations from PostgreSQL database."""
    items = await automation_repository.list_automations()
    assert isinstance(items, list)
    assert len(items) >= 5, f"Expected at least 5 automations in DB, got {len(items)}"
    
    ids = [item["id"] for item in items]
    assert "maintenance_request" in ids
    assert "rent_reminder" in ids
    assert "resident_support" in ids
    assert "lease_renewal" in ids
    assert "owner_reporting" in ids


@pytest.mark.asyncio
async def test_get_automation_by_id_db():
    """Verifies fetching single automation by ID."""
    item = await automation_repository.get_automation_by_id("maintenance_request")
    assert item is not None
    assert item["id"] == "maintenance_request"
    assert item["name"] == "Maintenance Request"
    assert isinstance(item["escalation_conditions"], list)
    assert isinstance(item["channels"], list)


@pytest.mark.asyncio
async def test_update_automation_db():
    """Verifies updating escalation conditions & status in PostgreSQL DB + audit logging."""
    new_conditions = [
        "Updated Emergency Rule (e.g., flood)",
        "AI confidence < 90%",
        "Estimate > $1000 requires PM sign-off"
    ]

    updated = await automation_repository.update_automation(
        automation_id="maintenance_request",
        updates={
            "escalation_conditions": new_conditions,
            "channels": ["WhatsApp", "Email", "SMS", "Web"],
            "active": True
        },
        actor="test_manager@tenantflow.ai"
    )

    assert updated is not None
    assert updated["escalation_conditions"] == new_conditions
    assert "SMS" in updated["channels"]
    assert updated["status"] == "Active"

    # Re-fetch from DB to guarantee persistent storage
    refetched = await automation_repository.get_automation_by_id("maintenance_request")
    assert refetched["escalation_conditions"] == new_conditions
    assert "SMS" in refetched["channels"]


@pytest.mark.asyncio
async def test_create_custom_automation_db():
    """Verifies creating a new custom automation in PostgreSQL DB."""
    custom_name = "Security & Access Check"
    created = await automation_repository.create_automation(
        data={
            "name": custom_name,
            "status": "Active",
            "description": "Handles: Access card requests, security gate logs.",
            "tagline": "Automated security clearance and gate log processing.",
            "handles": ["Access card requests", "Security gate logs"],
            "channels": ["WhatsApp", "Email"],
            "escalation_conditions": ["Unrecognized guest", "Gate hardware failure"],
            "scope": "All Properties (42)",
            "icon_type": "support"
        },
        actor="admin@tenantflow.ai"
    )

    assert created is not None
    assert created["name"] == custom_name
    assert created["id"] == "security_access_check"

    # Verify audit log was created
    logs = await audit_repository.list_audit_logs(limit=10)
    actions = [l["action"] for l in logs]
    assert "CREATE_AUTOMATION" in actions or "UPDATE_AUTOMATION" in actions


@pytest.mark.asyncio
async def test_delete_automation_db():
    """Verifies deleting an automation from PostgreSQL DB + audit logging."""
    temp_name = "Temp Test Automation"
    created = await automation_repository.create_automation(
        data={"name": temp_name, "status": "Active"},
        actor="test_admin@tenantflow.ai"
    )
    temp_id = created["id"]

    # Perform deletion
    deleted = await automation_repository.delete_automation(temp_id, actor="test_admin@tenantflow.ai")
    assert deleted is True

    # Verify it no longer exists in DB
    refetched = await automation_repository.get_automation_by_id(temp_id)
    assert refetched is None or refetched["id"] != temp_id or refetched.get("status") == "Deleted"

    # Verify audit log recorded DELETE_AUTOMATION
    logs = await audit_repository.list_audit_logs(limit=10)
    actions = [l["action"] for l in logs]
    assert "DELETE_AUTOMATION" in actions


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_list_automations_db())
    asyncio.run(test_get_automation_by_id_db())
    asyncio.run(test_update_automation_db())
    asyncio.run(test_create_custom_automation_db())
    asyncio.run(test_delete_automation_db())
    print("\n[OK] All PostgreSQL Automations DB tests passed successfully!")
