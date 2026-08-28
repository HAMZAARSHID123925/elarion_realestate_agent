import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.server import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-admin-token"}

def test_dashboard_metrics(auth_headers):
    mock_metrics = {"total_properties": 10, "total_tenants": 25}
    with patch("database.dashboard_repository.dashboard_repository.get_overview_metrics", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_metrics
        response = client.get("/api/v1/dashboard/metrics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_properties"] == 10
    assert data["total_tenants"] == 25

def test_leases_list(auth_headers):
    mock_leases = [{"lease_id": "L-001", "tenant_id": "T-100", "property_id": "P-100", "lease_start_date": "2026-01-01", "lease_end_date": "2026-12-31", "monthly_rent": 1000.0, "status": "active"}]
    with patch("database.lease_repository.lease_repository.list_leases", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_leases
        response = client.get("/api/v1/leases", headers=auth_headers)
    assert response.status_code == 200

def test_renewals_list(auth_headers):
    mock_renewals = [{"reminder_id": 1, "lease_id": "L-001", "tenant_id": "T-100", "channel": "email", "recipient": "test@test.com", "reminder_type": "day_90", "status": "sent", "sent_at": "2026-08-19T00:00:00Z"}]
    with patch("database.renewal_repository.renewal_repository.list_renewal_reminders", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_renewals
        response = client.get("/api/v1/renewals/reminders", headers=auth_headers)
    assert response.status_code == 200
    
def test_escalations_list(auth_headers):
    mock_escalations = [{"escalation_id": 1, "lease_id": "L-001", "tenant_id": "T-100", "escalation_reason": "No response", "escalation_priority": "high", "status": "OPEN"}]
    with patch("database.escalation_repository.escalation_repository.list_escalations", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_escalations
        response = client.get("/api/v1/escalations", headers=auth_headers)
    assert response.status_code == 200
    
def test_documents_list(auth_headers):
    mock_documents = [{"document_id": 1, "lease_id": "L-001", "tenant_id": "T-100", "doc_type": "lease", "file_name": "lease.pdf", "status": "uploaded", "uploaded_at": "2026-08-19T00:00:00Z"}]
    with patch("database.document_repository.document_repository.list_documents", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_documents
        response = client.get("/api/v1/documents", headers=auth_headers)
    assert response.status_code == 200

def test_property_create_and_update(auth_headers):
    with patch("database.property_repository.property_repository.create_property", new_callable=AsyncMock) as mock_create, \
         patch("database.property_repository.property_repository.update_property", new_callable=AsyncMock) as mock_update, \
         patch("database.property_repository.property_repository.get_property_by_id", new_callable=AsyncMock) as mock_get:
        
        mock_create.return_value = "PROP-NEW1"
        mock_update.return_value = True
        mock_get.return_value = {"property_id": "PROP-NEW1", "address": "123 Dashboard St", "city": "UpdatedCity", "price_lakhs": 500.0}
        
        # Create
        create_res = client.post("/api/v1/properties", json={
            "address": "123 Dashboard St",
            "city": "TestCity",
            "property_type": "commercial",
            "price_lakhs": 500.0
        }, headers=auth_headers)
        assert create_res.status_code == 201
        prop_id = create_res.json()["property_id"]
        
        # Update
        update_res = client.patch(f"/api/v1/properties/{prop_id}", json={
            "city": "UpdatedCity"
        }, headers=auth_headers)
        assert update_res.status_code == 200
        assert update_res.json()["city"] == "UpdatedCity"

def test_tenant_create_and_update(auth_headers):
    with patch("database.property_repository.property_repository.create_property", new_callable=AsyncMock) as mock_prop_create, \
         patch("database.property_repository.property_repository.get_property_by_id", new_callable=AsyncMock) as mock_prop_get, \
         patch("database.tenant_repository.tenant_repository.create_tenant", new_callable=AsyncMock) as mock_create, \
         patch("database.tenant_repository.tenant_repository.update_tenant", new_callable=AsyncMock) as mock_update, \
         patch("database.tenant_repository.tenant_repository.get_tenant_by_id", new_callable=AsyncMock) as mock_get:
        
        mock_prop_create.return_value = "PROP-NEW2"
        mock_prop_get.return_value = {"property_id": "PROP-NEW2", "address": "456 Tenant St", "price_lakhs": 0.0}
        mock_create.return_value = "T-NEW1"
        mock_update.return_value = True
        mock_get.return_value = {"tenant_id": "T-NEW1", "tenant_name": "Dash Tenant", "rent_amount": 1000.0, "rent_due_date": "2026-10-01", "payment_status": "unpaid"}
        
        # Create property first
        prop_res = client.post("/api/v1/properties", json={"address": "456 Tenant St"}, headers=auth_headers)
        prop_id = prop_res.json()["property_id"]
        
        # Create tenant
        create_res = client.post("/api/v1/tenants", json={
            "property_id": prop_id,
            "tenant_name": "Dash Tenant",
            "rent_amount": 1000.0,
            "rent_due_date": "2026-10-01"
        }, headers=auth_headers)
        assert create_res.status_code == 201
        tenant_id = create_res.json()["tenant_id"]
        
        # Update tenant
        update_res = client.patch(f"/api/v1/tenants/{tenant_id}", json={
            "payment_status": "unpaid"
        }, headers=auth_headers)
        assert update_res.status_code == 200
        assert update_res.json()["payment_status"] == "unpaid"

def test_maintenance_ticket_update(auth_headers):
    with patch("database.maintenance_repository.maintenance_repository.create_ticket", new_callable=AsyncMock) as mock_create, \
         patch("database.maintenance_repository.maintenance_repository.update_ticket", new_callable=AsyncMock) as mock_update, \
         patch("database.maintenance_repository.maintenance_repository.get_ticket_by_id", new_callable=AsyncMock) as mock_get, \
         patch("database.maintenance_repository.maintenance_repository.get_ticket_status_log", new_callable=AsyncMock) as mock_status_log, \
         patch("database.audit_repository.audit_repository.create_audit_log", new_callable=AsyncMock) as mock_audit:
        
        mock_create.return_value = {"ticket_id": "TICK-NEW1", "category": "plumbing", "status": "OPEN"}
        mock_update.return_value = True
        mock_get.return_value = {"ticket_id": "TICK-NEW1", "category": "plumbing", "status": "ASSIGNED"}
        mock_status_log.return_value = []
        mock_audit.return_value = None

        # Create ticket via existing endpoint
        create_res = client.post("/api/v1/maintenance/tickets", json={
            "tenant_id": "T-100",
            "category": "plumbing",
            "description": "Leaky dashboard"
        }, headers=auth_headers)
        assert create_res.status_code in (200, 201)
        
        ticket_id = create_res.json()["ticket_id"]
        
        # Patch ticket
        update_res = client.patch(f"/api/v1/maintenance/tickets/{ticket_id}", json={
            "status": "ASSIGNED",
            "assigned_vendor_id": "V-999"
        }, headers=auth_headers)
        assert update_res.status_code == 200
        assert update_res.json()["status"] == "ASSIGNED"
