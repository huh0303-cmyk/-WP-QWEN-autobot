from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "content_writing_policy.json"


@dataclass(frozen=True)
class WriterDecision:
    provider: str
    role: str
    reason: str
    status: str = "OK"


def load_policy(path: Path | str = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def choose_writer(
    *,
    quality_fail: bool = False,
    important_content: bool = False,
    high_value_content: bool = False,
    manual_override: bool = False,
    primary_available: bool = True,
    freshness_sensitive: bool = False,
    official_source_verified: bool = True,
    policy: dict[str, Any] | None = None,
) -> WriterDecision:
    """Route article generation under the locked two-model policy.

    GPT-5 mini is the routine writer. Gemini is the independent reviewer;
    Claude is excluded from automatic blog writing and review.
    """
    policy = policy or load_policy()

    if freshness_sensitive and not official_source_verified:
        return WriterDecision(
            provider="none",
            role="blocked",
            reason="official_source_verification_required",
            status=policy["freshness_sensitive_content"]["on_missing_verification"],
        )

    fallback_triggered = quality_fail or important_content or high_value_content or manual_override
    if fallback_triggered:
        return WriterDecision(
            provider=policy["fallback_writer"]["provider"],
            role=policy["fallback_writer"]["role"],
            reason="explicit_rewrite_signal",
        )

    if not primary_available:
        return WriterDecision(
            provider="none",
            role="blocked",
            reason="primary_writer_unavailable",
            status="AWAITING_APPROVAL",
        )

    return WriterDecision(
        provider=policy["primary_writer"]["provider"],
        role=policy["primary_writer"]["role"],
        reason="network_default_writer",
    )


def review_role(policy: dict[str, Any] | None = None) -> str:
    policy = policy or load_policy()
    return policy["auditor"]["role"]
