"""
Live test script for the Goal Agent using the cloud Gemini model.
"""

import sys
import os
import json
from rich.console import Console

# Add parent directory to path so we can import backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.goal_agent import goal_agent

console = Console()

def main():
    console.print("\n[bold blue]=== AURA Goal Tracking Live Test ===[/bold blue]")
    
    goal_title = input("\nEnter a high-level goal you want to achieve (e.g., 'Get an ML Internship'): ")
    deadline = input("Enter a deadline (e.g., '2026-12-31' or leave blank): ")
    context = input("Enter any syllabus or context (or leave blank): ")
    
    if not deadline:
        deadline = None
        
    console.print("\n[yellow]Decomposing goal using Gemini Cloud Model... This might take a few seconds.[/yellow]")
    
    try:
        goal = goal_agent.create_goal(title=goal_title, context=context, deadline=deadline)
        
        console.print(f"\n[bold green]Goal Created: {goal.title}[/bold green]")
        
        for i, milestone in enumerate(goal.milestones, 1):
            console.print(f"\n  [bold cyan]Milestone {i}: {milestone.title}[/bold cyan]")
            console.print(f"  {milestone.description}")
            
            for j, task in enumerate(milestone.weekly_tasks, 1):
                console.print(f"    [white]- Task {j}: {task.title}[/white]")
                if task.description:
                    console.print(f"      [dim]{task.description}[/dim]")
                    
        console.print(f"\n[green]Goal successfully saved to database with ID: {goal.id}[/green]\n")
        
        do_replan = input("Do you want to simulate falling behind and triggering Adaptive Replanning? (y/n): ")
        if do_replan.lower() == 'y':
            console.print("\n[yellow]Triggering Adaptive Replanner...[/yellow]")
            from backend.goals.replanner import replanner
            updated_goal = replanner.adaptive_replan(goal.id)
            
            console.print(f"\n[bold green]Goal Replanned: {updated_goal.title}[/bold green]")
            for i, milestone in enumerate(updated_goal.milestones, 1):
                console.print(f"\n  [bold cyan]Milestone {i}: {milestone.title}[/bold cyan]")
                for j, task in enumerate(milestone.weekly_tasks, 1):
                    console.print(f"    [white]- Task {j}: {task.title}[/white]")
                    if task.description:
                        console.print(f"      [dim]{task.description}[/dim]")
            
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    main()
