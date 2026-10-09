from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    code: str = Field(..., description="Standardized error code (e.g., 'NOT_FOUND', 'VALIDATION_ERROR', 'RATE_LIMITED')")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = None

class ToolContract(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    side_effects: bool = False
    idempotent: bool = True
    timeout_ms: int = 5000
    retryable: bool = True
    
    def validate_input(self, data: Dict[str, Any]) -> BaseModel:
        return self.input_schema(**data)
        
    def validate_output(self, data: Any) -> BaseModel:
        if isinstance(data, ErrorResponse):
            return data
        # If the tool returns a string (as currently implemented), we wrap it or validate it.
        # But wait, our tools currently return raw strings.
        # Let's adapt output schema to allow strings or structured data.
        if issubclass(self.output_schema, BaseModel):
            if isinstance(data, dict):
                return self.output_schema(**data)
            elif isinstance(data, BaseModel):
                return data
        return data

# --- Calendar Contracts ---

class CreateCalendarEventInput(BaseModel):
    title: str = Field(..., min_length=1)
    start_time: str = Field(..., description="RFC3339 format")
    end_time: str = Field(..., description="RFC3339 format")
    description: Optional[str] = ""
    reminders_minutes: Optional[List[int]] = None

class CreateCalendarEventOutput(BaseModel):
    success: bool
    event_id: str
    message: str
    link: Optional[str] = None

create_calendar_event_contract = ToolContract(
    name="create_calendar_event",
    description="Schedule a new event in Google Calendar",
    input_schema=CreateCalendarEventInput,
    output_schema=CreateCalendarEventOutput,
    side_effects=True,
    idempotent=True, # Should be idempotent based on some key, but typically API doesn't guarantee unless an idempotency key is passed
    retryable=True
)

class ListCalendarEventsInput(BaseModel):
    time_min: Optional[str] = None
    time_max: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=50)

list_calendar_events_contract = ToolContract(
    name="get_calendar_events",
    description="List upcoming events",
    input_schema=ListCalendarEventsInput,
    output_schema=BaseModel, # Current tools just return a string, we can enforce a String schema or just accept dicts
    side_effects=False,
    idempotent=True
)

# --- GitHub Contracts ---

class GetRepositoryInfoInput(BaseModel):
    repo_name: str = Field(..., min_length=3)

get_repository_info_contract = ToolContract(
    name="get_github_repository_info",
    description="Get repository info",
    input_schema=GetRepositoryInfoInput,
    output_schema=BaseModel,
    side_effects=False
)

class CreateGithubIssueInput(BaseModel):
    repo_name: str
    title: str
    body: Optional[str] = ""

create_github_issue_contract = ToolContract(
    name="create_github_issue",
    description="Create an issue on GitHub",
    input_schema=CreateGithubIssueInput,
    output_schema=BaseModel,
    side_effects=True,
    idempotent=False
)

# Registry of all expected contracts
CONTRACTS = {
    "create_calendar_event": create_calendar_event_contract,
    "get_calendar_events": list_calendar_events_contract,
    "get_github_repository_info": get_repository_info_contract,
    "create_github_issue": create_github_issue_contract,
}
