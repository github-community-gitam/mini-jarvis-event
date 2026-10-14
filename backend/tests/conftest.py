import pytest
import socket
import sys
from unittest.mock import MagicMock


from tests.mocks.providers import calendar_mock, github_mock, gmail_mock, drive_mock

# Disable network access globally for tests
# We patch socket.socket to raise an error
original_socket = socket.socket

class NetworkDisabledError(Exception):
    pass

class GuardedSocket(original_socket):
    def connect(self, address):
        if isinstance(address, tuple) and len(address) >= 2 and address[0] in ('127.0.0.1', 'localhost', '::1'):
            return super().connect(address)
        elif isinstance(address, str) and address.startswith('/'): # Unix sockets
            return super().connect(address)
        raise NetworkDisabledError(f"Network access is disabled during mock evaluation (blocked: {address})")

@pytest.fixture(autouse=True)
def disable_network(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(socket, "socket", GuardedSocket)
        yield

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
    def fake_build(serviceName, version, credentials=None, **kwargs):
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


@pytest.fixture(autouse=True)
def no_real_database(monkeypatch):
    monkeypatch.setattr('memory.get_db_connection', lambda: None)
