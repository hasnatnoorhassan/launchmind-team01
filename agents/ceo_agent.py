import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import message_bus

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def decompose_idea(startup_idea):
    """LLM Call #1: Break startup idea into tasks for each agent."""
    print("\n🧠 CEO: Decomposing startup idea into agent tasks...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are the CEO of a startup. Given a startup idea, 
                decompose it into specific tasks for three agents:
                1. Product Agent - define personas, features, user stories
                2. Engineer Agent - what to build technically
                3. Marketing Agent - how to position and market it
                
                Respond ONLY with a valid JSON object like this:
                {
                    "product_task": "specific instructions for product agent",
                    "engineer_task": "specific instructions for engineer agent", 
                    "marketing_task": "specific instructions for marketing agent",
                    "startup_summary": "one sentence summary of the startup"
                }"""
            },
            {
                "role": "user",
                "content": f"Startup idea: {startup_idea}"
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def review_product_spec(spec):
    """LLM Call #2: Review the product agent's output."""
    print("\n🔍 CEO: Reviewing product spec...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are a critical CEO reviewing a product specification.
                Evaluate if the spec is specific enough to build and market a real product.
                Check: Are personas realistic and specific? Are features concrete? 
                Are user stories actionable?
                
                Respond ONLY with a valid JSON object:
                {
                    "verdict": "pass" or "fail",
                    "reasoning": "explanation of your decision",
                    "revision_needed": "what specifically needs to be improved (empty string if pass)"
                }"""
            },
            {
                "role": "user",
                "content": f"Product spec to review:\n{json.dumps(spec, indent=2)}"
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def run(startup_idea):
    print(f"\n🚀 CEO AGENT STARTED")
    print(f"💡 Startup Idea: {startup_idea}")

    # --- LLM Call #1: Decompose the idea ---
    tasks = decompose_idea(startup_idea)
    print(f"\n✅ CEO: Tasks decomposed — {tasks['startup_summary']}")

    # --- Send task to Product Agent ---
    msg_id = message_bus.send_message(
        from_agent="ceo",
        to_agent="product",
        message_type="task",
        payload={
            "idea": startup_idea,
            "focus": tasks["product_task"],
            "startup_summary": tasks["startup_summary"]
        }
    )

    return msg_id, tasks