import time
import urllib.parse
import pytest
from fastapi.testclient import TestClient
from server import app
import oauth

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_github_env(monkeypatch):
    """Ensure GitHub client ID and secret are set for tests"""
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_github_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_github_client_secret")
    monkeypatch.setattr(oauth, "GITHUB_CLIENT_ID", "test_github_client_id")
    monkeypatch.setattr(oauth, "GITHUB_CLIENT_SECRET", "test_github_client_secret")
    oauth.oauth_state_store.reset()

def test_github_login_contains_state_parameter():
    """Verify authorization URL contains a secure state parameter and sets matching cookie."""
    response = client.get("/api/auth/github/login", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    parsed = urllib.parse.urlparse(location)
    params = urllib.parse.parse_qs(parsed.query)
    
    assert "state" in params
    state = params["state"][0]
    assert len(state) > 20
    assert params["client_id"][0] == "test_github_client_id"
    assert "repo,read:user" in params["scope"][0]
    
    # Verify cookie is set and matches URL state
    assert oauth.GITHUB_OAUTH_STATE_COOKIE in response.cookies
    assert response.cookies[oauth.GITHUB_OAUTH_STATE_COOKIE] == state

def test_distinct_login_attempts_receive_distinct_states():
    """Verify different login attempts receive unpredictable, distinct state values."""
    res1 = client.get("/api/auth/github/login", follow_redirects=False)
    state1 = urllib.parse.parse_qs(urllib.parse.urlparse(res1.headers["location"]).query)["state"][0]
    
    res2 = client.get("/api/auth/github/login", follow_redirects=False)
    state2 = urllib.parse.parse_qs(urllib.parse.urlparse(res2.headers["location"]).query)["state"][0]
    
    assert state1 != state2

def test_valid_callback_proceeds_through_flow(mocker):
    """Verify a valid callback state proceeds through the existing successful OAuth flow."""
    # Initiate login to obtain a valid state and cookie
    login_res = client.get("/api/auth/github/login", follow_redirects=False)
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]
    state_cookie = login_res.cookies[oauth.GITHUB_OAUTH_STATE_COOKIE]
    
    # Mock requests.post for token exchange
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.json.return_value = {
        "access_token": "gho_mock_access_token_123",
        "scope": "repo,read:user"
    }
    
    # Mock save_integration_token
    mock_save = mocker.patch("oauth.save_integration_token", return_value=True)
    
    # Execute callback with matching query param and cookie
    callback_res = client.get(
        f"/api/auth/github/callback?code=valid_code_123&state={state}",
        cookies={oauth.GITHUB_OAUTH_STATE_COOKIE: state_cookie},
        follow_redirects=False
    )
    
    assert callback_res.status_code == 307
    assert "status=success" in callback_res.headers["location"]
    assert mock_post.called
    assert mock_save.called
    assert mock_save.call_args[0][0] == "github"
    assert mock_save.call_args[0][1] == "gho_mock_access_token_123"

def test_missing_state_rejected(mocker):
    """Verify callback without state parameter is rejected."""
    mock_post = mocker.patch("requests.post")
    res = client.get("/api/auth/github/callback?code=mock_code", follow_redirects=False)
    assert res.status_code == 400
    assert "state" in res.json()["detail"].lower()
    mock_post.assert_not_called()

def test_missing_cookie_rejected(mocker):
    """Verify callback with query state but missing cookie (CSRF attack) is rejected."""
    mock_post = mocker.patch("requests.post")
    state = oauth.generate_oauth_state()
    res = client.get(f"/api/auth/github/callback?code=mock_code&state={state}", follow_redirects=False)
    assert res.status_code == 400
    assert "cookie" in res.json()["detail"].lower()
    mock_post.assert_not_called()

def test_mismatched_state_rejected(mocker):
    """Verify callback with query state differing from session cookie is rejected."""
    mock_post = mocker.patch("requests.post")
    login_res = client.get("/api/auth/github/login", follow_redirects=False)
    state_cookie = login_res.cookies[oauth.GITHUB_OAUTH_STATE_COOKIE]
    tampered_state = state_cookie + "_tampered"
    
    res = client.get(
        f"/api/auth/github/callback?code=mock_code&state={tampered_state}",
        cookies={oauth.GITHUB_OAUTH_STATE_COOKIE: state_cookie},
        follow_redirects=False
    )
    assert res.status_code == 400
    assert "state" in res.json()["detail"].lower()
    mock_post.assert_not_called()

def test_tampered_signature_rejected(mocker):
    """Verify callback with forged or tampered HMAC signature is rejected."""
    mock_post = mocker.patch("requests.post")
    login_res = client.get("/api/auth/github/login", follow_redirects=False)
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]
    
    parts = state.split(".")
    tampered_sig = "a" * len(parts[2])
    tampered_state = f"{parts[0]}.{parts[1]}.{tampered_sig}"
    
    res = client.get(
        f"/api/auth/github/callback?code=mock_code&state={tampered_state}",
        cookies={oauth.GITHUB_OAUTH_STATE_COOKIE: tampered_state},
        follow_redirects=False
    )
    assert res.status_code == 400
    assert "state" in res.json()["detail"].lower()
    mock_post.assert_not_called()

def test_expired_state_rejected(mocker):
    """Verify an expired state parameter is rejected."""
    mock_post = mocker.patch("requests.post")
    
    # Generate a state with timestamp in the past (700s ago > 600s TTL)
    old_time = time.time() - 700
    nonce = "old_nonce_123"
    payload = f"{nonce}.{int(old_time)}"
    sig = oauth.hmac.new(oauth._get_state_secret(), payload.encode("utf-8"), oauth.hashlib.sha256).hexdigest()
    expired_state = f"{payload}.{sig}"
    
    res = client.get(
        f"/api/auth/github/callback?code=mock_code&state={expired_state}",
        cookies={oauth.GITHUB_OAUTH_STATE_COOKIE: expired_state},
        follow_redirects=False
    )
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()
    mock_post.assert_not_called()

def test_previously_consumed_state_cannot_be_reused(mocker):
    """Verify a valid state cannot be replayed after being consumed."""
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.json.return_value = {
        "access_token": "gho_mock_access_token_123",
        "scope": "repo,read:user"
    }
    mocker.patch("oauth.save_integration_token", return_value=True)
    
    # Initiate login
    login_res = client.get("/api/auth/github/login", follow_redirects=False)
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]
    state_cookie = login_res.cookies[oauth.GITHUB_OAUTH_STATE_COOKIE]
    
    # First callback succeeds
    res1 = client.get(
        f"/api/auth/github/callback?code=mock_code_1&state={state}",
        cookies={oauth.GITHUB_OAUTH_STATE_COOKIE: state_cookie},
        follow_redirects=False
    )
    assert res1.status_code == 307
    assert mock_post.call_count == 1
    
    # Replayed callback with same state must be rejected
    res2 = client.get(
        f"/api/auth/github/callback?code=mock_code_2&state={state}",
        cookies={oauth.GITHUB_OAUTH_STATE_COOKIE: state_cookie},
        follow_redirects=False
    )
    assert res2.status_code == 400
    assert "consumed" in res2.json()["detail"].lower()
    # mock_post must NOT have been called again
    assert mock_post.call_count == 1

def test_invalid_state_rejected_before_external_request(mocker):
    """Verify invalid state is rejected BEFORE any external HTTP token exchange request."""
    mock_post = mocker.patch("requests.post")
    
    res = client.get(
        "/api/auth/github/callback?code=valid_looking_code&state=invalid_state_123",
        cookies={oauth.GITHUB_OAUTH_STATE_COOKIE: "different_cookie"},
        follow_redirects=False
    )
    assert res.status_code == 400
    mock_post.assert_not_called()

def test_github_status_and_disconnect(mocker):
    """Verify existing status and disconnect routes remain functional."""
    mocker.patch("oauth.get_integration_token", return_value={"access_token": "token"})
    res_status = client.get("/api/auth/github/status")
    assert res_status.status_code == 200
    assert res_status.json() == {"connected": True}
    
    mocker.patch("oauth.remove_integration", return_value=True)
    res_disc = client.delete("/api/auth/github/disconnect")
    assert res_disc.status_code == 200
    assert res_disc.json() == {"status": "success"}

def test_github_callback_error_handling(mocker):
    """Verify GitHub error parameters (e.g. access_denied) are handled without token exchange."""
    mock_post = mocker.patch("requests.post")
    res = client.get(
        "/api/auth/github/callback?error=access_denied&error_description=User+cancelled",
        follow_redirects=False
    )
    assert res.status_code == 400
    assert "access_denied" in res.json()["detail"] or "User cancelled" in res.json()["detail"]
    mock_post.assert_not_called()
