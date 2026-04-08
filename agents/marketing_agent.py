import os
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openai import OpenAI
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import message_bus

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
GMAIL_SENDER = os.getenv("GMAIL_SENDER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_RECEIVER = os.getenv("GMAIL_RECEIVER")


def generate_marketing_copy(spec):
    """Use GPT to generate all marketing content."""
    print("\n📣 MARKETING AGENT: Generating marketing copy...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are an expert growth marketer for a startup called MealSteal.
Always sign off emails with 'The MealSteal Team' at the bottom. Generate marketing content
                for a startup based on its product spec.
                Return ONLY a valid JSON object with this structure:
                {
                    "tagline": "under 10 words, punchy and memorable",
                    "description": "2-3 sentence product description for landing page",
                    "email_subject": "cold outreach email subject line",
                    "email_body": "cold outreach email body (HTML format) to a potential early user",
                    "twitter_post": "tweet under 280 characters",
                    "linkedin_post": "professional LinkedIn post 2-3 sentences",
                    "instagram_post": "casual Instagram caption with hashtags"
                }"""
            },
            {
                "role": "user",
                "content": f"Generate marketing copy for:\n{json.dumps(spec, indent=2)}"
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def send_email(subject, body):
    """Send email via Gmail SMTP."""
    print(f"\n📣 MARKETING AGENT: Sending email to {GMAIL_RECEIVER}...")

    msg = MIMEMultipart()
    msg["From"] = f"MealSteal Team <{GMAIL_SENDER}>"
    msg["To"] = GMAIL_RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, msg.as_string())

    print(f"   ✅ Email sent successfully")


def post_to_slack(tagline, description, pr_url):
    """Post a Block Kit message to Slack #launches channel."""
    print(f"\n📣 MARKETING AGENT: Posting to Slack #launches...")

    payload = {
        "channel": "#launches",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚀 New Launch: {tagline}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": description
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*GitHub PR:* <{pr_url}|View Pull Request>"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Status:* ✅ Ready for Review"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Posted by LaunchMind Marketing Agent 🤖"
                    }
                ]
            }
        ]
    }

    r = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        },
        json=payload
    )

    response_data = r.json()
    if response_data.get("ok"):
        print(f"   ✅ Slack message posted successfully")
    else:
        print(f"   ❌ Slack error: {response_data.get('error')}")

    return response_data.get("ok")


def run(pr_url):
    print("\n📣 MARKETING AGENT STARTED")

    # Get product spec from message bus
    task_msg = message_bus.get_latest_message("marketing")
    if not task_msg:
        print("❌ Marketing Agent: No task received")
        return None

    spec = task_msg["payload"]["product_spec"]

    # Step 1: Generate all marketing copy
    copy = generate_marketing_copy(spec)
    print(f"\n   Tagline: {copy['tagline']}")

    # Step 2: Send email
    send_email(copy["email_subject"], copy["email_body"])

    # Step 3: Post to Slack (needs PR url from Engineer)
    post_to_slack(copy["tagline"], copy["description"], pr_url)

    print(f"\n✅ MARKETING AGENT DONE")

    # Send results back to CEO
    message_bus.send_message(
        from_agent="marketing",
        to_agent="ceo",
        message_type="result",
        payload={"copy": copy},
        parent_message_id=task_msg["message_id"]
    )

    return copy