"""
Quick test for FastAPI endpoints.
"""

import requests
import time

BASE_URL = "http://localhost:8000"


def test_api():
    """Test basic API endpoints."""

    print("Testing AURA API...")
    print("="*60)

    # Test 1: Health check
    print("\n1. Testing root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"ERROR: {e}")

    # Test 2: Health check detailed
    print("\n2. Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"ERROR: {e}")

    # Test 3: Chat endpoint
    print("\n3. Testing chat endpoint (store memory)...")
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"message": "Remember that I love Python programming"}
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"Intent: {result.get('intent')}")
        print(f"Agent: {result.get('agent')}")
        print(f"Response: {result.get('message')[:150]}...")
    except Exception as e:
        print(f"ERROR: {e}")

    # Test 4: Chat endpoint (search memory)
    print("\n4. Testing chat endpoint (search memory)...")
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"message": "What do you know about my programming interests?"}
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"Intent: {result.get('intent')}")
        print(f"Response: {result.get('message')[:150]}...")
    except Exception as e:
        print(f"ERROR: {e}")

    # Test 5: Logs endpoint
    print("\n5. Testing logs endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/logs?lines=5")
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Total lines: {result.get('total_lines')}")
        print(f"Returned lines: {result.get('returned_lines')}")
        print(f"Last log entry: {result.get('logs', [])[-1] if result.get('logs') else 'None'}")
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n" + "="*60)
    print("API Test Complete")


if __name__ == "__main__":
    test_api()
