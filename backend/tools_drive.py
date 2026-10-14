import httplib2
from google_auth_httplib2 import AuthorizedHttp
from tool_registry import safe_error, provider_call
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from integrations import get_integration_token, google_credentials
from tool_registry import registry
import os

def get_drive_service():
    token_data = get_integration_token("google")
    if not token_data:
        raise Exception("Google Workspace is not connected. Please connect it in the Integrations panel.")
    
    creds = google_credentials(token_data)

    return build('drive', 'v3', http=AuthorizedHttp(creds, http=httplib2.Http(timeout=10)), cache_discovery=False)

@provider_call
def search_drive_files(query: str, max_results: int = 5, page_token: str = None):
    """Search for files in Google Drive by name or text content"""
    if type(max_results) is not int or not 1 <= max_results <= 50:
        raise ValueError('max_results must be between 1 and 50')
    try:
        service = get_drive_service()
        # Ensure we're searching safely
        results = service.files().list(
            q=query,
            pageSize=max_results,
            pageToken=page_token,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            return {"files": [], "next_page_token": results.get("nextPageToken"), "summary": "No files found matching the query."}
            
        lines = []
        for item in items:
            lines.append(f"ID: {item['id']} | Name: {item['name']} | Type: {item['mimeType']} | Last Modified: {item.get('modifiedTime', 'Unknown')}\nLink: {item.get('webViewLink', '')}")
            
        return {"files": items, "next_page_token": results.get('nextPageToken'), "summary": "\n\n".join(lines)}
    except Exception:
        raise

@provider_call
def read_drive_document(file_id: str, mime_type: str = "text/plain"):
    """Read the contents of a Google Doc or Text file in Google Drive. Note: Only supports Google Docs or plain text."""
    try:
        service = get_drive_service()
        file_metadata = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        file_mime = file_metadata.get('mimeType', '')
        
        if 'application/vnd.google-apps.document' in file_mime:
            # Export Google Doc to plain text
            request = service.files().export_media(fileId=file_id, mimeType='text/plain')
            content = request.execute().decode('utf-8')
            return f"Document '{file_metadata.get('name')}':\n\n{content[:20000]}" # Limit to 20k chars
        elif file_mime.startswith('text/') or file_mime == 'application/json':
            # Get plain text file
            request = service.files().get_media(fileId=file_id)
            content = request.execute().decode('utf-8')
            return f"File '{file_metadata.get('name')}':\n\n{content[:20000]}"
        else:
            return {"error": {"code": "unsupported_file_type", "message": "Use the web view link to open this file.", "mime_type": file_mime}}
            
    except Exception:
        raise

registry.register(
    name="search_google_drive",
    description="Search for files in the user's Google Drive. Use standard Drive query syntax (e.g., \"name contains 'assignment'\").",
    parameters={
        "type": "object",
        "properties": {
            "page_token": {"type": "string", "description": "Next page token from a previous search."},
            "query": {
                "type": "string",
                "description": "The Drive search query string."
            },
            "max_results": {
                "type": "integer",
                "description": "Max results to return (default 5)."
            }
        },
        "required": ["query"]
    },
    func=search_drive_files,
    requires_confirmation=False,
    required_permissions="google:https://www.googleapis.com/auth/drive.readonly"
)

registry.register(
    name="read_google_drive_file",
    description="Read the contents of a supported Google Drive file (Google Docs, plain text). You must use search_google_drive first to get the file_id.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {
                "type": "string",
                "description": "The unique ID of the Drive file."
            }
        },
        "required": ["file_id"]
    },
    func=read_drive_document,
    requires_confirmation=False,
    required_permissions="google:https://www.googleapis.com/auth/drive.readonly"
)
