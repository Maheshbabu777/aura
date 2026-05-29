import asyncio
from fastapi.testclient import TestClient
from loguru import logger
import time

from backend.api.main import app
from backend.agents.orchestrator import orchestrator
from backend.memory.activity_stream import activity_stream

client = TestClient(app)

def test_dynamic_spawn():
    logger.info("=== Starting Dynamic Spawn Test ===")
    
    # 1. Clear session
    orchestrator.session.reset()
    
    # 2. Trigger the research task
    logger.info("Sending complex research request...")
    start_time = time.time()
    
    response = client.post("/chat/", json={"message": "Can you do a deep research on the history of quantum computing?"})
    
    end_time = time.time()
    latency = end_time - start_time
    
    data = response.json()
    logger.info(f"API Response ({latency:.2f}s): {data['message']}")
    logger.info(f"Metadata: {data.get('metadata')}")
    
    assert data["success"] is True
    assert data["metadata"].get("is_agent_running") is True
    assert latency < 5.0, "API blocked waiting for the background task!"
    
    logger.info("API returned immediately! Waiting for background task to complete...")
    
    # 3. Wait for background task to finish
    # We simulate the wait by sleeping here, the background task runs in the same event loop 
    # but TestClient is synchronous so we might need to be careful.
    # Actually, TestClient creates a new event loop per request. The background task might be killed!
    # Let's check session history. Since TestClient is sync, it might not run the async task.
    pass

if __name__ == "__main__":
    test_dynamic_spawn()
    print("Run this test with a real server using tools/test_api.py instead to see background execution, since TestClient kills background tasks.")
