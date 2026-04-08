import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

# ============================================================
# CHANGE THIS TO PICK WHICH TEST TO RUN
# Options: "slack" / "gmail" / "github" / "engineer" / "marketing"
# ============================================================
TEST = "marketing"


# ============================================================
# TEST 1: SLACK
# Expected result: A message appears in your #launches channel
# ============================================================
if TEST == "slack":
    import requests
    print("Testing Slack connection...")
    r = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}"},
        json={"channel": "#launches", "text": "✅ LaunchMind Slack test successful!"}
    )
    data = r.json()
    if data.get("ok"):
        print("✅ Slack works! Check your #launches channel.")
    else:
        print(f"❌ Slack failed: {data.get('error')}")


# ============================================================
# TEST 2: GMAIL
# Expected result: An email arrives in your GMAIL_RECEIVER inbox
# ============================================================
elif TEST == "gmail":
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    print("Testing Gmail...")
    msg = MIMEMultipart()
    msg["From"] = os.getenv("GMAIL_SENDER")
    msg["To"] = os.getenv("GMAIL_RECEIVER")
    msg["Subject"] = "✅ LaunchMind Gmail Test"
    msg.attach(MIMEText("<h1>Gmail is working!</h1><p>LaunchMind email test successful.</p>", "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.getenv("GMAIL_SENDER"), os.getenv("GMAIL_APP_PASSWORD"))
            server.sendmail(os.getenv("GMAIL_SENDER"), os.getenv("GMAIL_RECEIVER"), msg.as_string())
        print("✅ Gmail works! Check your inbox.")
    except Exception as e:
        print(f"❌ Gmail failed: {e}")


# ============================================================
# TEST 3: GITHUB
# Expected result: A new branch + file appears in your repo
# ============================================================
elif TEST == "github":
    import requests
    import base64

    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_REPO = os.getenv("GITHUB_REPO")
    HEADERS = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    print("Testing GitHub connection...")

    # Step 1: Get main branch SHA
    r = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/ref/heads/main",
        headers=HEADERS
    )
    if r.status_code != 200:
        print(f"❌ GitHub auth failed: {r.json()}")
        exit()

    sha = r.json()["object"]["sha"]
    print(f"✅ GitHub connected. Main branch SHA: {sha[:10]}...")

    # Step 2: Create test branch
    r = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/refs",
        headers=HEADERS,
        json={"ref": "refs/heads/test-branch", "sha": sha}
    )
    if r.status_code in [201, 422]:  # 422 means already exists
        print("✅ Branch creation works!")
    else:
        print(f"❌ Branch creation failed: {r.json()}")
        exit()

    # Step 3: Commit a test file
    html = "<h1>Test from EngineerAgent</h1>"
    r = requests.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/test.html",
        headers=HEADERS,
        json={
            "message": "Test commit from EngineerAgent",
            "content": base64.b64encode(html.encode()).decode(),
            "branch": "test-branch",
            "author": {"name": "EngineerAgent", "email": "agent@launchmind.ai"}
        }
    )
    if r.status_code in [200, 201]:
        print("✅ File commit works!")
    else:
        print(f"❌ Commit failed: {r.json()}")
        exit()

    # Step 4: Open a test PR
    r = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls",
        headers=HEADERS,
        json={
            "title": "Test PR from EngineerAgent",
            "body": "This is a test PR to verify GitHub integration.",
            "head": "test-branch",
            "base": "main"
        }
    )
    if r.status_code == 201:
        print(f"✅ PR opened: {r.json()['html_url']}")
    else:
        print(f"❌ PR failed: {r.json()}")


# ============================================================
# TEST 4: FULL ENGINEER AGENT
# Expected result: Real PR opened with generated HTML
# ============================================================
elif TEST == "engineer":
    import message_bus
    from agents import engineer_agent

    print("Testing Engineer Agent...")

    # Send a dummy product spec to the engineer
    message_bus.send_message(
        from_agent="ceo",
        to_agent="engineer",
        message_type="task",
        payload={
            "product_spec": {
                "value_proposition": "An app connecting university students with local tutors",
                "personas": [
                    {"name": "Ali", "role": "Student", "pain_point": "Can't find affordable tutors"}
                ],
                "features": [
                    {"name": "Tutor Search", "description": "Browse verified tutors by subject", "priority": 1},
                    {"name": "Session Booking", "description": "Book and pay for sessions in-app", "priority": 2},
                    {"name": "Reviews", "description": "Rate tutors after sessions", "priority": 3},
                    {"name": "Chat", "description": "Message tutors before booking", "priority": 4},
                    {"name": "Schedule", "description": "View upcoming sessions", "priority": 5}
                ],
                "user_stories": [
                    {"as_a": "student", "i_want": "to search tutors by subject", "so_that": "I find the right help"}
                ]
            },
            "instructions": "Build a landing page for this tutoring app"
        }
    )

    result = engineer_agent.run()
    if result:
        print(f"\n✅ Engineer Agent works!")
        print(f"   PR URL:    {result['pr_url']}")
        print(f"   Issue URL: {result['issue_url']}")
    else:
        print("❌ Engineer Agent failed")


# ============================================================
# TEST 5: FULL MARKETING AGENT
# Expected result: Email sent + Slack message posted
# ============================================================
elif TEST == "marketing":
    import message_bus
    from agents import marketing_agent

    print("Testing Marketing Agent...")

    message_bus.send_message(
        from_agent="ceo",
        to_agent="marketing",
        message_type="task",
        payload={
            "product_spec": {
                "value_proposition": "An app connecting university students with local tutors",
                "personas": [
                    {"name": "Ali", "role": "Student", "pain_point": "Can't find affordable tutors"}
                ],
                "features": [
                    {"name": "Tutor Search", "description": "Browse verified tutors by subject", "priority": 1},
                    {"name": "Session Booking", "description": "Book and pay for sessions in-app", "priority": 2},
                    {"name": "Reviews", "description": "Rate tutors after sessions", "priority": 3},
                    {"name": "Chat", "description": "Message tutors before booking", "priority": 4},
                    {"name": "Schedule", "description": "View upcoming sessions", "priority": 5}
                ],
                "user_stories": [
                    {"as_a": "student", "i_want": "to search tutors by subject", "so_that": "I find the right help"}
                ]
            },
            "instructions": "Generate marketing copy and launch this product"
        }
    )

    result = marketing_agent.run(pr_url="https://github.com/test/repo/pull/1")
    if result:
        print(f"\n✅ Marketing Agent works!")
        print(f"   Tagline: {result['tagline']}")
        print(f"   Check your inbox and #launches channel!")
    else:
        print("❌ Marketing Agent failed")