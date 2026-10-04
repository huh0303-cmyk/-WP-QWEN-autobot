"""Read-only provider key check.

Every publisher (WordPress, Blogspot, newsrooms) writes with the same Gemini
key.  On 2026-09-29 that key was rejected ("API key not valid", HTTP 400) and
every article writer fell through its model list with a bare RuntimeError, so
the whole network failed together and each failure looked like a different bug.

This module answers one question before any article is claimed: is the key
usable?  It calls `models.list` (free, no generation) and classifies the result.
Only INVALID blocks publishing; quota and network trouble do not, because those
clear on their own and the publishers already retry them.
"""
from __future__ import annotations

import os
import sys

import requests

URL = "https://generativelanguage.googleapis.com/v1beta/models"

OK, INVALID, QUOTA, UNREACHABLE, MISSING = "OK", "INVALID", "QUOTA", "UNREACHABLE", "MISSING"
BLOCKING = {INVALID, MISSING}


def classify(status_code: int, body: str = "") -> str:
    text = (body or "").lower()
    if status_code == 200:
        return OK
    if status_code == 429:
        return QUOTA
    if status_code in {400, 401, 403} and ("api key" in text or "api_key" in text or "permission" in text
                                           or "disabled" in text or "expired" in text or status_code in {401, 403}):
        return INVALID
    return UNREACHABLE


def check_gemini(key: str | None, timeout: float = 15, session=requests) -> str:
    if not (key or "").strip():
        return MISSING
    try:
        # Key goes in a header, never the URL, so it cannot land in a request log.
        response = session.get(URL, params={"pageSize": 1}, headers={"x-goog-api-key": key.strip()}, timeout=timeout)
    except requests.RequestException:
        return UNREACHABLE
    return classify(response.status_code, response.text[:400])


MESSAGES = {
    OK: "Gemini key is valid.",
    QUOTA: "Gemini key is valid but rate/quota limited right now; publishers will retry.",
    UNREACHABLE: "Gemini could not be reached; not treated as a bad key.",
    INVALID: "Gemini key was REJECTED. Replace the GEMINI_API_KEY secret (GitHub) and /etc/korea365/article-runtime.json (VPS).",
    MISSING: "GEMINI_API_KEY is empty or not passed to this job.",
}


def main() -> int:
    state = check_gemini(os.environ.get("GEMINI_API_KEY"))
    print(f"gemini: {state} - {MESSAGES[state]}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"### Provider key check\n\n**gemini: {state}** - {MESSAGES[state]}\n")
    return 1 if state in BLOCKING else 0


if __name__ == "__main__":
    sys.exit(main())
