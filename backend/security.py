"""Owner identity comes only from a signed, expiring server session."""
import hashlib
import hmac
import json
import os
from contextvars import ContextVar
from uuid import UUID
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import HTTPException

owner_context = ContextVar('owner', default=None)
COOKIE = 'jarvis_session'

def owner_id():
    owner = owner_context.get()
    if not owner:
        raise HTTPException(401, 'Sign in required')
    return owner

def serializer():
    secret = os.getenv('SESSION_SECRET', '')
    if len(secret) < 32:
        raise HTTPException(503, 'Authentication is not configured')
    return URLSafeTimedSerializer(secret, salt='jarvis-session-v1')

def authenticate(code):
    # Map SHA-256 access-code hashes to stable user UUIDs; never store raw codes.
    users = json.loads(os.getenv('AUTH_USERS', '{}'))
    digest = hashlib.sha256(code.encode()).hexdigest()
    for stored, user in users.items():
        if hmac.compare_digest(stored, digest):
            return str(UUID(user))
    raise HTTPException(401, 'Invalid access code')

def session_owner(cookie):
    try:
        return str(UUID(serializer().loads(cookie or '', max_age=86400)['user_id']))
    except (BadSignature, SignatureExpired, ValueError, KeyError, TypeError):
        raise HTTPException(401, 'Sign in required')
