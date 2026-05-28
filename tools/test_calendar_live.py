"""
Test script for Google Calendar API integration.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.integrations.calendar import calendar_client

def test_calendar():
    print("=" * 60)
    print("AURA Calendar Integration Test")
    print("=" * 60)
    print()

    print("1. Authenticating with Google Calendar...")
    print("   (A browser window may open asking you to log in)")
    
    if not calendar_client.authenticate():
        print("[FAIL] Authentication failed!")
        return False
        
    print("[OK] Authentication successful!")
    print()
    
    print("2. Fetching today's events...")
    today_events = calendar_client.get_today_events()
    
    print(f"Found {len(today_events)} events for today:")
    for i, event in enumerate(today_events, 1):
        summary = event.get('summary', 'No Title').encode('ascii', 'ignore').decode('ascii')
        is_all_day = event.get('is_all_day', False)
        start = event.get('start', '')
        
        time_str = "All Day" if is_all_day else start
        print(f"  {i}. [{time_str}] {summary}")
        
    print()
    print("3. Fetching tomorrow's events...")
    tomorrow_events = calendar_client.get_tomorrow_events()
    
    print(f"Found {len(tomorrow_events)} events for tomorrow:")
    for i, event in enumerate(tomorrow_events, 1):
        summary = event.get('summary', 'No Title').encode('ascii', 'ignore').decode('ascii')
        is_all_day = event.get('is_all_day', False)
        start = event.get('start', '')
        
        time_str = "All Day" if is_all_day else start
        print(f"  {i}. [{time_str}] {summary}")
        
    print()
    print("=" * 60)
    print("[OK] Calendar integration test PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_calendar()
    sys.exit(0 if success else 1)
