import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import verify_token

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def override_verify_token():
    async def mock_verify_token():
        return "valide-token"  
    app.dependency_overrides[verify_token] = mock_verify_token
    yield
    app.dependency_overrides.clear()
