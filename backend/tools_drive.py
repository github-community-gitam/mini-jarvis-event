from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from integrations import get_integration_token
from tool_registry import registry
import os

def get_drive_service():
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
    
    return build('drive', 'v3', credentials=creds)

def search_drive_files(query: str, max_results: int = 5):
    """Search for files in Google Drive by name or text content"""
    try:
        service = get_drive_service()
        # Ensure we're searching safely
        results = service.files().list(
            q=query,
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            return "No files found matching the query."
            
        lines = []
        for item in items:
            lines.append(f"ID: {item['id']} | Name: {item['name']} | Type: {item['mimeType']} | Last Modified: {item.get('modifiedTime', 'Unknown')}\nLink: {item.get('webViewLink', '')}")
            
        return "\n\n".join(lines)
    except Exception as e:
        return f"Error searching Drive: {str(e)}"

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
            return f"Unsupported file type for direct reading: {file_mime}. Please use the web view link to open it."
            
    except Exception as e:
        return f"Error reading Drive file: {str(e)}"

registry.register(
    name="search_google_drive",
    description="Search for files in the user's Google Drive. Use standard Drive query syntax (e.g., \"name contains 'assignment'\").",
    parameters={
        "type": "object",
        "properties": {
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
    requires_confirmation=False
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
    requires_confirmation=False
)
