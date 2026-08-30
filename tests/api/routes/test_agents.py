from app.api.routes import agents as agents_routes
from app.services.agents_manager import AgentNotFoundError
from app.services.agents_service import agents_service, SessionMismatchError, AgentNotFoundError, SessionNotFoundError



def test_list_agents(client, monkeypatch):
    def fake_list_agents():
        return [
            {
                "id": "sylvain_durif",
                "name": "Syvlain Durif",
                "description": "A collective hallucination maker",
            },
            {
                "id": "karl_toko-ekambi",
                "name": "Karl Toko-Ekambi",
                "description": "A professional football player",
            },
        ]
    monkeypatch.setattr(
        agents_routes.agents_service,
        "list_agents",
        fake_list_agents,
    )

    response = client.get("/v0/agents")

    assert response.status_code == 200

    assert response.json() == [
        {
            "id": "sylvain_durif",
            "name": "Syvlain Durif",
            "description": "A collective hallucination maker",
        },
        {
            "id": "karl_toko-ekambi",
            "name": "Karl Toko-Ekambi",
            "description": "A professional football player",
        },
    ]
    
def test_list_agents_empty(client, monkeypatch):
    def fake_list_agents():
        return []

    monkeypatch.setattr(
        agents_routes.agents_service,
        "list_agents",
        fake_list_agents,
    )

    response = client.get("/v0/agents")
    assert response.status_code == 200
    assert response.json() == []
    
def test_list_agents_internal_error(client, monkeypatch):
    def fake_list_agents():
        raise RuntimeError("Database error")

    monkeypatch.setattr(
        agents_routes.agents_service,
        "list_agents",
        fake_list_agents,
    )

    response = client.get("/v0/agents")
    assert response.status_code == 500
    assert response.json() == {"detail": "Database error"}

def test_create_session(client, monkeypatch):
    def fake_create_session(agent_id):
        assert agent_id == "sylvain_durif"
        return "session-azerty-123456"
    
    monkeypatch.setattr(
        agents_routes.agents_service, 
        "create_session", 
        fake_create_session,
    )
    
    response = client.post("/v0/agents/sylvain_durif/sessions")
    
    assert response.status_code == 200
    assert response.json() == {
        "session_id":"session-azerty-123456",
        "agent_id":"sylvain_durif"
    }
    
def test_create_session_agent_not_found(client, monkeypatch):
    def fake_create_session(agent_id):
        raise AgentNotFoundError()

    monkeypatch.setattr(
        agents_routes.agents_service,
        "create_session",
        fake_create_session,
    )
    response = client.post(
        "/v0/agents/mabio-weed/sessions"
    )
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Agent not found"
    }

def test_send_message_requires_auth_header(client):
    response = client.post(
        "/v0/agents/sylvain_durif/sessions/session-azerty-123456/messages",
        json={
            "message": "Bonjour",
        },
    )

    assert response.status_code == 422 
    
def test_send_message_session_mismatch(client, monkeypatch, override_verify_token):
    async def fake_handle_message(agent_id, session_id, message, meta=None):
        raise SessionMismatchError()

    monkeypatch.setattr(
        agents_routes.agents_service,
        "handle_message",
        fake_handle_message,
    )

    response = client.post(
        "/v0/agents/sylvain_durif/sessions/wrong-session/messages",
        headers={"Authorization": "Bearer valid-token"},
        json={"message": "Bonjour"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Session not found for this agent"
    }
    
def test_create_session_internal_error(client, monkeypatch):
    def fake_create_session(agent_id):
        raise RuntimeError("Internal error")

    monkeypatch.setattr(
        agents_routes.agents_service,
        "create_session",
        fake_create_session,
    )

    response = client.post("/v0/agents/sylvain_durif/sessions")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error"}
    
def test_send_message_requires_auth(client):
    response = client.post(
        "/v0/agents/sylvain_durif/sessions/session-azerty-123456/messages",
        headers={"Authorization": "wrong token"},
        json={
            "message": "Bonjour",
        },
    )

    assert response.status_code == 401

def test_send_message_requires_auth_header(client):
    response = client.post(
        "/v0/agents/sylvain_durif/sessions/session-azerty-123456/messages",
        json={"message": "Bonjour"},
    )

    assert response.status_code == 422


def test_send_message_rejects_invalid_token(client):
    response = client.post(
        "/v0/agents/sylvain_durif/sessions/session-azerty-123456/messages",
        headers={
            "Authorization": "Bearer wrong-token",
        },
        json={"message": "Bonjour"},
    )

    assert response.status_code == 401


def test_send_message_rejects_invalid_auth_scheme(client):
    response = client.post(
        "/v0/agents/sylvain_durif/sessions/session-azerty-123456/messages",
        headers={
            "Authorization": "Basic wrong-token",
        },
        json={"message": "Bonjour"},
    )

    assert response.status_code == 401

        
def test_send_message_valid_token(client, monkeypatch, override_verify_token):
    async def fake_handle_message(agent_id, session_id, message, meta=None):
        return {
            "reply_text": "Bonjour!",
            "reply_ooc": False,
        }

    monkeypatch.setattr(
        agents_routes.agents_service,
        "handle_message",
        fake_handle_message,
    )

    response = client.post(
        "/v0/agents/sylvain_durif/sessions/session-azerty-123456/messages",
        headers={"Authorization": "Bearer valid-token"},
        json={"message": "Bonjour"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "session-azerty-123456",
        "agent_id": "sylvain_durif",
        "reply": {"text": "Bonjour!", "ooc": False},
    }


def test_send_message_empty_message(client, override_verify_token):
    response = client.post(
        "/v0/agents/sylvain_durif/sessions/session-azerty-123456/messages",
        headers={"Authorization": "Bearer valid-token"},
        json={"message": ""},
    )
    assert response.status_code == 422  
    
def test_send_message_too_long_message(client, override_verify_token):
    response = client.post(
        "/v0/agents/sylvain_durif/sessions/session-azerty-123456/messages",
        headers={"Authorization": "Bearer valid-token"},
        json={"message": "x" * 1001},
    )
    assert response.status_code == 422 

def test_send_message_session_not_found(client, monkeypatch, override_verify_token):
    async def fake_handle_message(agent_id, session_id, message, meta=None):
        raise SessionNotFoundError()

    monkeypatch.setattr(
        agents_routes.agents_service,
        "handle_message",
        fake_handle_message,
    )

    response = client.post(
        "/v0/agents/sylvain_durif/sessions/nonexistent-session/messages",
        headers={"Authorization": "Bearer valid-token"},
        json={"message": "Bonjour"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Session not found"
    }

def test_send_message_agent_not_found(client, monkeypatch, override_verify_token):
    async def fake_handle_message(agent_id, session_id, message, meta=None):
        raise AgentNotFoundError()

    monkeypatch.setattr(
        agents_routes.agents_service,
        "handle_message",
        fake_handle_message,
    )

    response = client.post(
        "/v0/agents/nonexistent-agent/sessions/session-azerty-123456/messages",
        headers={"Authorization": "Bearer valid-token"},
        json={"message": "Bonjour"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Agent not found"
    }
    
    
def test_send_message_with_meta(client, monkeypatch, override_verify_token):
    async def fake_handle_message(agent_id, session_id, message, meta=None):
        return {
            "reply_text": "Bonjour!",
            "reply_ooc": True,
        }

    monkeypatch.setattr(
        agents_routes.agents_service,
        "handle_message",
        fake_handle_message,
    )

    response = client.post(
        "/v0/agents/sylvain_durif/sessions/session-azerty-123456/messages",
        headers={"Authorization": "Bearer valid-token"},
        json={"message": "Bonjour", "meta": {"key":"value"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "session-azerty-123456",
        "agent_id": "sylvain_durif",
        "reply": {"text": "Bonjour!", "ooc": True},
    }