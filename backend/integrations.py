import os
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from memory import transaction
from security import owner_id

def get_integration_token(integration_name):
    with transaction() as cur:
        cur.execute('SELECT access_token, refresh_token, expires_at, scopes FROM user_integrations WHERE integration_name = %s AND user_id = %s;', (integration_name, owner_id()))
        return cur.fetchone()

def save_integration_token(integration_name, access_token, refresh_token, expires_at, scopes):
    with transaction() as cur:
        cur.execute('''INSERT INTO user_integrations (user_id, integration_name, access_token, refresh_token, expires_at, scopes)
        VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (user_id, integration_name) DO UPDATE SET
        access_token = EXCLUDED.access_token, refresh_token = COALESCE(NULLIF(EXCLUDED.refresh_token, ''), user_integrations.refresh_token),
        expires_at = EXCLUDED.expires_at, scopes = EXCLUDED.scopes, updated_at = CURRENT_TIMESTAMP;''',
        (owner_id(), integration_name, access_token, refresh_token, expires_at, scopes))
    return True

def remove_integration(integration_name):
    with transaction() as cur:
        cur.execute('DELETE FROM user_integrations WHERE integration_name = %s AND user_id = %s;', (integration_name, owner_id()))
    return True

def google_credentials(token_data):
    if not token_data:
        raise PermissionError('Google is not connected')
    expiry = token_data.get('expires_at')
    if isinstance(expiry, str):
        expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
    if expiry and expiry.tzinfo:
        expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)
    creds = Credentials(token=token_data['access_token'], refresh_token=token_data.get('refresh_token'),
        expiry=expiry, token_uri='https://oauth2.googleapis.com/token', client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'), scopes=(token_data.get('scopes') or '').replace(',', ' ').split())
    if creds.expired:
        try:
            if not creds.refresh_token:
                raise RefreshError('Missing refresh token')
            transport = Request()
            creds.refresh(lambda *args, **kwargs: transport(*args, **{**kwargs, 'timeout': 10}))
            if not save_integration_token('google', creds.token, creds.refresh_token, creds.expiry, ','.join(creds.scopes or [])):
                raise RuntimeError('Token persistence failed')
        except RefreshError as exc:
            # A transport outage must not discard a usable refresh token.
            if not getattr(exc, 'retryable', False):
                remove_integration('google')
            raise PermissionError('Google authorization needs reconnection') from None
    return creds
