import json
import os

import dotenv
import requests


dotenv.load_dotenv()

# These values come from `.env` and are used for every Marketo API call.
BASE_URL = os.environ["MARKETO_BASE_URL"].rstrip("/")
CLIENT_ID = os.environ["MARKETO_CLIENT_ID"]
CLIENT_SECRET = os.environ["MARKETO_CLIENT_SECRET"]


class MarketoApiError(RuntimeError):
    pass


def get_access_token():
    # Marketo uses a short-lived access token. We request a fresh one each time.
    response = requests.get(
        f"{BASE_URL}/identity/oauth/token",
        params={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=30,
    )
    data = response.json()
    return data["access_token"]


def update_lead(lead_data):
    # This function updates one Marketo lead using a dictionary of API field names and values.
    # Example:
    # {"id": "1625", "leadStatus": "SAL", "leadStatusReason": "Good fit"}
    lead_data = dict(lead_data)
    lead_data["id"] = int(lead_data["id"])

    response = requests.post(
        f"{BASE_URL}/rest/v1/leads.json",
        headers={"Authorization": f"Bearer {get_access_token()}"},
        json={
            "action": "updateOnly",
            "lookupField": "id",
            "input": [lead_data],
        },
        timeout=30,
    )
    data = response.json()

    if not data.get("success"):
        raise MarketoApiError(json.dumps(data))

    return data
