"""Read-only exact-channel OAuth check for the two Health Clinic channels."""
import os

import requests


def main() -> None:
    expected = os.environ["EXPECTED_CHANNEL_ID"]
    profile = os.environ["PROFILE"]
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
        "refresh_token": os.environ["REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    if not response.ok:
        raise RuntimeError(f"{profile}: refresh rejected HTTP {response.status_code}")
    data = response.json()
    scopes = set(data.get("scope", "").split())
    write_scopes = {
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    }
    if not scopes.intersection(write_scopes):
        raise RuntimeError(f"{profile}: token lacks YouTube write scope")
    check = requests.get("https://www.googleapis.com/youtube/v3/channels",
        params={"part": "id", "mine": "true"},
        headers={"Authorization": f"Bearer {data['access_token']}"}, timeout=30)
    if not check.ok:
        raise RuntimeError(f"{profile}: channel verification HTTP {check.status_code}")
    found = {item["id"] for item in check.json().get("items", [])}
    if expected not in found:
        raise RuntimeError(f"{profile}: authenticated channel does not match locked UC ID")
    print(f"{profile}: exact channel ID and write scope verified (read only)")


if __name__ == "__main__":
    main()
