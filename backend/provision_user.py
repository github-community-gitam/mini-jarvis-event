"""Run locally to generate a personal access code and server-side hash mapping."""
import hashlib
import json
import secrets
from uuid import uuid4

if __name__ == '__main__':
    code = secrets.token_urlsafe(32)
    user = str(uuid4())
    print('Personal access code (give only to this user):', code)
    print('User ID:', user)
    print('Add this entry to AUTH_USERS on the server:')
    print(json.dumps({hashlib.sha256(code.encode()).hexdigest(): user}))
