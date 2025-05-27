import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api.chat_routes import chat_handler

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"

def test_chat_smoke(monkeypatch):
    async def dummy_get_response(message, conversation_id):
        return {"response": "pong", "conversation_id": conversation_id}
    monkeypatch.setattr(chat_handler, "get_response", dummy_get_response)
    r = client.post("/api/chat", json={"message": "ping"})
    assert r.status_code == 200
    body = r.json()
    assert body["response"] == "pong"
    assert "conversation_id" in body