import httplib2
from google_auth_httplib2 import AuthorizedHttp
from tool_registry import safe_error, provider_call
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from integrations import get_integration_token, google_credentials
from tool_registry import registry
import os

def get_gmail_service():
    token_data = get_integration_token("google")
    if not token_data:
        raise Exception("Google Workspace is not connected. Please connect it in the Integrations panel.")
    
    creds = google_credentials(token_data)

    return build('gmail', 'v1', http=AuthorizedHttp(creds, http=httplib2.Http(timeout=10)), cache_discovery=False)

@provider_call
def search_emails(query: str, max_results: int = 5):
    """Search for emails matching a query in the user's Gmail"""
    if type(max_results) is not int or not 1 <= max_results <= 50:
        raise ValueError('max_results must be between 1 and 50')
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "No emails found matching the query."
            
        snippets = []
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
            headers = (msg_data.get('payload') or {}).get('headers') or []
            subject = next((h['value'] for h in headers if isinstance(h, dict) and str(h.get('name', '')).lower() == 'subject' and isinstance(h.get('value'), str) and h['value']), 'No Subject')
            sender = next((h['value'] for h in headers if isinstance(h, dict) and str(h.get('name', '')).lower() == 'from' and isinstance(h.get('value'), str) and h['value']), 'Unknown Sender')
            date = next((h['value'] for h in headers if isinstance(h, dict) and str(h.get('name', '')).lower() == 'date' and isinstance(h.get('value'), str) and h['value']), 'Unknown Date')
            snippet = msg_data.get('snippet', '')
            snippets.append(f"ID: {msg['id']} | From: {sender} | Date: {date} | Subject: {subject}\nSnippet: {snippet}")
            
        return "\n\n".join(snippets)
    except Exception:
        raise

@provider_call
def read_email(message_id: str):
    """Read the full content of a specific email by its ID"""
    try:
        service = get_gmail_service()
        msg_data = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        
        headers = (msg_data.get('payload') or {}).get('headers') or []
        subject = next((h['value'] for h in headers if isinstance(h, dict) and str(h.get('name', '')).lower() == 'subject' and isinstance(h.get('value'), str) and h['value']), 'No Subject')
        sender = next((h['value'] for h in headers if isinstance(h, dict) and str(h.get('name', '')).lower() == 'from' and isinstance(h.get('value'), str) and h['value']), 'Unknown Sender')
        date = next((h['value'] for h in headers if isinstance(h, dict) and str(h.get('name', '')).lower() == 'date' and isinstance(h.get('value'), str) and h['value']), 'Unknown Date')
        
        # Extract body
        def get_body(payload, depth=0):
            if not isinstance(payload, dict) or depth > 20: return ''
            if payload.get('mimeType', 'text/plain') == 'text/plain':
                data = (payload.get('body') or {}).get('data')
                if isinstance(data, str):
                    try:
                        return base64.b64decode(data + '=' * (-len(data) % 4), altchars=b'-_', validate=True).decode('utf-8', errors='replace')
                    except (ValueError, TypeError): pass
            parts = payload.get('parts') or []
            for part in parts:
                text = get_body(part, depth + 1)
                if text: return text
            return ''

        body = get_body(msg_data.get('payload', {})) or 'No readable plain text body.'
        
        return f"From: {sender}\nDate: {date}\nSubject: {subject}\n\nBody:\n{body}"
    except Exception:
        raise


registry.register(
    name="search_emails",
    description="Search for emails in the user's Gmail using standard Gmail search operators (e.g., 'from:professor assignment', 'is:unread'). Returns a summary.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The Gmail search query."
            },
            "max_results": {
                "type": "integer",
                "description": "Max results to return (default 5)."
            }
        },
        "required": ["query"]
    },
    func=search_emails,
    requires_confirmation=False,
    required_permissions="google:https://www.googleapis.com/auth/gmail.readonly"
)

registry.register(
    name="read_email",
    description="Read the full contents of a specific email. You must first use search_emails to get the message_id.",
    parameters={
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": "The unique ID of the email message."
            }
        },
        "required": ["message_id"]
    },
    func=read_email,
    requires_confirmation=False,
    required_permissions="google:https://www.googleapis.com/auth/gmail.readonly"
)
