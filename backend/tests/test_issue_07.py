from fastapi.testclient import TestClient
import pytest
from server import app
import memory

client = TestClient(app)

def test_get_recent_messages_order(mocker):
    # Mock get_db_connection
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    # Simulate DB returning newest first (DESC)
    mock_cursor.fetchall.return_value = [
        {"id": 3, "content": "Third"},
        {"id": 2, "content": "Second"},
        {"id": 1, "content": "First"}
    ]
    
    mocker.patch('memory.get_db_connection', return_value=mock_conn)
    
    # In the defective seeded code, it returns the rows as-is (newest first).
    # Participants should fix it to return oldest first (chronological) by adding reversed().
    # We assert the current defective behavior to prove the seed is active.
    messages = memory.get_recent_messages("conv123", limit=100)
    
    assert len(messages) == 3
    assert messages[0]["content"] == "Third"
    assert messages[1]["content"] == "Second"
    assert messages[2]["content"] == "First"
