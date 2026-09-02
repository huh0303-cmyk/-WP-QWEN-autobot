#!/usr/bin/env python3
"""Dispatch the 25 regular WordPress sites in a fixed, public sequence.

The two newsrooms are intentionally excluded: newsrooms-daily-publisher.yml owns
their independent 3-10 posts/day RSS schedule.
"""
import os
import sys
import time

import requests


A_GROUP_SITES = [
    "https://k-health365.com",
    "https://koreamedicaltour.com",
    "https://koreainvest365.com",
    "https://ki-korea.com",
    "https://koreainsurance365.com",
    "https://kfinance365.com",
    "https://koreataxnlaw.com",
    "https://koreacrypto365.com",
    "https://krealestate365.com",
    "https://ktech365.com",
    "https://kskin365.com",
    "https://oliveyoungkorea.com",
    "https://kworld365.com",
    "https://k-trip365.com",
    "https://k-visa365.com",
    "https://koreawedding365.com",
    "https://kstudy365.com",
    "https://studyinkorea365.com",
    "https://kieca-korea.org",
    "https://ksa-korea.org",
    "https://sis-korea.com",
    "https://jobkorea365.com",
    "https://jobinkorea365.com",
    "https://jobkoreaglobal.com",
    "https://korea365.org",
]

API = "https://api.github.com"


def dispatch(repo, token, workflow, inputs):
    response = requests.post(
        f"{API}/repos/{repo}/actions/workflows/{workflow}/dispatches",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"ref": "main", "inputs": inputs},
        timeout=30,
    )
    if response.status_code != 204:
        raise RuntimeError(f"dispatch {workflow} failed: HTTP {response.status_code} {response.text[:300]}")


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_DISPATCH_TOKEN"]
    index = int(os.environ.get("A_GROUP_INDEX", "0"))
    if not 0 <= index < len(A_GROUP_SITES):
        raise SystemExit(f"invalid A_GROUP_INDEX={index}")

    site = A_GROUP_SITES[index]
    print(f"A-group {index + 1}/{len(A_GROUP_SITES)}: dispatching {site}", flush=True)
    dispatch(repo, token, "daily-network-publish.yml", {
        "target_site_url": site,
        "publication_approved": "true",
        "room_id": f"wp25-{index + 1:02d}",
    })

    if index == len(A_GROUP_SITES) - 1:
        print("A-group sequence fully dispatched.", flush=True)
        return

    delay_minutes = int(os.environ.get("WP_SEQUENCE_DELAY_MINUTES", "5"))
    print(f"Next site will be dispatched in {delay_minutes} minutes.", flush=True)
    time.sleep(delay_minutes * 60)
    dispatch(repo, token, "a-group-sequential-publish.yml", {"index": str(index + 1)})
    print(f"Queued A-group index {index + 1}.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"::error title=A-group sequence failed::{type(exc).__name__}: {exc}")
        sys.exit(1)
