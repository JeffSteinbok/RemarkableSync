"""
GitHub OAuth Device Code Flow for obtaining a GitHub token.

Used by RemarkableSync to authenticate with GitHub Models for AI OCR.
No client secret is needed — only the public Client ID.
"""

import time
from typing import Optional, Tuple

import requests

# OAuth App Client ID for RemarkableSync (device flow — no secret needed)
CLIENT_ID = "Ov23linXELxwaOh05sch"

DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"
# GitHub Models access is granted by the token itself (no special scope needed).
# We request no scopes — the OAuth token works for Models inference.
SCOPE = ""


def request_device_code() -> dict:
    """Request a device code and user code from GitHub.

    Returns:
        dict with keys: device_code, user_code, verification_uri, expires_in, interval
    """
    resp = requests.post(
        DEVICE_CODE_URL,
        data={"client_id": CLIENT_ID, "scope": SCOPE},
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    return resp.json()


def poll_for_token(device_code: str, interval: int = 5, expires_in: int = 900) -> Tuple[Optional[str], Optional[str]]:
    """Poll GitHub until the user authorizes or the code expires.

    Args:
        device_code: The device_code from the initial request.
        interval: Polling interval in seconds.
        expires_in: Maximum time to wait before giving up.

    Returns:
        Tuple of (access_token, error_message). One will be None.
    """
    start = time.time()
    while True:
        time.sleep(interval)

        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
        )
        data = resp.json()

        if "access_token" in data:
            return data["access_token"], None

        error = data.get("error", "")
        if error == "authorization_pending":
            pass  # Still waiting
        elif error == "slow_down":
            interval += 5
        elif error == "expired_token":
            return None, "Device code expired. Please try again."
        elif error == "access_denied":
            return None, "Authorization was denied by the user."
        else:
            return None, f"Unexpected error: {error} - {data.get('error_description', '')}"

        if time.time() - start > expires_in:
            return None, "Timed out waiting for authorization."


def device_flow_authenticate(on_code_received=None) -> Tuple[Optional[str], Optional[str]]:
    """Run the full device code flow.

    Args:
        on_code_received: Optional callback(verification_uri, user_code)
            called when the user code is ready to display.

    Returns:
        Tuple of (access_token, error_message). One will be None.
    """
    data = request_device_code()

    if on_code_received:
        on_code_received(data["verification_uri"], data["user_code"])

    device_code = data["device_code"]
    interval = data.get("interval", 5)
    expires_in = data.get("expires_in", 900)

    return poll_for_token(device_code, interval, expires_in)
