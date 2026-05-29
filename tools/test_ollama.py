"""Quick test to verify Ollama is responding"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_ollama():
    url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/generate"
    model = os.getenv("OLLAMA_MODEL", "gemma3:1b")

    print(f"Testing Ollama at {url}")
    print(f"Using model: {model}")
    print()

    payload = {
        "model": model,
        "prompt": "Say hello in one word",
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()

        print("SUCCESS: Ollama is responding")
        print(f"Response: {result.get('response', 'N/A')}")
        return True
    except Exception as e:
        print(f"FAILED: {str(e)}")
        return False

if __name__ == "__main__":
    test_ollama()
