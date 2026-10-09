import pytest
import socket
import sys
from unittest.mock import MagicMock

# Mock database module to prevent loading psycopg2 during tests
sys.modules['database'] = MagicMock()

from tests.mocks.providers import calendar_mock, github_mock, gmail_mock, drive_mock

# Disable network access globally for tests
# We patch socket.socket to raise an error
original_socket = socket.socket

class NetworkDisabledError(Exception):
    pass

def guarded_socket(*args, **kwargs):
    raise NetworkDisabledError("Network access is disabled during mock evaluation.")

@pytest.fixture(autouse=True)
def disable_network():
    socket.socket = guarded_socket
    yield
    socket.socket = original_socket

@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mock provider states before each test runs"""
    calendar_mock.reset()
    github_mock.reset()
    gmail_mock.reset()
    drive_mock.reset()
    yield

@pytest.fixture(autouse=True)
def patch_google_build(mocker):
    """Patch the googleapiclient build function to return our mocks"""
    def fake_build(serviceName, version, credentials=None):
        if serviceName == 'calendar':
            return calendar_mock
        elif serviceName == 'gmail':
            return gmail_mock
        elif serviceName == 'drive':
            return drive_mock
        raise ValueError(f"Unknown mock service: {serviceName}")
    
    mocker.patch('tools_calendar.build', side_effect=fake_build)
    mocker.patch('tools_gmail.build', side_effect=fake_build)
    mocker.patch('tools_drive.build', side_effect=fake_build)

@pytest.fixture(autouse=True)
def patch_github(mocker):
    """Patch the PyGithub Github constructor to return our mock"""
    mocker.patch('tools_github.Github', return_value=github_mock)

@pytest.fixture(autouse=True)
def mock_integration_token(mocker):
    """Patch get_integration_token everywhere"""
    dummy_token = {
        'access_token': 'mock_token',
        'refresh_token': 'mock_refresh',
        'scopes': 'mock_scope'
    }
    mocker.patch('tools_calendar.get_integration_token', return_value=dummy_token)
    mocker.patch('tools_github.get_integration_token', return_value=dummy_token)
    mocker.patch('tools_gmail.get_integration_token', return_value=dummy_token)
    mocker.patch('tools_drive.get_integration_token', return_value=dummy_token)

