from __future__ import annotations

import json
from pathlib import Path

from scripts.tistory_readiness import (
    CANONICAL_TISTORY_REGISTRY,
    DEFAULT_PORTFOLIO_PATH,
    DEFAULT_ROOMS_PATH,
    build_readiness_report,
)


def test_contract_and_runtime_readiness_pass(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    cookie_store = profile_dir / "Default" / "Network" / "Cookies"
    cookie_store.parent.mkdir(parents=True)
    cookie_store.write_bytes(b"sqlite-cookie-data")
    env = {
        "SHEET_ID": "sheet-id",
        "GMAIL_APP_PASSWORD": "must-not-leak",
        "REPORT_EMAIL_TO": "owner@example.com",
    }

    report = build_readiness_report(env=env, profile_dir=profile_dir)

    assert report["status"] == "PASS"
    assert report["runtime_ready"] is True
    assert report["site_count"] == 5
    assert all(item["status"] == "PASS" for item in report["contract_checks"].values())
    assert all(item["status"] == "READY" for item in report["runtime_checks"].values())
    assert "must-not-leak" not in json.dumps(report)


def test_missing_runtime_configuration_does_not_hide_contract_pass(tmp_path: Path) -> None:
    report = build_readiness_report(env={}, profile_dir=tmp_path / "missing-profile")

    assert report["status"] == "PASS"
    assert report["runtime_ready"] is False
    assert report["runtime_checks"]["tistory_auth"]["status"] == "ACTION_REQUIRED"
    assert report["runtime_checks"]["sheet"]["status"] == "ACTION_REQUIRED"
    assert report["runtime_checks"]["email"]["status"] == "ACTION_REQUIRED"


def test_registry_drift_fails_exact_contract(tmp_path: Path) -> None:
    rooms = json.loads(DEFAULT_ROOMS_PATH.read_text(encoding="utf-8"))
    records = rooms if isinstance(rooms, list) else rooms["rooms"]
    target = next(item for item in records if item.get("room_id") == "tistory_life365")
    for key in (
        "destination_url",
        "destination_id",
        "base_url",
        "blog_url",
        "site_url",
        "url",
        "destination",
    ):
        if key in target:
            target[key] = "https://wrong.example/"
            break
    altered_rooms = tmp_path / "automation_rooms.json"
    altered_rooms.write_text(json.dumps(rooms), encoding="utf-8")

    report = build_readiness_report(
        env={},
        rooms_path=altered_rooms,
        portfolio_path=DEFAULT_PORTFOLIO_PATH,
        profile_dir=tmp_path / "profile",
    )

    assert report["status"] == "FAIL"
    assert report["contract_checks"]["exact_registry"]["status"] == "FAIL"
    assert report["contract_checks"]["exact_registry"]["expected"] == CANONICAL_TISTORY_REGISTRY
