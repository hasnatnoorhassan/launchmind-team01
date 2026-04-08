import json
import uuid
from datetime import datetime, timezone

# Central in-memory message store
_bus = {}

def send_message(from_agent, to_agent, message_type, payload, parent_message_id=None):
    """Send a structured message from one agent to another."""
    message = {
        "message_id": str(uuid.uuid4()),
        "from_agent": from_agent,
        "to_agent": to_agent,
        "message_type": message_type,  # task / result / revision_request / confirmation
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "parent_message_id": parent_message_id
    }

    if to_agent not in _bus:
        _bus[to_agent] = []

    _bus[to_agent].append(message)

    print(f"\n📨 [{from_agent.upper()} → {to_agent.upper()}] "
          f"Type: {message_type} | ID: {message['message_id'][:8]}")

    return message["message_id"]


def get_messages(agent_name):
    """Get all messages addressed to an agent."""
    return _bus.get(agent_name, [])


def get_latest_message(agent_name):
    """Get the most recent message for an agent."""
    messages = _bus.get(agent_name, [])
    return messages[-1] if messages else None


def get_full_history():
    """Return the complete message log across all agents."""
    all_messages = []
    for agent_messages in _bus.values():
        all_messages.extend(agent_messages)
    all_messages.sort(key=lambda x: x["timestamp"])
    return all_messages


def print_full_history():
    """Print the entire message history in a readable format."""
    print("\n" + "="*60)
    print("📋 FULL MESSAGE HISTORY")
    print("="*60)
    for msg in get_full_history():
        print(f"\n[{msg['timestamp']}]")
        print(f"  FROM : {msg['from_agent']}")
        print(f"  TO   : {msg['to_agent']}")
        print(f"  TYPE : {msg['message_type']}")
        print(f"  ID   : {msg['message_id'][:8]}")
        if msg['parent_message_id']:
            print(f"  REPLY TO: {msg['parent_message_id'][:8]}")
        print(f"  PAYLOAD: {json.dumps(msg['payload'], indent=4)}")
    print("\n" + "="*60)