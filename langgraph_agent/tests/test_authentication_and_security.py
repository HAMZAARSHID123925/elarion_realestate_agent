import sys
import os
# Ensure langgraph_agent and root are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.server import app

client = TestClient(app)

@pytest.fixture
def mock_db():
    with patch("database.user_repository.user_repository.get_user_by_email", new_callable=AsyncMock) as m_email, \
         patch("database.user_repository.user_repository.get_user_by_id", new_callable=AsyncMock) as m_id, \
         patch("app.api.routers.auth.auth_service.verify_password") as m_verify, \
         patch("database.audit_repository.audit_repository.create_audit_log", new_callable=AsyncMock) as m_audit, \
         patch("database.dashboard_repository.dashboard_repository.get_overview_metrics", new_callable=AsyncMock) as m_dashboard, \
         patch("app.api.auth.is_auth_enabled", return_value=True) as m_auth_enabled:
        
        m_verify.side_effect = lambda pwd, hash: pwd == "password"
        m_dashboard.return_value = {"total_tenants": 100, "total_properties": 10}
        
        # Valid user hashed with bcrypt("password")
        mock_user = {
            "user_id": "USR-1",
            "email": "test@elarion.com",
            "password_hash": "$2b$12$Kix3hO8S.F41S.Kz7eK7VOPs4.9.4A.3G/pD0sY2O5O/9t2m9A1J6",
            "role": "admin",
            "active": True
        }
        
        # Disabled user
        disabled_user = {
            "user_id": "USR-2",
            "email": "disabled@elarion.com",
            "password_hash": "$2b$12$Kix3hO8S.F41S.Kz7eK7VOPs4.9.4A.3G/pD0sY2O5O/9t2m9A1J6",
            "role": "read_only",
            "active": False
        }
        
        def side_effect(email):
            if email == "test@elarion.com": return mock_user
            if email == "disabled@elarion.com": return disabled_user
            return None
            
        m_email.side_effect = side_effect
        m_id.return_value = mock_user
        
        yield m_email, m_id, m_verify, m_audit

def test_login_success(mock_db):
    response = client.post("/api/v1/auth/login", data={"username": "test@elarion.com", "password": "password"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
def test_login_invalid_password(mock_db):
    response = client.post("/api/v1/auth/login", data={"username": "test@elarion.com", "password": "wrong"})
    assert response.status_code == 401

def test_login_unknown_user(mock_db):
    response = client.post("/api/v1/auth/login", data={"username": "unknown@elarion.com", "password": "password"})
    assert response.status_code == 401

def test_login_inactive_user(mock_db):
    response = client.post("/api/v1/auth/login", data={"username": "disabled@elarion.com", "password": "password"})
    assert response.status_code == 403

def test_get_me_with_jwt(mock_db):
    # First login
    login_res = client.post("/api/v1/auth/login", data={"username": "test@elarion.com", "password": "password"})
    token = login_res.json()["access_token"]
    
    # Then GET /me
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "test@elarion.com"
    assert response.json()["role"] == "admin"

def test_unauthenticated_request(mock_db):
    response = client.get("/api/v1/dashboard/metrics")
    assert response.status_code == 401

def test_invalid_token(mock_db):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-token-at-all"})
    assert response.status_code == 401
    
@patch("os.getenv")
def test_static_api_key_compatibility(mock_getenv, mock_db):
    # Mock environment to have static API keys
    def side_effect(key, default=None):
        if key == "ENABLE_API_AUTH": return "true"
        if key == "API_KEYS_SERVICE": return "test-service-key"
        if key == "API_KEYS_ADMIN": return "test-admin-key"
        if key == "API_KEYS_READONLY": return "test-ro-key"
        # Let JWT keys use default
        if key == "JWT_SECRET_KEY": return "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
        if key == "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": return "60"
        return default
    mock_getenv.side_effect = side_effect
    
    # Test service API key via Bearer
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer test-service-key"})
    assert response.status_code == 200
    assert response.json()["role"] == "service"
    
    # Test admin API key via X-API-Key
    response = client.get("/api/v1/auth/me", headers={"X-API-Key": "test-admin-key"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    
def test_jwt_role_enforcement(mock_db):
    # Mock a read_only user JWT
    from app.services.auth_service import auth_service
    ro_token = auth_service.create_access_token(data={"sub": "USR-RO", "role": "read_only"})
    
    # Attempt to access an admin-only endpoint (like /metrics)
    # Notice we patched metrics to require_admin
    response = client.get("/metrics", headers={"Authorization": f"Bearer {ro_token}"})
    assert response.status_code == 403

def test_admin_jwt_access_admin_endpoint(mock_db):
    # Mock admin user JWT
    from app.services.auth_service import auth_service
    admin_token = auth_service.create_access_token(data={"sub": "USR-ADMIN", "role": "admin"})
    
    # Attempt to access /metrics (which we updated to require_admin)
    response = client.get("/metrics", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
