import hashlib
import os
from urllib.parse import urlencode
import requests
from google_auth_oauthlib.flow import Flow
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from integrations import save_integration_token, get_integration_token, remove_integration
from actions import issue_record, consume_record
from security import COOKIE
from tool_registry import safe_error

router = APIRouter()
SCOPES = ['https://www.googleapis.com/auth/calendar.events',
          'https://www.googleapis.com/auth/calendar.readonly',
          'https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/drive.readonly']

def google_flow():
    client_id, secret = os.getenv('GOOGLE_CLIENT_ID'), os.getenv('GOOGLE_CLIENT_SECRET')
    if not client_id or not secret: raise HTTPException(503, 'Google OAuth is not configured')
    return Flow.from_client_config({'web': {'client_id': client_id, 'client_secret': secret,
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth', 'token_uri': 'https://oauth2.googleapis.com/token'}},
        scopes=SCOPES, redirect_uri=os.getenv('GOOGLE_REDIRECT_URI'))

def binding(request):
    return hashlib.sha256(request.cookies.get(COOKIE, '').encode()).hexdigest()

@router.get('/api/auth/{provider}/login')
def login(provider: str, request: Request):
    if provider not in ('google', 'github'): raise HTTPException(404, 'Unknown integration')
    if provider == 'google':
        flow = google_flow()
    elif not os.getenv('GITHUB_CLIENT_ID') or not os.getenv('GITHUB_CLIENT_SECRET'):
        raise HTTPException(503, 'GitHub OAuth is not configured')
    state = issue_record('oauth:' + provider, {}, binding(request))
    if provider == 'google':
        url, _ = flow.authorization_url(state=state, access_type='offline', include_granted_scopes='true', prompt='consent')
    else:
        # Public repository reads require no repo scope. Private reads are explicit opt-in.
        scope = 'repo' if os.getenv('GITHUB_PRIVATE_REPOS') == 'true' else ''
        url = 'https://github.com/login/oauth/authorize?' + urlencode({'client_id': os.getenv('GITHUB_CLIENT_ID'), 'state': state, 'scope': scope})
    return RedirectResponse(url)

@router.get('/api/auth/{provider}/callback')
def callback(provider: str, request: Request):
    if provider not in ('google', 'github'): raise HTTPException(404, 'Unknown integration')
    state = request.query_params.get('state')
    if not state: raise HTTPException(400, 'Invalid OAuth state')
    consume_record(state, 'oauth:' + provider, binding(request))
    code = request.query_params.get('code')
    if not code: raise HTTPException(400, 'Authorization was not completed')
    try:
        if provider == 'google':
            flow = google_flow()
            flow.fetch_token(code=code, timeout=10)
            creds = flow.credentials
            saved = save_integration_token('google', creds.token, creds.refresh_token, creds.expiry, ','.join(creds.granted_scopes or creds.scopes or []))
        else:
            res = requests.post('https://github.com/login/oauth/access_token', timeout=10,
                headers={'Accept': 'application/json'}, json={'client_id': os.getenv('GITHUB_CLIENT_ID'),
                'client_secret': os.getenv('GITHUB_CLIENT_SECRET'), 'code': code})
            res.raise_for_status()
            data = res.json()
            if not isinstance(data, dict) or not isinstance(data.get('access_token'), str) or not data['access_token']:
                raise ValueError('Missing access token')
            saved = save_integration_token('github', data['access_token'], None, None, data.get('scope', ''))
        if not saved: raise RuntimeError('Persistence failed')
    except Exception as exc:
        safe_error(exc)
        raise HTTPException(502, 'Unable to connect integration. Please try again.') from None
    frontend = os.getenv('FRONTEND_URL', 'http://localhost:5173').rstrip('/')
    return RedirectResponse(f'{frontend}/?integration={provider}&status=success')

@router.get('/api/auth/{provider}/status')
def status(provider: str):
    if provider not in ('google', 'github'): raise HTTPException(404, 'Unknown integration')
    token = get_integration_token(provider)
    return {'connected': bool(token and token.get('access_token'))}

@router.delete('/api/auth/{provider}/disconnect')
def disconnect(provider: str):
    if provider not in ('google', 'github'): raise HTTPException(404, 'Unknown integration')
    if not remove_integration(provider): raise HTTPException(503, 'Unable to disconnect')
    return {'status': 'success'}
