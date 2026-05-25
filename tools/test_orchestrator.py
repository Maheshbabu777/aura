"""
Quick test script for OrchestratorAgent end-to-end functionality.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.agents.orchestrator import OrchestratorAgent
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stdout, level="INFO")


def test_orchestrator():
    """Test orchestrator with various user inputs."""

    print("="*60)
    print("ORCHESTRATOR TEST")
    print("="*60)

    orchestrator = OrchestratorAgent()

    # Test cases
    test_cases = [
        "Hello, I'm testing AURA",
        "Remember that I work at TechCorp as a software engineer",
        "What do you know about my job?",
        "I want to become an ML engineer by December",  # Not implemented yet
        "Update my workplace to NewCorp",
    ]

    for i, message in enumerate(test_cases, 1):
        print(f"\n--- Test {i} ---")
        print(f"User: {message}")

        try:
            result = orchestrator.route(message)
            print(f"Success: {result['success']}")
            print(f"Intent: {result['intent']}")
            print(f"Agent: {result['agent']}")
            print(f"Response: {result['message'][:200]}...")  # Truncate long responses

        except Exception as e:
            print(f"ERROR: {e}")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    test_orchestrator()
