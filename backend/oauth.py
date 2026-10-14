import hashlib
import hmac
import os
import secrets
import threading
import time
from typing import Dict, Optional
import urllib.parse
from google_auth_oauthlib.flow import Flow
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from integrations import save_integration_token, get_integration_token, remove_integration
import requests

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.readonly'
]


def get_client_config():
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": "mini-jarvis-project",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [GOOGLE_REDIRECT_URI]
        }
    }

@router.get("/api/auth/google/login")
async def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured on the server.")

    flow = Flow.from_client_config(
        get_client_config(),
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    return RedirectResponse(url=authorization_url)

@router.get("/api/auth/google/callback")
async def google_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="No code provided")

    flow = Flow.from_client_config(
        get_client_config(),
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials

        save_integration_token(
            "google",
            credentials.token,
            credentials.refresh_token,
            credentials.expiry,
            ",".join(SCOPES)
        )
        # Redirect back to the frontend
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=f"{FRONTEND_URL}/?integration=google&status=success")
    except Exception as e:
        print(f"OAuth Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/auth/google/status")
async def google_status():
    token_data = get_integration_token("google")
    return {"connected": token_data is not None}

@router.delete("/api/auth/google/disconnect")
async def google_disconnect():
    success = remove_integration("google")
    return {"status": "success" if success else "error"}


# --- GitHub OAuth ---

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_OAUTH_STATE_COOKIE = "github_oauth_state"
STATE_TTL_SECONDS = int(os.getenv("GITHUB_OAUTH_STATE_TTL", "600"))

# Process-level random fallback secret if neither SECRET_KEY nor GITHUB_CLIENT_SECRET is provided
_PROCESS_STATE_SECRET = secrets.token_bytes(32)


def _get_state_secret() -> bytes:
    """Return secret key for HMAC state signing, preferring environment variables."""
    secret = os.getenv("SECRET_KEY") or os.getenv("GITHUB_CLIENT_SECRET")
    if secret:
        return secret.encode("utf-8")
    return _PROCESS_STATE_SECRET


class OAuthStateStore:
    """
    Thread-safe storage tracking consumed state tokens to prevent replay attacks.
    Automatically purges expired tokens to prevent memory growth.
    """
    def __init__(self, ttl: int = STATE_TTL_SECONDS):
        self.ttl = ttl
        self._lock = threading.Lock()
        self._consumed: Dict[str, float] = {}

    def _cleanup(self, now: float):
        cutoff = now - self.ttl
        expired = [k for k, v in self._consumed.items() if v < cutoff]
        for k in expired:
            del self._consumed[k]

    def consume(self, nonce: str) -> bool:
        """
        Atomically records a nonce as consumed.
        Returns True if the nonce was not previously consumed.
        Returns False if the nonce was already consumed.
        """
        now = time.time()
        with self._lock:
            self._cleanup(now)
            if nonce in self._consumed:
                return False
            self._consumed[nonce] = now
            return True

    def reset(self):
        """Reset consumed cache (useful for tests)."""
        with self._lock:
            self._consumed.clear()


oauth_state_store = OAuthStateStore(ttl=STATE_TTL_SECONDS)


def generate_oauth_state() -> str:
    """
    Generate a cryptographically secure, unpredictable, timestamped, HMAC-signed state token.
    Format: <nonce>.<timestamp>.<signature>
    """
    nonce = secrets.token_urlsafe(24)
    timestamp = int(time.time())
    payload = f"{nonce}.{timestamp}"
    signature = hmac.new(_get_state_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def validate_and_consume_state(state: Optional[str], cookie_state: Optional[str], ttl: int = STATE_TTL_SECONDS) -> None:
    """
    Validate the state returned from GitHub against the browser session cookie and server secret.
    Enforces presence, matching, cryptographic integrity, expiration, and single-use consumption.
    Raises HTTPException(400) on any validation failure.
    """
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state parameter.")

    if not cookie_state:
        raise HTTPException(status_code=400, detail="OAuth state cookie is missing.")

    # Constant-time comparison between state in query and state in cookie to prevent timing attacks
    if not secrets.compare_digest(state, cookie_state):
        raise HTTPException(status_code=400, detail="OAuth state parameter does not match session.")

    # Parse format: <nonce>.<timestamp>.<signature>
    parts = state.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Malformed OAuth state parameter.")

    nonce, ts_str, signature = parts
    payload = f"{nonce}.{ts_str}"
    expected_signature = hmac.new(_get_state_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    if not secrets.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=400, detail="Invalid OAuth state signature.")

    try:
        created_at = int(ts_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Malformed timestamp in OAuth state.")

    now = time.time()
    # Reject expired state or state with future timestamp (beyond 60s clock skew)
    if (now - created_at) > ttl or created_at > (now + 60):
        raise HTTPException(status_code=400, detail="OAuth state has expired.")

    # Enforce single-use consumption
    if not oauth_state_store.consume(nonce):
        raise HTTPException(status_code=400, detail="OAuth state has already been consumed.")


@router.get("/api/auth/github/login")
async def github_login(request: Request):
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub OAuth is not configured.")

    state = generate_oauth_state()

    # Request 'repo' scope for access to repositories (GitHub OAuth doesn't have a read-only private repo scope)
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "scope": "repo,read:user",
        "state": state
    }
    github_auth_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"

    response = RedirectResponse(url=github_auth_url)
    response.set_cookie(
        key=GITHUB_OAUTH_STATE_COOKIE,
        value=state,
        max_age=STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/"
    )
    return response

@router.get("/api/auth/github/callback")
async def github_callback(request: Request):
    # Check for error responses returned by GitHub
    oauth_error = request.query_params.get("error")
    if oauth_error:
        error_desc = request.query_params.get("error_description", oauth_error)
        raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {error_desc}")

    # Validate state BEFORE any external token exchange or code processing
    state = request.query_params.get("state")
    cookie_state = request.cookies.get(GITHUB_OAUTH_STATE_COOKIE)
    validate_and_consume_state(state, cookie_state, ttl=STATE_TTL_SECONDS)

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="No code provided")

    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    payload = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code
    }

    try:
        res = requests.post(token_url, json=payload, headers=headers)
        data = res.json()

        if "access_token" not in data:
            raise Exception(f"Failed to get access token: {data}")

        access_token = data["access_token"]
        # Save token
        save_integration_token("github", access_token, "", None, data.get("scope", ""))

        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
        response = RedirectResponse(url=f"{FRONTEND_URL}/?integration=github&status=success")
        response.delete_cookie(key=GITHUB_OAUTH_STATE_COOKIE, path="/")
        return response
    except Exception as e:
        print(f"GitHub OAuth Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/auth/github/status")
async def github_status():
    token_data = get_integration_token("github")
    return {"connected": token_data is not None}

@router.delete("/api/auth/github/disconnect")
async def github_disconnect():
    success = remove_integration("github")
    return {"status": "success" if success else "error"}
