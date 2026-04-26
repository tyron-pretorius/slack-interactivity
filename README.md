# Slack Interactivity for RevOps

This repo contains simple Python scripts for sending Slack alerts, opening Slack modals, and updating Marketo after a user makes a decision in Slack.

The main use case today is:
- send an MQL alert into Slack
- let a user click `Review`
- open a modal to choose a status and optional owner
- update the lead in Marketo
- add a `white_check_mark` reaction to the Slack message

## Scripts

`send_slack_message.py`
- Sends a test Slack message using `message_template.json`
- Uses the Slack bot token from `.env`
- Good for testing the Slack message format and Review button

`send_marketo_webhook_payload.py`
- Sends a test Slack message using `marketo_webhook_payload.json`
- Simulates the type of payload you might send from Marketo or another webhook source

`slack_interactions_listener.py`
- Runs a small Flask web server
- Receives button clicks and modal submissions from Slack
- Opens the modal when someone clicks `Review`
- Updates the lead in Marketo when the modal is submitted
- Adds a `white_check_mark` reaction to the original Slack message after a successful update

`slack_functions.py`
- Small helper functions for calling the Slack API
- Used by the other scripts so the Slack logic stays in one place

`marketo_functions.py`
- Small helper functions for calling the Marketo API
- Gets an access token
- Updates a lead using a dictionary of Marketo field names and values

`test_slack_user_email.py`
- Tests a few Slack user lookup methods
- Useful for confirming the app can read a user's email address

`test_slack_users_info_email.py`
- Small focused test for `users.info`

## Template Files

`message_template.json`
- The Slack message template used by `send_slack_message.py`

`marketo_webhook_payload.json`
- The Slack message template used by `send_marketo_webhook_payload.py`

## Environment Variables

Create a `.env` file with:

```env
SLACK_BOT_TOKEN="xoxb-..."
SLACK_SIGNING_SECRET="..."
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/AAA/BBB/CCC"
MARKETO_CLIENT_ID="..."
MARKETO_CLIENT_SECRET="..."
MARKETO_BASE_URL="https://your-instance.mktorest.com/"
```

## Install

Create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the Listener

Start the Flask listener:

```bash
./.venv/bin/python slack_interactions_listener.py
```

By default it runs on port `8080`.

You can confirm it is alive by opening:

```text
http://localhost:8080/
```

It should return:

```text
ok
```

## Exposing the Listener with ngrok

Slack needs a public URL so it can send button clicks and modal submissions back to your local listener.

If your listener is running on port `8080`, start ngrok like this:

```bash
ngrok http 8080
```

ngrok will give you a public URL that looks something like:

```text
https://abc123.ngrok-free.app
```

## Slack App Setup

In your Slack app settings:

1. Open `Interactivity & Shortcuts`
2. Turn `Interactivity` on
3. Set the `Request URL` to:

```text
https://abc123.ngrok-free.app/slack/interactions
```

Replace the example domain with your real ngrok URL.

If you restart ngrok and the URL changes, you need to update the Slack app setting again.

## Slack Bot Scopes

The app should have the scopes needed for this workflow, including:

```text
chat:write
users:read
users:read.email
commands
reactions:write
```

If you add or change scopes, reinstall the app to the workspace.

## How the Flow Works

1. Send a message using `send_slack_message.py` or `send_marketo_webhook_payload.py`
2. A user clicks the `Review` button in Slack
3. Slack sends that interaction to `slack_interactions_listener.py`
4. The listener opens a modal
5. The user submits the modal
6. The listener updates Marketo
7. The listener adds a `white_check_mark` reaction to the original Slack message

## Notes

- The listener verifies the Slack request signature before doing anything
- The modal stores enough metadata to know which lead is being updated and which Slack message should get the reaction
- The top-level `text` field in Slack messages is fallback text for notifications and previews; the visible layout comes from the `blocks`
