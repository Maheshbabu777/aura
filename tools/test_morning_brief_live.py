"""
Test script for Morning Brief generation with real data.
"""

import sys
import os
from pathlib import Path
from loguru import logger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.heartbeat.morning_brief import MorningBriefGenerator

# Configure console logging for the test
logger.add(sys.stdout, level="INFO")

def test_morning_brief():
    print("=" * 60)
    print("AURA Morning Brief Generation Test")
    print("=" * 60)
    print()

    # Generate brief (using local model by default to preserve privacy)
    print("Initializing Morning Brief Generator (Local Mode)...")
    generator = MorningBriefGenerator(use_cloud=False)
    
    print("\nStarting generation pipeline...")
    print("This will fetch your calendar events and run an email triage.\n")
    
    try:
        brief_markdown = generator.generate()
        
        print("\n" + "=" * 60)
        print("GENERATED MORNING BRIEF:")
        print("=" * 60 + "\n")
        
        # Handle Windows console encoding
        print(brief_markdown.encode('ascii', 'ignore').decode('ascii'))
        
        print("\n" + "=" * 60)
        print("[OK] Morning Brief test PASSED!")
        return True

    except Exception as e:
        print(f"\n[FAIL] Error during generation: {e}")
        return False

if __name__ == "__main__":
    success = test_morning_brief()
    sys.exit(0 if success else 1)
