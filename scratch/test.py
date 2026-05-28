import sys
import os

# Add parent directory to path so we can import backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.goal_agent import goal_agent
from backend.goals.replanner import replanner

def run_test():
    try:
        print("Creating goal...")
        goal = goal_agent.create_goal(
            title="get an ai engineer internship", 
            deadline="2026-07-31",
            context=""
        )
        print(f"Goal created successfully with {len(goal.milestones)} milestones.")
        
        print("Triggering replanner...")
        updated_goal = replanner.adaptive_replan(goal.id)
        print(f"Goal replanned successfully. Total milestones: {len(updated_goal.milestones)}")
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    run_test()
