import json
import os
from database import get_db_connection

def get_integration_token(integration_name: str) -> dict:
    """Retrieve tokens for a given integration"""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT access_token, refresh_token, expires_at, scopes FROM user_integrations WHERE integration_name = %s",
                (integration_name,)
            )
            return cur.fetchone()
    finally:
        conn.close()

def save_integration_token(integration_name: str, access_token: str, refresh_token: str, expires_at, scopes: str):
    """Save or update tokens for a given integration"""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_integrations (integration_name, access_token, refresh_token, expires_at, scopes)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (integration_name) DO UPDATE 
                SET access_token = EXCLUDED.access_token,
                    refresh_token = COALESCE(EXCLUDED.refresh_token, user_integrations.refresh_token),
                    expires_at = EXCLUDED.expires_at,
                    scopes = EXCLUDED.scopes,
                    updated_at = NOW();
            """, (integration_name, access_token, refresh_token, expires_at, scopes))
            return True
    finally:
        conn.close()

def remove_integration(integration_name: str):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_integrations WHERE integration_name = %s", (integration_name,))
            return True
    finally:
        conn.close()
