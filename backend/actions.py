"""Durable one-time approvals and OAuth state; atomic consumption across workers."""
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from memory import transaction
from security import owner_id

def issue_record(kind, payload, binding='', ttl=600):
    token = secrets.token_urlsafe(32)
    with transaction() as cur:
        cur.execute('DELETE FROM pending_actions WHERE expires_at < CURRENT_TIMESTAMP;')
        cur.execute('INSERT INTO pending_actions (id, user_id, kind, payload, binding, expires_at) VALUES (%s,%s,%s,%s,%s,%s);',
            (hashlib.sha256(token.encode()).hexdigest(), owner_id(), kind, json.dumps(payload), binding, datetime.now(timezone.utc) + timedelta(seconds=ttl)))
    return token

def consume_record(token, kind, binding=''):
    with transaction() as cur:
        cur.execute('DELETE FROM pending_actions WHERE id = %s AND user_id = %s AND kind = %s AND binding = %s AND expires_at > CURRENT_TIMESTAMP RETURNING payload;',
            (hashlib.sha256(token.encode()).hexdigest(), owner_id(), kind, binding))
        row = cur.fetchone()
        if not row:
            raise HTTPException(409, 'Action expired, invalid, or already used')
        return json.loads(row['payload']) if isinstance(row['payload'], str) else row['payload']
