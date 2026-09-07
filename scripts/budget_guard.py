#!/usr/bin/env python3
"""Hard monthly spend ceiling for paid AI API calls across this repo.

This is not a per-call cap (those already exist per-provider, e.g.
replicate_image_provider.py's 1-image/1-attempt limits) - it's a
cumulative circuit breaker. Every script that is about to call a paid
API (Gemini/GPT/Claude text, Replicate image, future YouTube/SNS
generation) must call `check_and_record()` first with its own rough
cost estimate. If the running total for the current calendar month
would exceed the configured ceiling, this raises and the caller must
stop - no API call happens. This protects against the failure mode
that actually costs money: a stuck retry loop, an accidentally
duplicated scheduler run, or a bulk trigger - not the average per-item
cost, which the per-call caps already handle.

State lives in budget_state.json at the repo root, committed back by
CI the same way blogger_scheduler_state.json already is.
"""
from __future__ import annotations

import base64
import hashlib
import math
import random
import time

import requests

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))
STATE_FILE = Path(__file__).resolve().parents[1] / "budget_state.json"

# Total monthly ceiling across every paid pipeline (WP+Blogspot writing,
# YouTube, SNS, everything). Deliberately conservative; raise only with
# an explicit decision, never silently.
DEFAULT_CEILING_USD = float(os.environ.get("BUDGET_MONTHLY_CEILING_USD", "").strip() or "80")


def _month_key(now: datetime) -> str:
    return now.strftime("%Y-%m")


def _load_state(now: datetime) -> dict:
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if state.get("month") == _month_key(now):
                return state
        except (OSError, ValueError):
            pass
    return {"month": _month_key(now), "spent_estimate_usd": 0.0, "calls": []}


def check_and_record(amount_usd: float, *, label: str, ceiling_usd: float = DEFAULT_CEILING_USD) -> None:
    """Raise SystemExit and record nothing if this call would breach the
    monthly ceiling. Otherwise record it and return normally."""
    if not math.isfinite(amount_usd) or amount_usd < 0:
        raise ValueError("Budget amount must be finite and nonnegative")
    if os.getenv("BUDGET_GITHUB_REPOSITORY"):
        _reserve_remote(amount_usd, label=label, ceiling_usd=ceiling_usd)
        return
    now = datetime.now(KST)
    state = _load_state(now)
    projected = state["spent_estimate_usd"] + amount_usd
    if projected > ceiling_usd:
        raise SystemExit(
            f"BUDGET GUARD BLOCKED: {label} (${amount_usd:.4f}) would bring this month's "
            f"estimated spend to ${projected:.2f}, over the ${ceiling_usd:.2f} ceiling "
            f"(already at ${state['spent_estimate_usd']:.2f}). No API call made. "
            f"Raise BUDGET_MONTHLY_CEILING_USD deliberately if this is expected, "
            f"or investigate why spend is higher than planned before retrying."
        )
    state["spent_estimate_usd"] = round(projected, 4)
    state["calls"].append({"at": now.isoformat(), "label": label, "amount_usd": amount_usd})
    state["calls"] = state["calls"][-500:]  # keep the file bounded
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"budget guard OK: {label} +${amount_usd:.4f} -> month total ${state['spent_estimate_usd']:.2f} / ${ceiling_usd:.2f}")



def _reserve_remote(amount_usd: float, *, label: str, ceiling_usd: float) -> None:
    """Reserve estimated spend before generation using GitHub's SHA compare-and-swap.

    A conflicting writer is re-read and merged before retrying. Failure to save
    blocks paid calls; reservation amounts are estimates, never measured charges.
    """
    repository = os.environ["BUDGET_GITHUB_REPOSITORY"]
    token = os.getenv("GH_TOKEN", "")
    if not token:
        raise RuntimeError("Budget reservation requires GH_TOKEN")
    branch = os.getenv("BUDGET_GITHUB_BRANCH", "main")
    run = os.getenv("GITHUB_RUN_ID", "")
    attempt = os.getenv("GITHUB_RUN_ATTEMPT", "1")
    if not run:
        raise RuntimeError("Budget reservation requires GITHUB_RUN_ID")
    operation = hashlib.sha256(f"{run}:{attempt}:{label}".encode()).hexdigest()
    url = f"https://api.github.com/repos/{repository}/contents/budget_state.json"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    for retry in range(12):
        response = requests.get(url, headers=headers, params={"ref": branch}, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"Budget read failed: HTTP {response.status_code}; paid calls blocked")
        data = response.json()
        state = json.loads(base64.b64decode(data["content"]))
        now = datetime.now(KST)
        if state.get("month") != _month_key(now):
            state = {"month": _month_key(now), "spent_estimate_usd": 0.0, "calls": []}
        if any(call.get("reservation_id") == operation for call in state["calls"]):
            raise RuntimeError("Budget reservation already exists for this execution; refusing a second paid attempt")
        projected = round(float(state["spent_estimate_usd"]) + amount_usd, 4)
        if not math.isfinite(projected) or projected > ceiling_usd:
            raise SystemExit("BUDGET GUARD BLOCKED: monthly estimated ceiling would be exceeded; no API call made")
        state["spent_estimate_usd"] = projected
        state["calls"].append({"at": now.isoformat(), "label": label, "amount_usd": amount_usd,
            "reservation_id": operation, "run_id": run, "run_attempt": attempt, "cost_type": "estimate"})
        encoded = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        response = requests.put(url, headers=headers, json={"message": "chore: reserve generation budget [skip ci]",
            "branch": branch, "sha": data["sha"], "content": base64.b64encode(encoded.encode()).decode()}, timeout=30)
        if response.status_code in {200, 201}:
            STATE_FILE.write_text(encoded, encoding="utf-8")
            print(f"budget guard reserved estimate: {label} +${amount_usd:.4f}; month ${projected:.2f}")
            return
        if response.status_code not in {409, 422}:
            raise RuntimeError(f"Budget save failed: HTTP {response.status_code}; paid calls blocked")
        time.sleep(min(retry + 1, 5) + random.random())
    raise RuntimeError("Budget reservation contention exhausted retries; no paid API call made")


def month_status(ceiling_usd: float = DEFAULT_CEILING_USD) -> dict:
    now = datetime.now(KST)
    state = _load_state(now)
    return {"month": state["month"], "spent_estimate_usd": state["spent_estimate_usd"],
            "ceiling_usd": ceiling_usd, "remaining_usd": round(ceiling_usd - state["spent_estimate_usd"], 4)}


if __name__ == "__main__":
    import sys
    print(json.dumps(month_status(), ensure_ascii=False, indent=2))
    sys.exit(0)
