import requests
import uvicorn
import multiprocessing
import time
from loguru import logger
import sqlite3
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.api.main import app

def run_server():
    # Windows multiprocessing requires uvicorn to use an import string instead of the app object
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8001, log_level="warning")

def wait_for_server():
    logger.info("Waiting for server to become ready...")
    for _ in range(30):
        try:
            requests.get("http://127.0.0.1:8001/docs")
            logger.info("Server is up!")
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    return False

def verify_logs(agent_name, expected_min_count):
    conn = sqlite3.connect("memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT description FROM daily_logs WHERE agent_name=?", (agent_name,))
    logs = cursor.fetchall()
    conn.close()
    
    logger.info(f"--- Activity Stream Logs for {agent_name} ---")
    for log in logs:
        logger.info(f" - {log[0]}")
    
    assert len(logs) >= expected_min_count, f"Expected at least {expected_min_count} logs for {agent_name}, got {len(logs)}"

def test_multiple_scenarios():
    logger.info("Starting Background Server (Wait 15s for models to load into RAM)...")
    server_process = multiprocessing.Process(target=run_server)
    server_process.start()
    
    if not wait_for_server():
        logger.error("Server failed to start in time.")
        server_process.terminate()
        return
    
    try:
        # TEST 1: Normal Conversational Query
        logger.info("=== TEST CASE 1: Normal Conversation ===")
        start = time.time()
        resp1 = requests.post("http://127.0.0.1:8001/chat/", json={"message": "Hi AURA, how are you?"})
        latency1 = time.time() - start
        
        data1 = resp1.json()
        logger.info(f"Latency: {latency1:.2f}s | Response: {data1['message']}")
        assert (data1.get("metadata") or {}).get("is_agent_running", False) is False, "Normal chat should not flag agent running"
        
        time.sleep(1)
        
        # TEST 2: Status Request
        logger.info("=== TEST CASE 2: Status Intent ===")
        start = time.time()
        resp2 = requests.post("http://127.0.0.1:8001/chat/", json={"message": "What is my status today?"})
        latency2 = time.time() - start
        
        data2 = resp2.json()
        logger.info(f"Latency: {latency2:.2f}s | Response: {data2['message']}")
        assert data2["intent"] == "status_request"
        assert (data2.get("metadata") or {}).get("is_agent_running", False) is False
        
        time.sleep(1)

        # TEST 3: Dynamic Agent Spawning
        logger.info("=== TEST CASE 3: Dynamic Research Spawn ===")
        start = time.time()
        resp3 = requests.post("http://127.0.0.1:8001/chat/", json={"message": "Can you deep research the origins of artificial intelligence?"})
        latency3 = time.time() - start
        
        data3 = resp3.json()
        logger.info(f"Latency: {latency3:.2f}s | Response: {data3['message']}")
        assert latency3 < 3.0, "API blocked on background task! Should return instantly."
        assert (data3.get("metadata") or {}).get("is_agent_running") is True, "Missing UI Flag for spinning wheel"
        
        # TEST 4: Chat while agent is running
        logger.info("=== TEST CASE 4: Async Non-Blocking Chat ===")
        start = time.time()
        resp4 = requests.post("http://127.0.0.1:8001/chat/", json={"message": "While you do that, what's 2+2?"})
        latency4 = time.time() - start
        
        data4 = resp4.json()
        logger.info(f"Latency: {latency4:.2f}s | Response: {data4['message']}")
        assert "4" in data4['message']
        
        logger.info("Waiting 12 seconds for the background agent to complete its research...")
        time.sleep(12)
        
        # TEST 5: Verify Context Injection
        logger.info("=== TEST CASE 5: Context Injection Follow-up ===")
        start = time.time()
        resp5 = requests.post("http://127.0.0.1:8001/chat/", json={"message": "What did you find in the research?"})
        latency5 = time.time() - start
        
        data5 = resp5.json()
        logger.info(f"Latency: {latency5:.2f}s | Response: {data5['message']}")
        
        # Verify the agent logged its progress
        verify_logs("ResearchAgent", 3)
        
        logger.info("=== ALL END-TO-END TESTS PASSED SUCCESSFULLY ===")
        
    except Exception as e:
        logger.error(f"Test Failed: {e}")
        raise e
    finally:
        server_process.terminate()
        server_process.join()

if __name__ == "__main__":
    test_multiple_scenarios()
