import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from integrations import get_integration_token

def get_calendar_service():
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
    
    return build('calendar', 'v3', credentials=creds)

def list_events(time_min: str = None, time_max: str = None, max_results: int = 10):
    """
    List events from the user's primary Google Calendar.
    time_min and time_max should be RFC3339 formatted strings (e.g., '2023-10-10T10:00:00Z').
    """
    try:
        service = get_calendar_service()
        
        if not time_min:
            time_min = datetime.datetime.utcnow().isoformat() + 'Z'
            
        events_result = service.events().list(
            calendarId='primary', timeMin=time_min, timeMax=time_max,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        if not events:
            return "No upcoming events found."
            
        result = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            result.append(f"- {event['summary']} at {start}")
        return "\n".join(result)
    except Exception as e:
        return f"Error accessing calendar: {str(e)}"

def create_event(title: str, start_time: str, end_time: str, description: str = "", reminders_minutes: list = None):
    """
    Create a new event in the user's primary Google Calendar.
    start_time and end_time should be RFC3339 formatted strings with timezone offsets (e.g., '2023-10-10T10:00:00+05:30').
    """
    try:
        service = get_calendar_service()
        
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time,
            },
            'end': {
                'dateTime': end_time,
            },
        }
        
        if reminders_minutes:
            overrides = [{'method': 'popup', 'minutes': m} for m in reminders_minutes]
            event['reminders'] = {
                'useDefault': False,
                'overrides': overrides
            }
            
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        return f"Successfully created event '{title}'. Link: {event_result.get('htmlLink')}"
    except Exception as e:
        return f"Error creating event: {str(e)}"

import os
from tool_registry import registry

registry.register(
    name="get_calendar_events",
    description="Retrieve a list of upcoming events from the user's Google Calendar. Useful for checking schedule.",
    parameters={
        "type": "object",
        "properties": {
            "time_min": {
                "type": "string",
                "description": "Start of the time range in RFC3339 format (e.g. 2026-10-09T00:00:00Z). Defaults to current time."
            },
            "time_max": {
                "type": "string",
                "description": "End of the time range in RFC3339 format. Optional."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of events to return. Default 10."
            }
        }
    },
    func=list_events,
    requires_confirmation=False
)

registry.register(
    name="create_calendar_event",
    description="Schedule a new event in the user's Google Calendar. ALWAYS ask the user for confirmation BEFORE calling this tool, and make sure you have the exact start_time and end_time in RFC3339 format.",
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title of the event"
            },
            "start_time": {
                "type": "string",
                "description": "Start time of the event in RFC3339 format with timezone (e.g., 2026-10-10T09:00:00+05:30). Do not invent this, calculate it based on user request and current time."
            },
            "end_time": {
                "type": "string",
                "description": "End time of the event in RFC3339 format with timezone. If not specified, default to 1 hour after start_time."
            },
            "description": {
                "type": "string",
                "description": "Optional description for the event"
            },
            "reminders_minutes": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of reminder times in minutes before the event (e.g. [30, 10])."
            }
        },
        "required": ["title", "start_time", "end_time"]
    },
    func=create_event,
    requires_confirmation=True,
    required_permissions="google"
)
