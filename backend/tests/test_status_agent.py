import pytest
import asyncio
from unittest.mock import patch

from backend.agents.status_agent import StatusAgent


@pytest.fixture
def status_agent():
    return StatusAgent()

@pytest.mark.asyncio
@patch("backend.agents.status_agent.gemini_client.generate")
@patch("backend.agents.status_agent.activity_stream.get_today_logs")
@patch("backend.agents.status_agent.MemoryStore.search_memory")
async def test_get_daily_status(mock_search_memory, mock_get_logs, mock_generate, status_agent):
    # Mock data
    mock_get_logs.return_value = [
        {"timestamp": "2026-05-29T14:00:00Z", "agent_name": "GoalAgent", "description": "Finished Math Homework"}
    ]
    mock_search_memory.return_value = [
        {"text": "User is studying for exams until June 11"}
    ]
    
    mock_generate.return_value = '''
    {
      "summary_text": "You finished your math homework today. Keep up the good work for your exams!",
      "suggested_actions": ["Review physics notes"]
    }
    '''
    
    chat_history = [
        {"role": "user", "content": "I am feeling productive today!"}
    ]
    
    response = await status_agent.get_daily_status(chat_history)
    
    assert response["summary_text"] == "You finished your math homework today. Keep up the good work for your exams!"
    assert "Review physics notes" in response["suggested_actions"]
    
    # Verify parallel tasks were called
    mock_get_logs.assert_called_once()
    mock_search_memory.assert_called_once()
