import pytest
import server
import memory
from server import CreateConversationRequest
import anyio
import socket
from tests.conftest import original_socket

def test_create_conversation_no_validation(mocker):
    socket.socket = original_socket
    mocker.patch('memory.create_conversation', return_value="12345")
    
    async def run_test():
        req = CreateConversationRequest(title="   ")
        response = await server.create_conversation(req)
        assert response["id"] == "12345"
        
    anyio.run(run_test)
