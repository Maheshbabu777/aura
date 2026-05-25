"""
Tool Calling Validation Script for Gemma 4 E4B
Validates that the local model can reliably select tools and format parameters.
Pass threshold: 70% average score across 20 test cases.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()


# Tool definitions (Pydantic-style schemas)
TOOLS = [
    {
        "name": "store_memory",
        "description": "Store information in persistent memory",
        "parameters": {
            "text": {"type": "string", "description": "The information to store"},
            "entity_type": {"type": "string", "enum": ["Person", "Goal", "Job", "Location", "Fact"]}
        },
        "required": ["text", "entity_type"]
    },
    {
        "name": "search_memory",
        "description": "Search for information in memory",
        "parameters": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"]
    },
    {
        "name": "update_memory",
        "description": "Update existing memory entry",
        "parameters": {
            "query": {"type": "string", "description": "Find the memory to update"},
            "new_text": {"type": "string", "description": "New content"}
        },
        "required": ["query", "new_text"]
    },
    {
        "name": "get_calendar",
        "description": "Get calendar events",
        "parameters": {
            "time": {"type": "string", "description": "Time period (e.g., 'today', 'tomorrow', 'morning')"}
        },
        "required": ["time"]
    },
    {
        "name": "search_emails",
        "description": "Search emails",
        "parameters": {
            "query": {"type": "string", "description": "Email search query"}
        },
        "required": ["query"]
    },
    {
        "name": "schedule_reminder",
        "description": "Schedule a reminder",
        "parameters": {
            "event": {"type": "string", "description": "What to remind about"},
            "time": {"type": "string", "description": "When to remind"}
        },
        "required": ["event", "time"]
    }
]


# Test cases with expected outputs (customized with LPU and Sarvam)
TEST_CASES = [
    # Category 1: Memory Operations
    {
        "id": 1,
        "input": "My name is John and I'm studying at University",
        "expected_tool": "store_memory",
        "expected_params": {"entity_type": "Person"},
        "category": "memory"
    },
    {
        "id": 2,
        "input": "I want to get a job at CompanyX by September",
        "expected_tool": "store_memory",
        "expected_params": {"entity_type": "Goal"},
        "category": "memory"
    },
    {
        "id": 3,
        "input": "What's my name?",
        "expected_tool": "search_memory",
        "expected_params": {"query": ["name", "user"]},
        "category": "memory"
    },
    {
        "id": 4,
        "input": "What are my career goals?",
        "expected_tool": "search_memory",
        "expected_params": {"query": ["career", "goals", "job"]},
        "category": "memory"
    },
    {
        "id": 5,
        "input": "I graduated from University last year",
        "expected_tool": "update_memory",
        "expected_params": {"query": ["University"]},
        "category": "memory"
    },
    {
        "id": 6,
        "input": "Remind me what I told you about my job search",
        "expected_tool": "search_memory",
        "expected_params": {"query": ["job", "search"]},
        "category": "memory"
    },

    # Category 2: Calendar Operations
    {
        "id": 7,
        "input": "What's on my schedule today?",
        "expected_tool": "get_calendar",
        "expected_params": {"time": ["today"]},
        "category": "calendar"
    },
    {
        "id": 8,
        "input": "Show me my meetings tomorrow",
        "expected_tool": "get_calendar",
        "expected_params": {"time": ["tomorrow"]},
        "category": "calendar"
    },
    {
        "id": 9,
        "input": "What do I have this morning?",
        "expected_tool": "get_calendar",
        "expected_params": {"time": ["morning"]},
        "category": "calendar"
    },

    # Category 3: Email Operations
    {
        "id": 10,
        "input": "Check my email",
        "expected_tool": "search_emails",
        "expected_params": {"query": ["email", "unread", "all"]},
        "category": "email"
    },
    {
        "id": 11,
        "input": "Show me emails from the recruiter",
        "expected_tool": "search_emails",
        "expected_params": {"query": ["recruiter"]},
        "category": "email"
    },
    {
        "id": 12,
        "input": "Find emails about the project",
        "expected_tool": "search_emails",
        "expected_params": {"query": ["project"]},
        "category": "email"
    },

    # Category 4: Reminder Operations
    {
        "id": 13,
        "input": "Remind me about the meeting tomorrow",
        "expected_tool": "schedule_reminder",
        "expected_params": {"event": ["meeting"], "time": ["tomorrow"]},
        "category": "reminder"
    },
    {
        "id": 14,
        "input": "Set a reminder for my interview on Friday",
        "expected_tool": "schedule_reminder",
        "expected_params": {"event": ["interview"], "time": ["Friday"]},
        "category": "reminder"
    },

    # Category 5: Multi-Tool Scenarios (test first tool selection)
    {
        "id": 15,
        "input": "Remember that I have an interview on Friday and remind me the day before",
        "expected_tool": "store_memory",
        "expected_params": {"entity_type": "Fact"},
        "category": "multi",
        "multi_tool": True
    },
    {
        "id": 16,
        "input": "Find my college name and save it",
        "expected_tool": "search_memory",
        "expected_params": {"query": ["college"]},
        "category": "multi",
        "multi_tool": True
    },
    {
        "id": 17,
        "input": "Check if I have any goals about getting a job, and if not, create one",
        "expected_tool": "search_memory",
        "expected_params": {"query": ["job", "goals"]},
        "category": "multi",
        "multi_tool": True
    },
    {
        "id": 18,
        "input": "Check my morning schedule and find related emails",
        "expected_tool": "get_calendar",
        "expected_params": {"time": ["morning"]},
        "category": "multi",
        "multi_tool": True
    },
    {
        "id": 19,
        "input": "Search my emails about interviews and remind me to prepare",
        "expected_tool": "search_emails",
        "expected_params": {"query": ["interview"]},
        "category": "multi",
        "multi_tool": True
    },
    {
        "id": 20,
        "input": "What's my goal for this week and what's on my calendar?",
        "expected_tool": "search_memory",
        "expected_params": {"query": ["goal", "week"]},
        "category": "multi",
        "multi_tool": True
    }
]


def call_ollama(prompt: str, model: str = None) -> Dict[str, Any]:
    """Call Ollama API with the given prompt."""
    if model is None:
        model = os.getenv("OLLAMA_MODEL", "gemma4:e2b")

    url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def build_tool_prompt(user_input: str) -> str:
    """Build a prompt with tool definitions for the LLM."""
    tools_json = json.dumps(TOOLS, indent=2)

    prompt = f"""You are a tool-calling AI assistant. Given a user request, you must select the appropriate tool and provide correct parameters.

Available tools:
{tools_json}

IMPORTANT RULES:
1. Use "store_memory" when user wants to save NEW information
2. Use "search_memory" when user asks about EXISTING information
3. Use "update_memory" when user wants to CHANGE existing information
4. Use "get_calendar" when user asks about their schedule, meetings, or calendar
5. Use "search_emails" when user wants to check, find, or read emails
6. Use "schedule_reminder" when user wants to be reminded about something

EXAMPLES:
User: "My name is Alice" → {{"tool": "store_memory", "parameters": {{"text": "My name is Alice", "entity_type": "Person"}}}}
User: "What's my name?" → {{"tool": "search_memory", "parameters": {{"query": "name"}}}}
User: "Check my email" → {{"tool": "search_emails", "parameters": {{"query": "email"}}}}
User: "What's on my schedule today?" → {{"tool": "get_calendar", "parameters": {{"time": "today"}}}}
User: "Remind me about the meeting" → {{"tool": "schedule_reminder", "parameters": {{"event": "meeting", "time": "later"}}}}

User request: "{user_input}"

Respond with ONLY a JSON object in this exact format:
{{
  "tool": "tool_name",
  "parameters": {{
    "param1": "value1"
  }}
}}

JSON response:"""
    return prompt


def score_response(test_case: Dict, llm_response: Dict) -> Dict[str, Any]:
    """Score the LLM response based on the rubric."""
    score = 0
    details = {
        "test_id": test_case["id"],
        "input": test_case["input"],
        "expected_tool": test_case["expected_tool"],
        "expected_params": test_case["expected_params"],
        "score": 0,
        "breakdown": {},
        "llm_response": llm_response
    }

    # Check for errors
    if "error" in llm_response:
        details["breakdown"]["error"] = llm_response["error"]
        return details

    # Try to parse the response
    try:
        response_text = llm_response.get("response", "")
        parsed = json.loads(response_text)

        # Score: Correct tool (5 points)
        if parsed.get("tool") == test_case["expected_tool"]:
            score += 5
            details["breakdown"]["correct_tool"] = True
        else:
            details["breakdown"]["correct_tool"] = False
            details["breakdown"]["actual_tool"] = parsed.get("tool")

        # Score: Correct parameters (3 points)
        params = parsed.get("parameters", {})
        expected = test_case["expected_params"]

        params_correct = True  # Start optimistic
        for key, expected_value in expected.items():
            actual_value = params.get(key, "")

            # Handle list of acceptable values (for queries)
            if isinstance(expected_value, list):
                if not any(exp.lower() in str(actual_value).lower() for exp in expected_value):
                    params_correct = False
                    break
            else:
                if expected_value != actual_value:
                    params_correct = False
                    break

        if params_correct:
            score += 3
            details["breakdown"]["correct_params"] = True
        else:
            details["breakdown"]["correct_params"] = False
            details["breakdown"]["actual_params"] = params

        # Score: Valid JSON (2 points)
        score += 2
        details["breakdown"]["valid_json"] = True

    except json.JSONDecodeError as e:
        details["breakdown"]["valid_json"] = False
        details["breakdown"]["parse_error"] = str(e)

    details["score"] = score
    return details


def run_validation() -> Dict[str, Any]:
    """Run the full validation suite."""
    model_name = os.getenv("OLLAMA_MODEL", "gemma4:e2b")

    print("=" * 60)
    print("AURA Tool Calling Validation Test")
    print("=" * 60)
    print(f"Model: {model_name}")
    print(f"Test cases: {len(TEST_CASES)}")
    print(f"Pass threshold: 70% (14/20 points average)")
    print("=" * 60)
    print()

    results = []

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"[{i}/20] Test #{test_case['id']}: {test_case['category']}")
        print(f"  Input: {test_case['input'][:60]}...")

        # Build prompt and call model
        prompt = build_tool_prompt(test_case["input"])
        llm_response = call_ollama(prompt)

        # Score the response
        result = score_response(test_case, llm_response)
        results.append(result)

        # Print result
        print(f"  Score: {result['score']}/10")
        if result['score'] < 7:
            print(f"  WARNING: {result['breakdown']}")
        print()

    # Calculate summary statistics
    total_score = sum(r["score"] for r in results)
    avg_score = total_score / len(results)
    pass_threshold = 7.0  # 70%

    passed = avg_score >= pass_threshold

    summary = {
        "timestamp": datetime.now().isoformat(),
        "model": os.getenv("OLLAMA_MODEL", "gemma4:e2b"),
        "total_cases": len(TEST_CASES),
        "total_score": total_score,
        "max_possible_score": len(TEST_CASES) * 10,
        "average_score": avg_score,
        "percentage": (avg_score / 10) * 100,
        "pass_threshold": pass_threshold,
        "passed": passed,
        "results": results
    }

    # Print summary
    print("=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    print(f"Total Score: {total_score}/{len(TEST_CASES) * 10}")
    print(f"Average Score: {avg_score:.2f}/10")
    print(f"Percentage: {summary['percentage']:.1f}%")
    print(f"Pass Threshold: {pass_threshold}/10 (70%)")
    print()

    if passed:
        print("PASSED - Proceed to Week 2 (Memory Agent)")
    else:
        print("FAILED - Adjust prompting or switch to Gemma 9B")
        print("Do NOT proceed to Week 2 until this passes.")

    print("=" * 60)

    # Save results
    output_file = "validation_results.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return summary


if __name__ == "__main__":
    run_validation()
