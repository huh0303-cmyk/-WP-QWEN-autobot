"""Read-only YouTube OAuth diagnostic with safe error details."""
import json
import os
import requests


def main():
    profile = os.environ["PROFILE"]
    fields = {key: os.environ.get(key, "") for key in ("CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN")}
    if not all(fields.values()):
        raise RuntimeError(f"{profile}: missing credential configuration")

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": fields["CLIENT_ID"],
            "client_secret": fields["CLIENT_SECRET"],
            "refresh_token": fields["REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if not token_response.ok:
        raise RuntimeError(f"{profile}: refresh rejected: {token_response.json().get('error', token_response.status_code)}")

    token_data = token_response.json()
    response = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "id,snippet", "mine": "true"},
        headers={"Authorization": "Bearer " + token_data["access_token"]},
        timeout=30,
    )
    if not response.ok:
        try:
            detail = response.json().get("error", {})
        except ValueError:
            detail = {"code": response.status_code, "message": response.text[:500]}
        # The response contains API/project diagnostics, not credential values.
        raise RuntimeError(f"{profile}: channel verification rejected: {json.dumps(detail, ensure_ascii=False)}")

    print(f"{profile}: channel lookup succeeded")


if __name__ == "__main__":
    main()
