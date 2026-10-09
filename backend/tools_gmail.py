import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from integrations import get_integration_token
from tool_registry import registry
import os

def get_gmail_service():
    token_data = get_integration_token("google")
    if not token_data:
        raise Exception("Google Workspace is not connected. Please connect it in the Integrations panel.")
    
    creds = Credentials(
        token=token_data['access_token'],
        refresh_token=token_data['refresh_token'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=token_data['scopes'].split(",") if token_data['scopes'] else []
    )
    
    return build('gmail', 'v1', credentials=creds)

def search_emails(query: str, max_results: int = 5):
    """Search for emails matching a query in the user's Gmail"""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "No emails found matching the query."
            
        snippets = []
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
            headers = msg_data.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown Date')
            snippet = msg_data.get('snippet', '')
            snippets.append(f"ID: {msg['id']} | From: {sender} | Date: {date} | Subject: {subject}\nSnippet: {snippet}")
            
        return "\n\n".join(snippets)
    except Exception as e:
        return f"Error searching emails: {str(e)}"

def read_email(message_id: str):
    """Read the full content of a specific email by its ID"""
    try:
        service = get_gmail_service()
        msg_data = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        
        headers = msg_data.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown Date')
        
        # Extract body
        def get_body(payload):
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                for part in payload['parts']:
                    if 'parts' in part:
                        return get_body(part)
            elif 'body' in payload and 'data' in payload['body']:
                return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            return "Could not extract plain text body."
            
        body = get_body(msg_data.get('payload', {}))
        
        return f"From: {sender}\nDate: {date}\nSubject: {subject}\n\nBody:\n{body}"
    except Exception as e:
        return f"Error reading email: {str(e)}"


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
    requires_confirmation=False
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
    requires_confirmation=False
)
