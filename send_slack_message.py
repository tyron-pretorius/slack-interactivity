import json
import os
import re
from pathlib import Path

import dotenv

from slack_functions import send_message


dotenv.load_dotenv()

# Edit these sample values when you want to send a test message manually.
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = "#wins"
TEMPLATE_PATH = Path(__file__).with_name("message_template.json")

MESSAGE_VALUES = {
    "First": "Tyron",
    "Last": "Pretorius",
    "Company": "The Workflow Pro",
    "Size": "51-200",
    "Industry": "RevOps AI Consulting",
    "Title": "Owner",
    "Email": "tyron@theworkflowpro.com",
    "MarketoID": "1625",
    "BaseURL": "https://app-sj24.marketo.com",
}

PLACEHOLDER_PATTERN = re.compile(r"{{\s*([A-Za-z0-9_]+)\s*}}")


def render(value, replacements):
    # Replaces placeholders like {{First}} in the JSON template.
    if isinstance(value, str):
        return PLACEHOLDER_PATTERN.sub(lambda match: str(replacements[match.group(1)]), value)
    if isinstance(value, list):
        return [render(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: render(item, replacements) for key, item in value.items()}
    return value


def main():
    # This value is stored on the Slack button so the listener knows which lead is being reviewed.
    review_context = "|".join(
        [
            MESSAGE_VALUES["MarketoID"],
            MESSAGE_VALUES["Email"],
            MESSAGE_VALUES["First"],
            MESSAGE_VALUES["Last"],
            MESSAGE_VALUES["Company"],
        ]
    )
    profile_url = (
        f"{MESSAGE_VALUES['BaseURL']}/leadDatabase/loadLeadDetail"
        f"?leadId={MESSAGE_VALUES['MarketoID']}&accessZoneId=1"
    )

    # These are the values that get merged into `message_template.json`.
    values = {
        **MESSAGE_VALUES,
        "ProfileURL": profile_url,
        "ReviewContext": review_context,
    }

    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    payload = render(template, values)

    response = send_message(
        token=SLACK_BOT_TOKEN,
        channel=SLACK_CHANNEL,
        # This is Slack's fallback text for notifications and previews.
        text=f"New MQL: {MESSAGE_VALUES['First']} {MESSAGE_VALUES['Last']} - {MESSAGE_VALUES['Company']}",
        blocks=payload["blocks"],
    )
    print(response["ts"])


if __name__ == "__main__":
    main()
