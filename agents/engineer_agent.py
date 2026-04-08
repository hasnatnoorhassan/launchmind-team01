import os
import json
import base64
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


def generate_html(spec):
    """Use GPT to generate a landing page based on product spec."""
    print("\n🔧 ENGINEER AGENT: Generating HTML landing page...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are a frontend developer. Generate a complete, beautiful 
                HTML landing page for a startup. Include:
                - A compelling headline and subheadline
                - A features section listing all features
                - A call-to-action button
                - Clean, modern inline CSS styling
                - Responsive design
                Return ONLY the raw HTML code, nothing else. No markdown, no backticks."""
            },
            {
                "role": "user",
                "content": f"Build a landing page for this product:\n{json.dumps(spec, indent=2)}"
            }
        ]
    )

    return response.choices[0].message.content.strip()


def generate_pr_details(spec):
    """Use GPT to generate PR title, body and issue description."""
    print("\n🔧 ENGINEER AGENT: Generating PR and issue details...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are a software engineer writing GitHub PR details.
                Return ONLY a valid JSON object with this structure:
                {
                    "issue_title": "...",
                    "issue_body": "...",
                    "pr_title": "...",
                    "pr_body": "...",
                    "branch_name": "agent-landing-page"
                }"""
            },
            {
                "role": "user",
                "content": f"Generate PR and issue details for this product:\n{json.dumps(spec, indent=2)}"
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def get_main_branch_sha():
    """Get the SHA of the main branch."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/git/ref/heads/main"
    r = requests.get(url, headers=HEADERS)
    return r.json()["object"]["sha"]


def create_branch(branch_name, sha):
    """Create a new branch from main."""
    print(f"\n🔧 ENGINEER AGENT: Creating branch '{branch_name}'...")
    url = f"https://api.github.com/repos/{GITHUB_REPO}/git/refs"
    r = requests.post(url, headers=HEADERS, json={
        "ref": f"refs/heads/{branch_name}",
        "sha": sha
    })
    if r.status_code == 422:
        print(f"   Branch already exists, continuing...")
    else:
        print(f"   ✅ Branch created")


def commit_html(html_content, branch_name):
    """Commit the HTML file to the branch."""
    print(f"\n🔧 ENGINEER AGENT: Committing index.html to '{branch_name}'...")
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/index.html"

    # Check if file already exists (get its SHA if it does)
    existing = requests.get(url, headers=HEADERS, params={"ref": branch_name})
    payload = {
        "message": "Add landing page [by EngineerAgent]",
        "content": base64.b64encode(html_content.encode()).decode(),
        "branch": branch_name,
        "author": {
            "name": "EngineerAgent",
            "email": "agent@launchmind.ai"
        }
    }
    if existing.status_code == 200:
        payload["sha"] = existing.json()["sha"]

    r = requests.put(url, headers=HEADERS, json=payload)
    print(f"   ✅ File committed")
    return r.json()


def create_github_issue(issue_title, issue_body):
    """Create a GitHub issue."""
    print(f"\n🔧 ENGINEER AGENT: Creating GitHub issue...")
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    r = requests.post(url, headers=HEADERS, json={
        "title": issue_title,
        "body": issue_body
    })
    issue_url = r.json()["html_url"]
    print(f"   ✅ Issue created: {issue_url}")
    return issue_url


def open_pull_request(pr_title, pr_body, branch_name):
    """Open a pull request."""
    print(f"\n🔧 ENGINEER AGENT: Opening pull request...")
    url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls"
    r = requests.post(url, headers=HEADERS, json={
        "title": pr_title,
        "body": pr_body,
        "head": branch_name,
        "base": "main"
    })

    data = r.json()

    # If PR already exists, fetch the existing one
    if r.status_code == 422:
        print("   PR already exists, fetching existing PR...")
        existing = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/pulls",
            headers=HEADERS,
            params={"head": f"{GITHUB_REPO.split('/')[0]}:{branch_name}", "state": "open"}
        )
        prs = existing.json()
        if prs:
            pr_url = prs[0]["html_url"]
            print(f"   ✅ Existing PR found: {pr_url}")
            return pr_url
        else:
            print("   ❌ Could not find existing PR")
            return ""

    pr_url = data.get("html_url", "")
    print(f"   ✅ PR opened: {pr_url}")
    return pr_url


def run():
    print("\n⚙️  ENGINEER AGENT STARTED")

    # Get product spec from message bus
    task_msg = message_bus.get_latest_message("engineer")
    if not task_msg:
        print("❌ Engineer Agent: No task received")
        return None

    spec = task_msg["payload"]["product_spec"]

    # Step 1: Generate HTML
    html_content = generate_html(spec)

    # Step 2: Generate PR + issue details
    pr_details = generate_pr_details(spec)
    branch_name = pr_details["branch_name"]

    # Step 3: GitHub actions
    sha = get_main_branch_sha()
    create_branch(branch_name, sha)
    commit_html(html_content, branch_name)
    issue_url = create_github_issue(pr_details["issue_title"], pr_details["issue_body"])
    pr_url = open_pull_request(pr_details["pr_title"], pr_details["pr_body"], branch_name)

    print(f"\n✅ ENGINEER AGENT DONE")
    print(f"   Issue: {issue_url}")
    print(f"   PR:    {pr_url}")

    # Send results back to CEO
    message_bus.send_message(
        from_agent="engineer",
        to_agent="ceo",
        message_type="result",
        payload={
            "pr_url": pr_url,
            "issue_url": issue_url,
            "branch_name": branch_name,
            "html_preview": html_content[:200] + "..."
        },
        parent_message_id=task_msg["message_id"]
    )

    return {"pr_url": pr_url, "issue_url": issue_url}