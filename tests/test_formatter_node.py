import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from langgraph_agent.app.nodes.response_formatter_node import response_formatter_node

def test_formatter_success_mcp_result():
    state = {
        "property_search_result": {
            "status": "success",
            "count": 2,
            "message": "Found 2 houses in Lahore within your budget.",
            "properties": [
                {
                    "id": 1,
                    "title": "3-Bed House in Gulberg III",
                    "city": "Lahore",
                    "area": "Gulberg III",
                    "property_type": "house",
                    "price_lakhs": 180.0,
                    "contact_name": "Ahmed Malik",
                    "contact_phone": "0300-1234567"
                },
                {
                    "id": 2,
                    "title": "2-Bed Apartment in DHA",
                    "city": "Lahore",
                    "area": "DHA",
                    "property_type": "apartment",
                    "price_lakhs": 150.0,
                    "contact_name": "Ali Raza",
                    "contact_phone": "0300-7654321"
                }
            ]
        }
    }
    
    # Mock ChatGroq to avoid actual API call during test
    with patch('langgraph_agent.app.nodes.response_formatter_node.ChatGroq') as MockChatGroq:
        mock_instance = MockChatGroq.return_value
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = AIMessage(content="I found two properties. The first is a three bed house in Gulberg three for one hundred and eighty lakhs contact Ahmed Malik. The second is a two bed apartment in DHA for one hundred and fifty lakhs contact Ali Raza. Which one interests you?")
        
        # Patch the prompt | llm behavior if needed, but since we mock ChatGroq, 
        # we can just patch the ChatPromptTemplate.from_messages(...).__or__ to return mock_chain
        with patch('langgraph_agent.app.nodes.response_formatter_node.ChatPromptTemplate') as MockPrompt:
            mock_prompt_instance = MockPrompt.from_messages.return_value
            mock_prompt_instance.__or__.return_value = mock_chain
            
            result = response_formatter_node(state)
            
            assert result["is_conversation_complete"] is True
            assert "voice_response" in result
            assert "messages" in result
            assert result["voice_response"] == "I found two properties. The first is a three bed house in Gulberg three for one hundred and eighty lakhs contact Ahmed Malik. The second is a two bed apartment in DHA for one hundred and fifty lakhs contact Ali Raza. Which one interests you?"
            assert result["messages"][0].content == result["voice_response"]

def test_formatter_no_results():
    state = {
        "property_search_result": {
            "status": "success",
            "count": 0,
            "properties": []
        }
    }
    
    result = response_formatter_node(state)
    
    assert result["is_conversation_complete"] is True
    assert "voice_response" in result
    assert "I'm sorry, but I couldn't find any properties matching your exact criteria right now." in result["voice_response"]

def test_formatter_no_markdown_characters():
    state = {
        "property_search_result": {
            "status": "success",
            "count": 1,
            "properties": [{"title": "Test"}]
        }
    }
    
    with patch('langgraph_agent.app.nodes.response_formatter_node.ChatGroq'):
        with patch('langgraph_agent.app.nodes.response_formatter_node.ChatPromptTemplate') as MockPrompt:
            mock_chain = MagicMock()
            # Mock an LLM response that ignores instructions and returns markdown
            mock_chain.invoke.return_value = AIMessage(content="*I found 1 property!* \n- Title: [Test House](#) \nWhich one interests you?")
            mock_prompt_instance = MockPrompt.from_messages.return_value
            mock_prompt_instance.__or__.return_value = mock_chain
            
            result = response_formatter_node(state)
            
            voice_response = result["voice_response"]
            assert "*" not in voice_response
            assert "#" not in voice_response
            assert "-" not in voice_response
            assert "[" not in voice_response
            assert "]" not in voice_response
            assert voice_response == "I found 1 property! \n Title: Test House() \nWhich one interests you?"
