import time
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.orchestrator import orchestrator

print("=== AURA Intent Routing Speed Test ===")
print("Testing routing speed with the 815MB gemma3:1b model...\n")

start_time = time.time()
result = orchestrator.route("Hey AURA, what is my status today?")
end_time = time.time()

print(f"Result: {result.get('intent')}")
print(f"Time Taken: {end_time - start_time:.2f} seconds")

if end_time - start_time < 3.0:
    print("\nSUCCESS: Routing is incredibly fast because it's using the correct small model!")
else:
    print("\nWARNING: Routing is still slow. This usually means the model had to cold-boot into memory.")
