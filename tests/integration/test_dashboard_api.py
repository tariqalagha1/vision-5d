"""
V5D Dashboard API Integration Tests
Tests all 7 dashboard endpoints + auth + workspace discovery
"""
import pytest
import requests
import json
import time
import uuid

BASE = "http://localhost:8000"
SESSION = requests.Session()


class TestAuthFlow:
    """Test authentication and session persistence"""

    def test_login_creates_session(self):
        r = SESSION.post(f"{BASE}/api/v1/auth/login", json={
            "provider": "google", "oauth_token": f"integration-test-{uuid.uuid4().hex[:8]}"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["authenticated"] is True
        assert "session_token" in data
        assert "user_id" in data
        assert "tenant_id" in data

    def test_unauthorized_rejected(self):
        r = requests.get(f"{BASE}/api/v1/dashboard/stats")
        assert r.status_code == 401

    def test_unauthorized_with_bad_cookie(self):
        r = requests.get(f"{BASE}/api/v1/dashboard/stats",
                         cookies={"v5d_session": "invalid-token"})
        assert r.status_code == 401


class TestWorkspaceDiscovery:
    """Test workspace auto-discovery (critical for restart recovery)"""

    def test_list_workspaces(self):
        r = SESSION.get(f"{BASE}/api/v1/workspaces")
        assert r.status_code == 200
        data = r.json()
        assert "workspaces" in data
        assert "count" in data
        assert "default_workspace_id" in data

    def test_create_workspace_if_none(self):
        r = SESSION.get(f"{BASE}/api/v1/workspaces")
        data = r.json()
        if data["count"] == 0:
            r2 = SESSION.post(f"{BASE}/api/v1/workspaces", json={
                "name": "Integration Test WS",
                "description": "Auto-created for testing"
            })
            assert r2.status_code == 200
            assert "workspace_id" in r2.json()


class TestDashboardStats:
    """Test dashboard statistics endpoint"""

    def test_stats_returns_all_fields(self):
        r = SESSION.get(f"{BASE}/api/v1/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        required_fields = [
            "total_projects", "active_projects", "total_scenes",
            "total_revisions", "conflict_count", "failed_sync_count",
            "ai_providers_configured", "ai_providers_healthy", "sync_health"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_stats_values_are_non_negative(self):
        r = SESSION.get(f"{BASE}/api/v1/dashboard/stats")
        data = r.json()
        for key in ["total_projects", "active_projects", "total_scenes",
                     "total_revisions", "conflict_count", "failed_sync_count"]:
            assert data[key] >= 0, f"{key} should be >= 0, got {data[key]}"


class TestDashboardActivity:
    """Test activity feed endpoint"""

    def test_activity_returns_list(self):
        r = SESSION.get(f"{BASE}/api/v1/dashboard/activity?limit=5")
        assert r.status_code == 200
        data = r.json()
        assert "activity" in data
        assert "count" in data
        assert isinstance(data["activity"], list)

    def test_activity_respects_limit(self):
        r = SESSION.get(f"{BASE}/api/v1/dashboard/activity?limit=2")
        data = r.json()
        assert data["count"] <= 2


class TestPascalHealth:
    """Test Pascal health endpoint (credential-safe)"""

    def test_pascal_health_no_credentials(self):
        r = SESSION.get(f"{BASE}/api/v1/dashboard/pascal-health")
        assert r.status_code == 200
        data = r.json()
        assert "credentials_exposed_to_browser" in data
        assert data["credentials_exposed_to_browser"] is False
        assert "status" in data

    def test_pascal_has_version(self):
        r = SESSION.get(f"{BASE}/api/v1/dashboard/pascal-health")
        data = r.json()
        assert "pascal_version" in data


class TestProjectCRUD:
    """Test project create and list"""

    def test_create_and_list_project(self):
        # Discover workspace
        r = SESSION.get(f"{BASE}/api/v1/workspaces")
        ws = r.json()
        if ws["count"] == 0:
            pytest.skip("No workspace available")

        ws_id = ws["default_workspace_id"]

        # Create project
        r2 = SESSION.post(f"{BASE}/api/v1/workspaces/{ws_id}/projects", json={
            "workspace_id": ws_id,
            "name": f"Integration Project {uuid.uuid4().hex[:6]}",
            "project_type": "residential"
        })
        assert r2.status_code == 200
        proj = r2.json()
        assert proj["state"] == "DRAFT"
        assert "project_id" in proj

        # List projects
        r3 = SESSION.get(f"{BASE}/api/v1/workspaces/{ws_id}/projects")
        assert r3.status_code == 200
        assert r3.json()["total_count"] >= 1


class TestProviderConfig:
    """Test AI provider configuration"""

    def test_list_providers_in_workspace(self):
        r = SESSION.get(f"{BASE}/api/v1/workspaces")
        ws = r.json()
        if ws["count"] == 0:
            pytest.skip("No workspace available")
        ws_id = ws["default_workspace_id"]

        r2 = SESSION.get(f"{BASE}/api/v1/workspaces/{ws_id}/providers")
        assert r2.status_code == 200
        assert "providers" in r2.json()


class TestPerformance:
    """Performance benchmarks for dashboard endpoints"""

    def test_stats_response_time(self):
        times = []
        for _ in range(10):
            t0 = time.time()
            r = SESSION.get(f"{BASE}/api/v1/dashboard/stats")
            t1 = time.time()
            assert r.status_code == 200
            times.append((t1 - t0) * 1000)
        avg = sum(times) / len(times)
        max_t = max(times)
        print(f"\n    Stats: avg={avg:.1f}ms, max={max_t:.1f}ms")
        assert max_t < 500, f"Stats too slow: {max_t:.1f}ms"

    def test_workspace_discovery_time(self):
        times = []
        for _ in range(10):
            t0 = time.time()
            r = SESSION.get(f"{BASE}/api/v1/workspaces")
            t1 = time.time()
            assert r.status_code == 200
            times.append((t1 - t0) * 1000)
        avg = sum(times) / len(times)
        print(f"\n    Workspace discovery: avg={avg:.1f}ms")

    def test_pascal_health_time(self):
        t0 = time.time()
        r = SESSION.get(f"{BASE}/api/v1/dashboard/pascal-health")
        t1 = time.time()
        assert r.status_code == 200
        elapsed = (t1 - t0) * 1000
        print(f"\n    Pascal health: {elapsed:.1f}ms")
        assert elapsed < 200, f"Pascal health too slow: {elapsed:.1f}ms"
