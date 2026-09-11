"""
V5D End-to-End Workflow Tests
Full frontend-to-backend flow simulation
"""
import pytest
import requests
import json
import uuid

BASE = "http://localhost:8000"


class TestFullDashboardWorkflow:
    """Complete user journey: login → dashboard → project → AI config"""

    @classmethod
    def setup_class(cls):
        cls.session = requests.Session()
        cls.ws_id = None
        cls.proj_id = None
        cls.prov_id = None

    def test_e2e_login(self):
        r = self.session.post(f"{BASE}/api/v1/auth/login", json={
            "provider": "google", "oauth_token": f"e2e-{uuid.uuid4().hex[:8]}"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["authenticated"] is True
        assert data["is_new_user"] in [True, False]

    def test_e2e_discover_workspace(self):
        r = self.session.get(f"{BASE}/api/v1/workspaces")
        assert r.status_code == 200
        data = r.json()
        if data["count"] == 0:
            r2 = self.session.post(f"{BASE}/api/v1/workspaces", json={
                "name": "E2E Workspace", "description": "End-to-end test"
            })
            assert r2.status_code == 200
            self.__class__.ws_id = r2.json()["workspace_id"]
        else:
            self.__class__.ws_id = data["default_workspace_id"]
        assert self.ws_id is not None

    def test_e2e_dashboard_stats(self):
        r = self.session.get(f"{BASE}/api/v1/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["sync_health"] in ["healthy", "attention"]

    def test_e2e_create_project(self):
        r = self.session.post(
            f"{BASE}/api/v1/workspaces/{self.ws_id}/projects",
            json={"workspace_id": self.ws_id,
                  "name": f"E2E Project {uuid.uuid4().hex[:6]}",
                  "project_type": "residential"}
        )
        assert r.status_code == 200
        self.__class__.proj_id = r.json()["project_id"]
        assert self.proj_id is not None

    def test_e2e_list_projects(self):
        r = self.session.get(
            f"{BASE}/api/v1/workspaces/{self.ws_id}/projects")
        assert r.status_code == 200
        assert r.json()["total_count"] >= 1

    def test_e2e_activate_project(self):
        r = self.session.post(
            f"{BASE}/api/v1/projects/{self.proj_id}/status",
            json={"target_state": "ACTIVE"}
        )
        assert r.status_code == 200
        assert r.json()["new_state"] == "ACTIVE"

    def test_e2e_ai_config_flow(self):
        # List providers
        r = self.session.get(
            f"{BASE}/api/v1/workspaces/{self.ws_id}/providers")
        assert r.status_code == 200

        # Create provider if none exist
        if r.json()["count"] == 0:
            r2 = self.session.post(
                f"{BASE}/api/v1/workspaces/{self.ws_id}/providers",
                json={"workspace_id": self.ws_id,
                      "provider_type": "openai",
                      "display_name": "E2E OpenAI",
                      "base_url": "https://api.openai.com/v1",
                      "default_model_id": "gpt-4o"}
            )
            assert r2.status_code == 200
            self.__class__.prov_id = r2.json()["provider_id"]
        else:
            self.__class__.prov_id = r.json()["providers"][0]["provider_id"]

        # Set default model
        r3 = self.session.put(
            f"{BASE}/api/v1/providers/{self.prov_id}/default-model",
            json={"provider_id": self.prov_id, "model_id": "gpt-4o"}
        )
        assert r3.status_code == 200

    def test_e2e_credential_lifecycle(self):
        # Save API key
        r = self.session.post(
            f"{BASE}/api/v1/providers/{self.prov_id}/credentials",
            json={"provider_id": self.prov_id,
                  "api_key": "sk-e2e-test-key-1234567890abcdef",
                  "key_label": "e2e-default"}
        )
        assert r.status_code == 200

        # Verify masked
        r2 = self.session.get(
            f"{BASE}/api/v1/providers/{self.prov_id}/credentials")
        assert r2.status_code == 200
        data = r2.json()
        assert "masked_key" in data
        assert "sk-e2e" not in str(data), "Raw key leaked in response!"

        # Delete
        r3 = self.session.delete(
            f"{BASE}/api/v1/providers/{self.prov_id}/credentials")
        assert r3.status_code == 200
        assert r3.json()["deleted"] is True

    def test_e2e_pascal_health(self):
        r = self.session.get(f"{BASE}/api/v1/dashboard/pascal-health")
        assert r.status_code == 200
        data = r.json()
        assert data["credentials_exposed_to_browser"] is False

    def test_e2e_activity_feed(self):
        r = self.session.get(f"{BASE}/api/v1/dashboard/activity?limit=10")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] >= 1, "Activity should show at least project creation"

    def test_e2e_final_stats(self):
        r = self.session.get(f"{BASE}/api/v1/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["total_projects"] >= 1
        assert data["active_projects"] >= 1
        assert data["ai_providers_configured"] >= 1
        print(f"\n    Final state: projects={data['total_projects']}, "
              f"active={data['active_projects']}, "
              f"configured={data['ai_providers_configured']}, "
              f"sync={data['sync_health']}")


class TestAuthEdgeCases:
    """Edge case testing for authentication"""

    def test_double_login_same_user(self):
        s1 = requests.Session()
        s2 = requests.Session()
        token = f"edge-{uuid.uuid4().hex[:8]}"
        r1 = s1.post(f"{BASE}/api/v1/auth/login",
                      json={"provider": "google", "oauth_token": token})
        r2 = s2.post(f"{BASE}/api/v1/auth/login",
                      json={"provider": "google", "oauth_token": token})
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Same user should get same tenant
        assert r1.json()["tenant_id"] == r2.json()["tenant_id"]

    def test_different_providers_different_users(self):
        s1 = requests.Session()
        s2 = requests.Session()
        r1 = s1.post(f"{BASE}/api/v1/auth/login",
                      json={"provider": "google",
                            "oauth_token": f"g-{uuid.uuid4().hex[:8]}"})
        r2 = s2.post(f"{BASE}/api/v1/auth/login",
                      json={"provider": "github",
                            "oauth_token": f"gh-{uuid.uuid4().hex[:8]}"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Different providers → different users → different tenants
        assert r1.json()["tenant_id"] != r2.json()["tenant_id"]


class TestErrorStates:
    """Error state handling"""

    def test_404_nonexistent_endpoint(self):
        r = requests.get(f"{BASE}/api/v1/nonexistent-endpoint")
        assert r.status_code == 404

    def test_401_no_auth(self):
        r = requests.get(f"{BASE}/api/v1/dashboard/stats")
        assert r.status_code == 401

    def test_422_invalid_input(self):
        s = requests.Session()
        s.post(f"{BASE}/api/v1/auth/login",
               json={"provider": "google",
                     "oauth_token": f"err-{uuid.uuid4().hex[:8]}"})
        r = s.post(f"{BASE}/api/v1/workspaces/00000000-0000-0000-0000-000000000001/projects",
                   json={"name": "Bad Project"})  # Missing workspace_id
        assert r.status_code == 422

    def test_invalid_uuid_workspace(self):
        s = requests.Session()
        s.post(f"{BASE}/api/v1/auth/login",
               json={"provider": "google",
                     "oauth_token": f"uuid-{uuid.uuid4().hex[:8]}"})
        r = s.get(f"{BASE}/api/v1/workspaces/not-a-uuid/projects")
        assert r.status_code == 422
