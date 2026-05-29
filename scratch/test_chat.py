import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.routers.chat import chat, ChatRequest
from backend.memory.activity_stream import activity_stream

async def run():
    print("Injecting fake activity logs...")
    activity_stream.log("GoalAgent", "Completed Task: Read Chapter 4")
    activity_stream.log("EmailTriage", "Archived 3 promotional emails")
    
    print("Testing Chat API for status_request...")
    req = ChatRequest(message="What have I done today?")
    try:
        response = await chat(req)
        print(f"\nSUCCESS: {response.success}")
        print(f"MESSAGE:\n{response.message}")
        print(f"\nSUGGESTED ACTIONS: {response.data.get('suggested_actions', [])}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(run())
