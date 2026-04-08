import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import message_bus

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


def review_html(html_content, spec):
    """Use GPT to review the HTML landing page against the product spec."""
    print("\n🔍 QA AGENT: Reviewing HTML landing page...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are a strict QA engineer reviewing a landing page.
                Check if the HTML matches the product specification.
                Return ONLY a valid JSON object:
                {
                    "verdict": "pass" or "fail",
                    "score": 1-10,
                    "issues": [
                        {"line": "approximate line or section", "comment": "specific issue found"},
                        {"line": "approximate line or section", "comment": "specific issue found"}
                    ],
                    "summary": "overall review summary in 2 sentences"
                }
                Always return at least 2 issues even if minor (for PR comments requirement)."""
            },
            {
                "role": "user",
                "content": f"Product Spec:\n{json.dumps(spec, indent=2)}\n\nHTML to review:\n{html_content}"
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def review_marketing_copy(copy, spec):
    """Use GPT to review the marketing copy."""
    print("\n🔍 QA AGENT: Reviewing marketing copy...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are a senior marketing reviewer.
                Evaluate the marketing copy against the product spec.
                Return ONLY a valid JSON object:
                {
                    "verdict": "pass" or "fail",
                    "score": 1-10,
                    "tagline_feedback": "specific feedback on the tagline",
                    "email_feedback": "specific feedback on the cold email",
                    "social_feedback": "specific feedback on social media posts",
                    "summary": "overall review summary in 2 sentences"
                }"""
            },
            {
                "role": "user",
                "content": f"Product Spec:\n{json.dumps(spec, indent=2)}\n\nMarketing Copy:\n{json.dumps(copy, indent=2)}"
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def post_pr_review_comments(pr_number, html_review):
    """Post inline review comments on the GitHub PR."""
    print(f"\n🔍 QA AGENT: Posting review comments on PR #{pr_number}...")

    # Get the latest commit SHA on the PR
    pr_data = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}",
        headers=HEADERS
    ).json()

    commit_sha = pr_data["head"]["sha"]

    # Post a general PR review with comments
    comments = []
    for issue in html_review["issues"][:2]:  # minimum 2 comments required
        comments.append({
            "path": "index.html",
            "position": 1,
            "body": f"🔍 **QA Review:** {issue['comment']}"
        })

    review_payload = {
        "commit_id": commit_sha,
        "body": f"## QA Review Report\n\n"
                f"**Verdict:** {'✅ PASS' if html_review['verdict'] == 'pass' else '❌ FAIL'}\n"
                f"**Score:** {html_review['score']}/10\n\n"
                f"**Summary:** {html_review['summary']}",
        "event": "COMMENT",
        "comments": comments
    }

    r = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/reviews",
        headers=HEADERS,
        json=review_payload
    )

    if r.status_code == 200:
        print(f"   ✅ PR review comments posted successfully")
    else:
        print(f"   ❌ PR review failed: {r.json()}")


def run():
    print("\n🔍 QA AGENT STARTED")

    # Get task from CEO
    task_msg = message_bus.get_latest_message("qa")
    if not task_msg:
        print("❌ QA Agent: No task received from CEO")
        return None

    payload = task_msg["payload"]
    html_content = payload["html_content"]
    marketing_copy = payload["marketing_copy"]
    spec = payload["product_spec"]
    pr_url = payload["pr_url"]

    # Extract PR number from URL
    pr_number = pr_url.rstrip("/").split("/")[-1]

    # Step 1: Review HTML
    html_review = review_html(html_content, spec)
    print(f"   HTML Score: {html_review['score']}/10 — {html_review['verdict'].upper()}")

    # Step 2: Review marketing copy
    copy_review = review_marketing_copy(marketing_copy, spec)
    print(f"   Copy Score: {copy_review['score']}/10 — {copy_review['verdict'].upper()}")

    # Step 3: Post PR review comments
    post_pr_review_comments(pr_number, html_review)

    # Overall verdict
    overall_verdict = "pass" if (
        html_review["verdict"] == "pass" and
        copy_review["verdict"] == "pass"
    ) else "fail"

    print(f"\n   Overall QA Verdict: {overall_verdict.upper()}")

    # Step 4: Send report back to CEO
    message_bus.send_message(
        from_agent="qa",
        to_agent="ceo",
        message_type="result",
        payload={
            "verdict": overall_verdict,
            "html_review": html_review,
            "copy_review": copy_review,
            "issues": html_review["issues"],
            "revision_needed": overall_verdict == "fail"
        },
        parent_message_id=task_msg["message_id"]
    )

    return {
        "verdict": overall_verdict,
        "html_review": html_review,
        "copy_review": copy_review
    }