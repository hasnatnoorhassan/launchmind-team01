import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import message_bus

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_product_spec(task_payload):
    """Use GPT to generate a full product specification."""
    print("\n📋 PRODUCT AGENT: Generating product specification...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are an expert product manager. Given a startup idea and focus areas,
                generate a detailed product specification.
                
                Respond ONLY with a valid JSON object with exactly this structure:
                {
                    "value_proposition": "one sentence describing what the product does and for whom",
                    "personas": [
                        {"name": "...", "role": "...", "pain_point": "..."},
                        {"name": "...", "role": "...", "pain_point": "..."}
                    ],
                    "features": [
                        {"name": "...", "description": "...", "priority": 1},
                        {"name": "...", "description": "...", "priority": 2},
                        {"name": "...", "description": "...", "priority": 3},
                        {"name": "...", "description": "...", "priority": 4},
                        {"name": "...", "description": "...", "priority": 5}
                    ],
                    "user_stories": [
                        {"as_a": "...", "i_want": "...", "so_that": "..."},
                        {"as_a": "...", "i_want": "...", "so_that": "..."},
                        {"as_a": "...", "i_want": "...", "so_that": "..."}
                    ]
                }"""
            },
            {
                "role": "user",
                "content": f"Startup idea: {task_payload['idea']}\n\nFocus: {task_payload['focus']}"
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def revise_spec(original_spec, feedback):
    """Revise the spec based on CEO feedback."""
    print("\n🔄 PRODUCT AGENT: Revising spec based on CEO feedback...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are an expert product manager. Revise the given product specification
                based on the CEO's feedback. Make it more specific and actionable.
                Return ONLY a valid JSON object with the same structure as the original spec."""
            },
            {
                "role": "user",
                "content": f"Original spec:\n{json.dumps(original_spec, indent=2)}\n\nCEO Feedback: {feedback}"
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def run():
    print("\n📋 PRODUCT AGENT STARTED")

    # Get task from CEO
    task_msg = message_bus.get_latest_message("product")
    if not task_msg:
        print("❌ Product Agent: No task received from CEO")
        return None

    task_payload = task_msg["payload"]
    spec = generate_product_spec(task_payload)
    print(f"\n✅ PRODUCT AGENT: Spec generated — {spec['value_proposition']}")

    # Send spec back to CEO for review
    message_bus.send_message(
        from_agent="product",
        to_agent="ceo",
        message_type="result",
        payload={"product_spec": spec},
        parent_message_id=task_msg["message_id"]
    )

    return spec