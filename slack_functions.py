import requests


SLACK_API_BASE_URL = "https://slack.com/api"


class SlackApiError(RuntimeError):
    pass


def slack_get(token, method, params=None):
    # Use this for Slack API methods that expect values in the URL/query string.
    response = requests.get(
        f"{SLACK_API_BASE_URL}/{method}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    data = response.json()

    if not data.get("ok"):
        raise SlackApiError(data.get("error", "unknown_error"))

    return data


def slack_post(token, method, payload=None):
    # Use this for Slack API methods that accept JSON payloads.
    response = requests.post(
        f"{SLACK_API_BASE_URL}/{method}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload or {},
        timeout=30,
    )
    data = response.json()

    if not data.get("ok"):
        raise SlackApiError(data.get("error", "unknown_error"))

    return data


def send_message(token, channel, text=None, blocks=None):
    # Sends a message to Slack. `text` is the fallback/notification text.
    return slack_post(
        token,
        "chat.postMessage",
        {
            "channel": channel,
            "text": text,
            "blocks": blocks,
        },
    )


def open_modal(token, trigger_id, view):
    # Opens a Slack modal after a user clicks a button or other interactive element.
    return slack_post(
        token,
        "views.open",
        {
            "trigger_id": trigger_id,
            "view": view,
        },
    )


def add_reaction(token, channel, timestamp, name):
    # Adds an emoji reaction to an existing Slack message.
    return slack_post(
        token,
        "reactions.add",
        {
            "channel": channel,
            "timestamp": timestamp,
            "name": name,
        },
    )


def get_user_profile(token, user_id, include_labels=False):
    # Looks up a Slack user's profile so we can read fields like email.
    response = slack_get(
        token,
        "users.profile.get",
        {
            "user": user_id,
            "include_labels": include_labels,
        },
    )
    return response["profile"]
