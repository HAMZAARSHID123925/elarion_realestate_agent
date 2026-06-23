import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage

# We import the app from api.py. Make sure to run this from root dir.
from langgraph_agent.api import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@patch("langgraph_agent.api.graph")
def test_chat_endpoint_full_message(mock_graph):
    # Mock the graph execution
    mock_result_state = {
        "conversation_id": "test-001",
        "user_name": "Ali",
        "location": "Lahore",
        "budget": "200 lakhs",
        "property_type": "house",
        "messages": [AIMessage(content="I found properties in Lahore.")],
        "voice_response": "I found three houses in Lahore under two hundred lakhs. Which one interests you?",
        "is_conversation_complete": True
    }
    mock_graph.invoke.return_value = mock_result_state
    
    payload = {
        "conversation_id": "test-001",
        "message": "Hi I am Ali I want a house in Lahore under 200 lakhs",
        "state": {}
    }
    
    response = client.post("/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "voice_response" in data
    assert data["voice_response"] == "I found three houses in Lahore under two hundred lakhs. Which one interests you?"
    
    assert "state" in data
    assert data["state"]["conversation_id"] == "test-001"
    assert data["state"]["user_name"] == "Ali"
    assert data["state"]["is_conversation_complete"] is True

@patch("langgraph_agent.api.graph")
def test_chat_endpoint_state_preservation(mock_graph):
    # First request mock
    mock_graph.invoke.return_value = {
        "conversation_id": "test-002",
        "user_name": "Sara",
        "messages": [AIMessage(content="What is your budget?")],
        "is_conversation_complete": False
    }
    
    payload1 = {
        "conversation_id": "test-002",
        "message": "Hi, I am Sara.",
        "state": {}
    }
    
    response1 = client.post("/chat", json=payload1)
    state1 = response1.json()["state"]
    
    assert state1["user_name"] == "Sara"
    assert state1["is_conversation_complete"] is False
    
    # Second request mock, simulating state passed back
    mock_graph.invoke.return_value = {
        "conversation_id": "test-002",
        "user_name": "Sara",
        "budget": "150 lakhs",
        "messages": [AIMessage(content="What city?")],
        "is_conversation_complete": False
    }
    
    payload2 = {
        "conversation_id": "test-002",
        "message": "My budget is 150 lakhs.",
        "state": state1
    }
    
    response2 = client.post("/chat", json=payload2)
    state2 = response2.json()["state"]
    
    assert state2["user_name"] == "Sara"
    assert state2["budget"] == "150 lakhs"
    
    # Verify that the graph was called with the state from request 1
    call_args = mock_graph.invoke.call_args[0][0]
    assert call_args["user_name"] == "Sara"
