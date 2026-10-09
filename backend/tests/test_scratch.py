from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200

def test_external_network_blocked():
    import socket
    import pytest
    with pytest.raises(Exception, match="Network access is disabled"):
        s = socket.socket()
        s.connect(("8.8.8.8", 80))
