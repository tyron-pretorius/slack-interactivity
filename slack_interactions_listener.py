import hashlib
import hmac
import json
import os
import time

import dotenv
from flask import Flask, Response, jsonify, request

from marketo_functions import update_lead
from slack_functions import SlackApiError, add_reaction, get_user_profile, open_modal


dotenv.load_dotenv()

app = Flask(__name__)

### Update These ###
# This keeps the Marketo API field names in one place.
MARKETO_FIELD_NAMES = {
    "status": "leadStatus",
    "status_reason": "leadStatusReason",
    "owner_email": "ownerEmailAddress",
}

# These values come from `.env` and are used for every incoming Slack interaction.
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]

# These IDs connect the modal form fields to the code below.
STATUS_BLOCK_ID = "status_block"
STATUS_ACTION_ID = "status_action"
STATUS_REASON_BLOCK_ID = "status_reason_block"
STATUS_REASON_ACTION_ID = "status_reason_action"
SALES_OWNER_BLOCK_ID = "sales_owner_block"
SALES_OWNER_ACTION_ID = "sales_owner_action"


def verify_slack_signature(timestamp, body, slack_signature):
    # Confirms that the request really came from Slack.
    # Without this check, anyone could post fake payloads to this listener URL.
    try:
        request_age = abs(time.time() - int(timestamp))
    except ValueError:
        return False

    if request_age > 60 * 5:
        return False

    basestring = f"v0:{timestamp}:{body.decode('utf-8')}".encode("utf-8")
    expected_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode("utf-8"),
        basestring,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, slack_signature)


def build_review_modal(review_context):
    # Builds the modal a user sees after clicking the Review button in Slack.
    lead_label = " ".join([review_context.get("first", ""), review_context.get("last", "")]).strip()
    if not lead_label:
        lead_label = review_context.get("company", "lead")

    return {
        "type": "modal",
        "callback_id": "mql_review_submission",
        "title": {"type": "plain_text", "text": "Review MQL"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": json.dumps(review_context),
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"Updating *{lead_label}*"}},
            {
                "type": "input",
                "block_id": STATUS_BLOCK_ID,
                "label": {"type": "plain_text", "text": "Status"},
                "element": {
                    "type": "static_select",
                    "action_id": STATUS_ACTION_ID,
                    "placeholder": {"type": "plain_text", "text": "Select a status"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "SAL"}, "value": "SAL"},
                        {"text": {"type": "plain_text", "text": "SSL"}, "value": "SSL"},
                        {"text": {"type": "plain_text", "text": "Disqualified"}, "value": "Disqualified"},
                    ],
                },
            },
            {
                "type": "input",
                "block_id": STATUS_REASON_BLOCK_ID,
                "label": {"type": "plain_text", "text": "Status Reason"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": STATUS_REASON_ACTION_ID,
                    "multiline": True,
                },
            },
            {
                "type": "input",
                "optional": True,
                "block_id": SALES_OWNER_BLOCK_ID,
                "label": {"type": "plain_text", "text": "Sales Owner"},
                "element": {
                    "type": "users_select",
                    "action_id": SALES_OWNER_ACTION_ID,
                    "placeholder": {"type": "plain_text", "text": "Select a sales owner"},
                },
            },
        ],
    }


def get_sales_owner_email(slack_user_id):
    # If a user was selected in the modal, fetch their Slack profile email.
    if not slack_user_id:
        return ""
    profile = get_user_profile(SLACK_BOT_TOKEN, slack_user_id)
    return profile.get("email", "")


@app.get("/")
def healthcheck():
    return "ok", 200


@app.post("/slack/interactions")
def slack_interactions():
    # Slack signs every interaction request. We verify that signature before doing anything.
    slack_signature = request.headers.get("X-Slack-Signature", "")
    slack_timestamp = request.headers.get("X-Slack-Request-Timestamp", "0")
    raw_body = request.get_data()

    if not verify_slack_signature(slack_timestamp, raw_body, slack_signature):
        return Response("invalid signature", status=401)

    payload = json.loads(request.form["payload"])

    if payload.get("type") == "block_actions":
        # This runs when someone clicks the Review button on the Slack message.
        action = payload["actions"][0]
        if action.get("action_id") == "open_review_modal":
            marketo_id, email, first, last, company = action["value"].split("|")
            open_modal(
                SLACK_BOT_TOKEN,
                payload["trigger_id"],
                build_review_modal(
                    {
                        "marketo_id": marketo_id,
                        "email": email,
                        "first": first,
                        "last": last,
                        "company": company,
                        "channel_id": payload["channel"]["id"],
                        "message_ts": payload["message"]["ts"],
                    }
                ),
            )
        return jsonify({"ok": True})

    if payload.get("type") == "view_submission":
        # This runs when someone submits the modal.
        view = payload["view"]
        values = view["state"]["values"]
        review_context = json.loads(view["private_metadata"])
        sales_owner = values[SALES_OWNER_BLOCK_ID][SALES_OWNER_ACTION_ID].get("selected_user")
        sales_owner_email = get_sales_owner_email(sales_owner)

        # Build the Marketo update payload using the API field names defined at the top of the file.
        marketo_lead_data = {
            "id": review_context["marketo_id"],
            MARKETO_FIELD_NAMES["status"]: values[STATUS_BLOCK_ID][STATUS_ACTION_ID]["selected_option"]["value"],
            MARKETO_FIELD_NAMES["status_reason"]: values[STATUS_REASON_BLOCK_ID][STATUS_REASON_ACTION_ID]["value"],
            MARKETO_FIELD_NAMES["owner_email"]: sales_owner_email,
        }

        marketo_response = update_lead(marketo_lead_data)

        # Add a check mark to the original Slack message so the team can see it was handled.
        try:
            add_reaction(
                SLACK_BOT_TOKEN,
                review_context["channel_id"],
                review_context["message_ts"],
                "white_check_mark",
            )
        except SlackApiError as exc:
            # If the message already has the check mark, we do not want the whole submission to fail.
            if str(exc) != "already_reacted":
                raise

        print("Review submitted")
        print(f"marketo_id={review_context['marketo_id']}")
        print(f"sales_owner={sales_owner}")
        print(f"sales_owner_email={sales_owner_email}")
        print(json.dumps(marketo_response))
        return jsonify({"response_action": "clear"})

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), debug=True)
