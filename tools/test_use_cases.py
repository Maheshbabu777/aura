import requests
import uvicorn
import multiprocessing
import time
from loguru import logger
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.api.main import app

def run_server():
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8001, log_level="warning")

def wait_for_server():
    logger.info("Waiting for server to become ready...")
    for _ in range(30):
        try:
            requests.get("http://127.0.0.1:8001/docs")
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    return False

def test_use_cases():
    logger.info("Starting Background Server...")
    server_process = multiprocessing.Process(target=run_server)
    server_process.start()
    
    if not wait_for_server():
        logger.error("Server failed to start.")
        server_process.terminate()
        return
    
    try:
        # TEST 1: Memory Storage
        logger.info("=== TEST 1: Memory Storage ===")
        start = time.time()
        resp1 = requests.post("http://127.0.0.1:8001/chat/", json={"message": "Remember that my secret code is 8472."})
        logger.info(f"Latency: {time.time()-start:.2f}s | Response: {resp1.json()['message']}")
        time.sleep(2) # Allow memory DB to settle
        
        # TEST 2: Memory Retrieval
        logger.info("=== TEST 2: Memory Retrieval ===")
        start = time.time()
        resp2 = requests.post("http://127.0.0.1:8001/chat/", json={"message": "What is my secret code?"})
        logger.info(f"Latency: {time.time()-start:.2f}s | Response: {resp2.json()['message']}")
        
        # Need to force a session reset or let the session time out (180s default)
        # We can bypass sticky routing by manually hitting the DB or just trusting Gemini memory
        
        # TEST 3: Deep Research Spawning
        logger.info("=== TEST 3: Dynamic Web Research ===")
        start = time.time()
        resp3 = requests.post("http://127.0.0.1:8001/chat/", json={"message": "Do a deep background check on Microsoft's newest AI models."})
        logger.info(f"Latency: {time.time()-start:.2f}s | Metadata: {resp3.json().get('metadata')}")
        logger.info(f"Response: {resp3.json()['message']}")
        
        logger.info("Waiting 10s for research agent to finish...")
        time.sleep(10)
        
        # TEST 4: Follow up on research
        logger.info("=== TEST 4: Follow up on Research ===")
        start = time.time()
        resp4 = requests.post("http://127.0.0.1:8001/chat/", json={"message": "Summarize what you found from the background check."})
        logger.info(f"Latency: {time.time()-start:.2f}s | Response: {resp4.json()['message']}")
        
    finally:
        server_process.terminate()
        server_process.join()

if __name__ == "__main__":
    test_use_cases()
