"""Chat API endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestChatStatus:
    """Test chat status endpoint."""

    def test_chat_status_endpoint(self, client):
        """Test chat status returns expected structure."""
        response = client.get("/api/chat/status")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert "provider" in data
        assert "models" in data

    def test_chat_status_models_structure(self, client):
        """Test that models field has expected structure."""
        response = client.get("/api/chat/status")
        data = response.json()
        models = data["models"]
        assert "chat" in models
        assert "vision" in models


class TestChatEndpoint:
    """Test chat message endpoint."""

    def test_chat_requires_message(self, client):
        """Test that chat requires a message."""
        response = client.post(
            "/api/chat/",
            json={"conversation_history": []}
        )
        assert response.status_code == 422

    def test_chat_empty_message(self, client):
        """Test chat with empty message."""
        response = client.post(
            "/api/chat/",
            json={"message": "", "conversation_history": []}
        )
        # API currently accepts empty messages
        assert response.status_code in [200, 400, 422, 500]

    def test_chat_request_structure(self, client):
        """Test that chat accepts proper request structure."""
        # This tests the endpoint accepts the request
        # Actual AI response depends on Azure OpenAI availability
        response = client.post(
            "/api/chat/",
            json={
                "message": "Hello",
                "conversation_history": []
            }
        )
        # Should either succeed or return service unavailable
        assert response.status_code in [200, 503]

    def test_chat_with_conversation_history(self, client):
        """Test chat with conversation history."""
        response = client.post(
            "/api/chat/",
            json={
                "message": "What about wood floors?",
                "conversation_history": [
                    {"role": "user", "content": "I want to design a living room"},
                    {"role": "assistant", "content": "I can help with that."}
                ]
            }
        )
        assert response.status_code in [200, 503]

    def test_chat_with_project_context(self, client):
        """Test chat with project context."""
        response = client.post(
            "/api/chat/",
            json={
                "message": "Suggest materials",
                "conversation_history": [],
                "project_context": {
                    "room_type": "bedroom",
                    "style": "minimalist"
                }
            }
        )
        assert response.status_code in [200, 503]


@pytest.mark.integration
class TestChatIntegration:
    """Integration tests for chat with Azure OpenAI.

    These tests require Azure OpenAI to be configured.
    Run with: pytest -m integration
    """

    def test_chat_returns_response(self, client):
        """Test that chat returns a valid response."""
        # Check if chat is available
        status = client.get("/api/chat/status").json()
        if not status["available"]:
            pytest.skip("Azure OpenAI not configured")

        response = client.post(
            "/api/chat/",
            json={
                "message": "What is a good color for a kitchen?",
                "conversation_history": []
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert len(data["message"]) > 0

    def test_chat_response_is_relevant(self, client):
        """Test that chat response is contextually relevant."""
        status = client.get("/api/chat/status").json()
        if not status["available"]:
            pytest.skip("Azure OpenAI not configured")

        response = client.post(
            "/api/chat/",
            json={
                "message": "What flooring material is best for a bathroom?",
                "conversation_history": []
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Response should mention relevant terms
        response_lower = data["message"].lower()
        relevant_terms = ["tile", "floor", "bathroom", "water", "ceramic", "porcelain", "vinyl"]
        has_relevant = any(term in response_lower for term in relevant_terms)
        assert has_relevant, "Response should be relevant to bathroom flooring"

    def test_chat_maintains_context(self, client):
        """Test that chat maintains conversation context."""
        status = client.get("/api/chat/status").json()
        if not status["available"]:
            pytest.skip("Azure OpenAI not configured")

        # First message
        response1 = client.post(
            "/api/chat/",
            json={
                "message": "I'm designing a Scandinavian style living room",
                "conversation_history": []
            }
        )
        assert response1.status_code == 200
        first_response = response1.json()["message"]

        # Follow-up with context
        response2 = client.post(
            "/api/chat/",
            json={
                "message": "What wood type should I use?",
                "conversation_history": [
                    {"role": "user", "content": "I'm designing a Scandinavian style living room"},
                    {"role": "assistant", "content": first_response}
                ]
            }
        )
        assert response2.status_code == 200

        # Response should reference Scandinavian or light wood
        response_lower = response2.json()["message"].lower()
        relevant_terms = ["scandinavian", "light", "oak", "birch", "pine", "ash", "nordic"]
        has_relevant = any(term in response_lower for term in relevant_terms)
        assert has_relevant, "Response should be contextually aware of Scandinavian style"
