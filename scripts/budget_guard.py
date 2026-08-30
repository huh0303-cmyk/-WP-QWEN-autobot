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

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))
STATE_FILE = Path(__file__).resolve().parents[1] / "budget_state.json"

# Total monthly ceiling across every paid pipeline (WP+Blogspot writing,
# YouTube, SNS, everything). Deliberately conservative; raise only with
# an explicit decision, never silently.
DEFAULT_CEILING_USD = float(os.environ.get("BUDGET_MONTHLY_CEILING_USD", "80"))


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


def month_status(ceiling_usd: float = DEFAULT_CEILING_USD) -> dict:
    now = datetime.now(KST)
    state = _load_state(now)
    return {"month": state["month"], "spent_estimate_usd": state["spent_estimate_usd"],
            "ceiling_usd": ceiling_usd, "remaining_usd": round(ceiling_usd - state["spent_estimate_usd"], 4)}


if __name__ == "__main__":
    import sys
    print(json.dumps(month_status(), ensure_ascii=False, indent=2))
    sys.exit(0)
