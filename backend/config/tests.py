from django.test import SimpleTestCase
from rest_framework.test import APIClient
from unittest.mock import patch
from pymongo.errors import ServerSelectionTimeoutError


class HealthEndpointTests(SimpleTestCase):
    def test_backend_root_redirects_to_react_frontend(self):
        response = APIClient().get("/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://127.0.0.1:5173/")

    def test_health_endpoint_is_public_and_database_independent(self):
        response = APIClient().get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "connect-ai-api"},
        )

    @patch("config.views.get_client")
    def test_readiness_returns_ready_when_mongodb_ping_succeeds(self, get_client):
        response = APIClient().get("/api/health/ready/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready", "database": "available"})
        get_client.return_value.admin.command.assert_called_once_with("ping")

    @patch("config.views.get_client")
    def test_readiness_returns_json_unavailable_when_mongodb_ping_fails(self, get_client):
        get_client.return_value.admin.command.side_effect = ServerSelectionTimeoutError(
            "connection refused"
        )

        response = APIClient().get("/api/health/ready/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "database_unavailable")
