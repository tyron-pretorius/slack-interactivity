import json
import os
import re
from pathlib import Path

import dotenv
import requests


dotenv.load_dotenv()

SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
PAYLOAD_TEMPLATE_PATH = Path(__file__).with_name("marketo_webhook_payload.json")

# Edit these sample values when you want to test the Marketo-style webhook payload manually.
MARKETO_VALUES = {
    "lead.First Name": "Tyron",
    "lead.Last Name": "Pretorius",
    "company.Company Name": "The Workflow Pro",
    "company.Num Employees": "51-200",
    "company.Industry": "RevOps AI Consulting",
    "lead.Job Title": "Owner",
    "lead.Email Address": "tyron@theworkflowpro.com",
    "lead.Id": "1625",
    "my.Base URL": "https://app-sj24.marketo.com",
}

TOKEN_PATTERN = re.compile(r"{{\s*([^{}]+?)\s*}}")


def render(value):
    # Replaces placeholders like {{lead.First Name}} in the JSON template.
    if isinstance(value, str):
        return TOKEN_PATTERN.sub(lambda match: str(MARKETO_VALUES[match.group(1)]), value)
    if isinstance(value, list):
        return [render(item) for item in value]
    if isinstance(value, dict):
        return {key: render(item) for key, item in value.items()}
    return value


def main():
    # Loads the JSON template, fills in the sample values, and sends it to Slack.
    template = json.loads(PAYLOAD_TEMPLATE_PATH.read_text(encoding="utf-8"))
    payload = render(template)
    response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=30)
    print(response.text)


if __name__ == "__main__":
    main()
