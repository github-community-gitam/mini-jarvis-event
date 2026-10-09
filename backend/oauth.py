import os
from google_auth_oauthlib.flow import Flow
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from integrations import save_integration_token, get_integration_token, remove_integration

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
import requests

@router.get("/api/auth/github/login")
async def github_login():
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub OAuth is not configured.")
    
    # Request 'repo' scope for access to repositories (GitHub OAuth doesn't have a read-only private repo scope)
    github_auth_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo,read:user"
    return RedirectResponse(url=github_auth_url)

@router.get("/api/auth/github/callback")
async def github_callback(request: Request):
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
        return RedirectResponse(url=f"{FRONTEND_URL}/?integration=github&status=success")
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
