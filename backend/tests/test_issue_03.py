import pytest
import server
import memory
import anyio
import socket
from tests.conftest import original_socket

def test_get_conversation_missing_should_return_404(mocker):
    socket.socket = original_socket
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None
    
    mocker.patch('server.get_db_connection', return_value=mock_conn)
    
    async def run_test():
        response = await server.get_conversation("123e4567-e89b-12d3-a456-426614174000")
        assert response["conversation"] is None
        
    anyio.run(run_test)
