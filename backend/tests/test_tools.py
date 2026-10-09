import pytest
from tests.mocks.providers import calendar_mock, github_mock
from tools_calendar import list_events, create_event
from tools_github import get_repository_info
import json

def test_get_calendar_events():
    # The mock is pre-seeded with 2 events
    result = list_events()
    assert "Mock Review" in result
    assert "Mock Dentist" in result

def test_create_event():
    # Execute the tool
    result = create_event("Meeting", "2026-10-15T10:00:00Z", "2026-10-15T11:00:00Z", "Discuss AI")
    assert "Meeting" in result
    
    # Check the mock state directly to ensure side-effect occurred
    assert len(calendar_mock.state["events"]) == 3
    new_event = calendar_mock.state["events"][-1]
    assert new_event["summary"] == "Meeting"
    assert new_event["start"]["dateTime"] == "2026-10-15T10:00:00Z"

def test_provider_failure_handling():
    # Simulate a 500 error from Google Calendar
    calendar_mock.set_failure("RATE_LIMIT_EXCEEDED")
    
    # The tool should catch this and return an error string
    result = list_events()
    assert "RATE_LIMIT_EXCEEDED" in result or "Error" in result

def test_github_repo_info():
    # Test github repository read
    result = get_repository_info("mock-user/mock-repo")
    assert "mock-user/mock-repo" in result
    assert "42" in result # stargazers count

def test_github_404_handling():
    result = get_repository_info("non-existent/repo")
    assert "Error" in result
    assert "404" in result
