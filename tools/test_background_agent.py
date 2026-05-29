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
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")

def test_dynamic_agent():
    logger.info("Starting Background Server...")
    server_process = multiprocessing.Process(target=run_server)
    server_process.start()
    
    # Wait for server to start
    time.sleep(4)
    
    try:
        logger.info("Sending Research Request...")
        
        # Send the request and measure latency
        start_time = time.time()
        response = requests.post("http://127.0.0.1:8001/chat/", json={"message": "Can you do deep research on the history of Quantum Computing?"})
        latency = time.time() - start_time
        
        data = response.json()
        logger.info(f"API Returned in {latency:.2f}s!")
        logger.info(f"Message: {data['message']}")
        logger.info(f"Metadata: {data.get('metadata')}")
        
        assert latency < 3.0, f"API blocked on background task! Latency: {latency:.2f}s"
        assert data["metadata"].get("is_agent_running") is True, "Missing UI Flag"
        
        logger.info("Waiting 10 seconds for the background agent to finish its work...")
        time.sleep(10)
        
        # Verify context injection by asking a follow up
        logger.info("Sending Follow-up Request...")
        follow_up = requests.post("http://127.0.0.1:8001/chat/", json={"message": "What did you find?"})
        logger.info(f"Follow-up Response: {follow_up.json()['message']}")
        
        # Verify Activity Stream
        conn = sqlite3.connect("memory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT agent_name, description FROM daily_logs WHERE agent_name='ResearchAgent'")
        logs = cursor.fetchall()
        conn.close()
        
        logger.info(f"Activity Stream Logs found: {len(logs)}")
        for log in logs:
            logger.info(f" - {log[1]}")
            
        assert len(logs) > 0, "No logs were written by the background agent!"
        
        logger.info("=== TEST PASSED SUCCESSFULLY ===")
        
    finally:
        server_process.terminate()
        server_process.join()

if __name__ == "__main__":
    test_dynamic_agent()
