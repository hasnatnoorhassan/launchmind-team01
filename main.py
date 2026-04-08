import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents import ceo_agent, product_agent, engineer_agent, marketing_agent
import message_bus

STARTUP_IDEA = """
A mobile app that connects customers with restaurants offering surplus end-of-day food at discounted prices.
Customers can browse available meals based on location and price, place orders, and pay directly through the app.
Restaurants can list leftover food items, set discounted rates, and update availability in real time.
To encourage sustainability and reduce bias, customers cannot see the restaurant or brand name while browsing—only food details, quantity, and price are shown.
this is an online delivery service only. not a dine-in option.
"""


def main():
    print("=" * 60)
    print("🚀 LAUNCHMIND MULTI-AGENT SYSTEM STARTING")
    print("=" * 60)

    # ── PHASE 1: CEO decomposes idea, tasks Product Agent ──
    msg_id, tasks = ceo_agent.run(STARTUP_IDEA)

    # ── PHASE 2: Product Agent generates spec ──
    spec = product_agent.run()
    if not spec:
        print("❌ System halted: Product agent failed")
        return

    # ── PHASE 3: CEO reviews spec (feedback loop) ──
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
        spec = product_agent.revise_spec(spec, review["revision_needed"])
        print("\n✅ Product spec revised and approved")
    else:
        print("\n✅ CEO approved the product spec")

    # ── PHASE 4: CEO dispatches Engineer + Marketing ──
    print("\n📨 CEO: Dispatching to Engineer and Marketing agents...")

    message_bus.send_message(
        from_agent="ceo",
        to_agent="engineer",
        message_type="task",
        payload={
            "product_spec": spec,
            "instructions": tasks["engineer_task"]
        }
    )

    message_bus.send_message(
        from_agent="ceo",
        to_agent="marketing",
        message_type="task",
        payload={
            "product_spec": spec,
            "instructions": tasks["marketing_task"]
        }
    )

    # ── PHASE 5: Engineer Agent builds + pushes to GitHub ──
    engineer_result = engineer_agent.run()
    if not engineer_result:
        print("❌ System halted: Engineer agent failed")
        return

    # ── PHASE 6: Marketing Agent sends email + posts to Slack ──
    marketing_result = marketing_agent.run(pr_url=engineer_result["pr_url"])
    if not marketing_result:
        print("❌ System halted: Marketing agent failed")
        return

    # ── PHASE 7: CEO posts final summary to Slack ──
    print("\n📨 CEO: Posting final summary to Slack...")
    ceo_agent.post_final_summary(
        spec=spec,
        pr_url=engineer_result["pr_url"],
        issue_url=engineer_result["issue_url"],
        tagline=marketing_result["tagline"]
    )

    # ── Print full message history ──
    message_bus.print_full_history()

    print("\n" + "=" * 60)
    print("🎉 LAUNCHMIND PIPELINE COMPLETE!")
    print("=" * 60)
    print(f"   ✅ Product spec generated")
    print(f"   ✅ GitHub PR: {engineer_result['pr_url']}")
    print(f"   ✅ GitHub Issue: {engineer_result['issue_url']}")
    print(f"   ✅ Email sent to {os.getenv('GMAIL_RECEIVER')}")
    print(f"   ✅ Slack message posted to #launches")


if __name__ == "__main__":
    main()