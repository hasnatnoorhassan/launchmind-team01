import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents import ceo_agent, product_agent
import message_bus

STARTUP_IDEA = """
A mobile app that connects customers with restaurants offering surplus end-of-day food at discounted prices.
Customers can browse available meals based on location and price, place orders.
Restaurants can list leftover food items, set discounted rates, and update availability in real time.
To encourage sustainability and reduce bias, customers cannot see the restaurant or brand name while browsing—only food details, quantity, and price are shown.
it is just an online delivery service not a dine-in service at all.
"""

def main():
    print("=" * 60)
    print("🚀 LAUNCHMIND MULTI-AGENT SYSTEM STARTING")
    print("=" * 60)

    # Step 1: CEO decomposes the idea and tasks Product Agent
    msg_id, tasks = ceo_agent.run(STARTUP_IDEA)

    # Step 2: Product Agent generates the spec
    spec = product_agent.run()
    if not spec:
        print("❌ System halted: Product agent failed")
        return

    # Step 3: CEO reviews the spec (feedback loop)
    review = ceo_agent.review_product_spec(spec)
    print(f"\n🔍 CEO Review Verdict: {review['verdict'].upper()}")
    print(f"   Reasoning: {review['reasoning']}")

    if review["verdict"] == "fail":
        print(f"\n🔄 CEO sending revision request to Product Agent...")
        message_bus.send_message(
            from_agent="ceo",
            to_agent="product",
            message_type="revision_request",
            payload={
                "idea": STARTUP_IDEA,
                "focus": review["revision_needed"],
                "startup_summary": tasks["startup_summary"]
            }
        )
        # Product agent revises
        spec = product_agent.revise_spec(spec, review["revision_needed"])
        print("\n✅ Product spec revised and approved")
    else:
        print("\n✅ CEO approved the product spec — moving forward")

    # Print full message history
    message_bus.print_full_history()

    print("\n🎉 DAY 1 COMPLETE — CEO + Product agents working!")
    print(f"   Value Proposition: {spec['value_proposition']}")
    print(f"   Features defined: {len(spec['features'])}")
    print(f"   Personas created: {len(spec['personas'])}")

if __name__ == "__main__":
    main()