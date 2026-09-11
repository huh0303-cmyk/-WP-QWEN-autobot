from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOMS_PATH = ROOT / "config" / "automation_rooms.json"
DEFAULT_PORTFOLIO_PATH = ROOT / "config" / "tistory_portfolio.json"

CANONICAL_TISTORY_REGISTRY = {
    "tistory_insurance_lab": "https://k-insight-vietnam.tistory.com/",
    "tistory_finance_housing": "https://k-vietnam.tistory.com/",
    "tistory_health_info": "https://k-healthcare.tistory.com/",
    "tistory_life365": "https://huh0303.tistory.com/",
    "tistory_ktrip365": "https://k-trip365.tistory.com/",
}

CANONICAL_DAILY_WINDOWS = {
    "tistory_finance_housing": (7, 9),
    "tistory_insurance_lab": (10, 12),
    "tistory_health_info": (13, 15),
    "tistory_life365": (16, 18),
    "tistory_ktrip365": (19, 21),
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _records(payload: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        value = payload.get(key, [])
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _first(record: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record:
            return record[key]
    return None


def _normalized_url(value: Any) -> str:
    text = str(value or "").strip()
    return f"{text.rstrip('/')}/" if text else ""


def _site_id(record: Mapping[str, Any]) -> str:
    return str(_first(record, "site_id", "room_id", "id") or "").strip()


def _site_url(record: Mapping[str, Any]) -> str:
    return _normalized_url(
        _first(
            record,
            "destination_url",
            "destination_id",
            "base_url",
            "blog_url",
            "site_url",
            "url",
            "destination",
        )
    )


def _registry(records: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for record in records:
        site_id = _site_id(record)
        platform = str(record.get("platform", "")).strip().lower()
        if platform == "tistory" or site_id.startswith("tistory_"):
            result[site_id] = _site_url(record)
    return result


def _window(record: Mapping[str, Any]) -> tuple[int, int] | None:
    value = _first(record, "daily_window", "schedule_window", "publish_window", "window")
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return int(value[0]), int(value[1])
    if isinstance(value, dict):
        start = _first(value, "start_hour", "start", "from")
        end = _first(value, "end_hour", "end", "to")
        if start is not None and end is not None:
            return int(str(start).split(":", 1)[0]), int(str(end).split(":", 1)[0])
    if isinstance(value, str):
        hours = re.findall(r"(?:^|\D)([01]?\d|2[0-3])(?::\d\d)?", value)
        if len(hours) >= 2:
            return int(hours[0]), int(hours[1])
    start = _first(record, "window_start_hour", "start_hour")
    end = _first(record, "window_end_hour", "end_hour")
    if start is not None and end is not None:
        return int(start), int(end)
    return None


def _profile_dir(env: Mapping[str, str], explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    configured = env.get("TISTORY_PROFILE_DIR") or env.get("TISTORY_USER_DATA_DIR")
    return Path(configured) if configured else ROOT / "artifacts" / "tistory-profile"


def _profile_cookie_store(profile_dir: Path) -> Path | None:
    candidates = (
        profile_dir / "Default" / "Network" / "Cookies",
        profile_dir / "Default" / "Cookies",
        profile_dir / "Network" / "Cookies",
    )
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def _check(status: str, **details: Any) -> dict[str, Any]:
    return {"status": status, **details}


def build_readiness_report(
    *,
    env: Mapping[str, str] | None = None,
    rooms_path: Path = DEFAULT_ROOMS_PATH,
    portfolio_path: Path = DEFAULT_PORTFOLIO_PATH,
    profile_dir: Path | None = None,
) -> dict[str, Any]:
    runtime_env = dict(os.environ if env is None else env)
    rooms_payload = _load_json(rooms_path)
    portfolio_payload = _load_json(portfolio_path)
    rooms = _records(rooms_payload, "rooms")
    sites = _records(portfolio_payload, "sites")

    room_registry = _registry(rooms)
    portfolio_registry = _registry(sites)
    registry_ok = (
        room_registry == CANONICAL_TISTORY_REGISTRY
        and portfolio_registry == CANONICAL_TISTORY_REGISTRY
    )

    tistory_rooms = [record for record in rooms if _site_id(record) in CANONICAL_TISTORY_REGISTRY]
    room_controls_ok = len(tistory_rooms) == 5 and all(
        record.get("enabled") is True
        and str(record.get("workflow", "")) == "tistory-daily-plan.yml"
        and str(record.get("publish_policy", "")) == "awaiting_approval"
        and record.get("duplicate_guard") is True
        for record in tistory_rooms
    )

    tistory_sites = [record for record in sites if _site_id(record) in CANONICAL_TISTORY_REGISTRY]
    configured_windows = {_site_id(record): _window(record) for record in tistory_sites}
    timezone = ""
    if isinstance(portfolio_payload, dict):
        timezone = str(
            portfolio_payload.get("timezone")
            or portfolio_payload.get("default_timezone")
            or ""
        )
    schedule_ok = configured_windows == CANONICAL_DAILY_WINDOWS and timezone == "Asia/Seoul"

    site_safety_ok = len(tistory_sites) == 5 and all(
        record.get("launch_enabled") is True
        and str(record.get("publish_policy", "awaiting_approval")) == "awaiting_approval"
        and record.get("duplicate_guard", True) is True
        for record in tistory_sites
    )

    admin_links = {
        site_id: f"{urlparse(url).scheme}://{urlparse(url).netloc}/manage/newpost/1?type=post"
        for site_id, url in CANONICAL_TISTORY_REGISTRY.items()
    }
    admin_links_ok = all(
        link.startswith("https://") and link.endswith("/manage/newpost/1?type=post")
        for link in admin_links.values()
    )

    selected_profile_dir = _profile_dir(runtime_env, profile_dir)
    cookie_store = _profile_cookie_store(selected_profile_dir)
    sheet_id_present = bool(runtime_env.get("SHEET_ID", "").strip())
    email_password_present = bool(runtime_env.get("GMAIL_APP_PASSWORD", "").strip())
    email_recipient = (
        runtime_env.get("REPORT_EMAIL_TO")
        or runtime_env.get("GMAIL_TO")
        or "huh0303@naver.com"
    ).strip()

    contract_checks = {
        "exact_registry": _check(
            "PASS" if registry_ok else "FAIL",
            expected=CANONICAL_TISTORY_REGISTRY,
            rooms=room_registry,
            portfolio=portfolio_registry,
        ),
        "sheet_schedule": _check(
            "PASS" if schedule_ok else "FAIL",
            timezone=timezone,
            windows={key: list(value) if value else None for key, value in configured_windows.items()},
        ),
        "duplicate_block": _check("PASS" if room_controls_ok and site_safety_ok else "FAIL"),
        "private_review": _check(
            "PASS" if room_controls_ok and site_safety_ok else "FAIL",
            publish_policy="awaiting_approval",
            public_allowed=False,
        ),
        "admin_links": _check("PASS" if admin_links_ok else "FAIL", examples=admin_links),
    }
    contract_pass = all(check["status"] == "PASS" for check in contract_checks.values())

    runtime_checks = {
        "tistory_auth": _check(
            "READY" if cookie_store else "ACTION_REQUIRED",
            profile_dir=str(selected_profile_dir),
            cookie_store_present=bool(cookie_store),
        ),
        "sheet": _check(
            "READY" if sheet_id_present else "ACTION_REQUIRED",
            sheet_id_present=sheet_id_present,
        ),
        "email": _check(
            "READY" if email_password_present and bool(email_recipient) else "ACTION_REQUIRED",
            gmail_app_password_present=email_password_present,
            recipient=email_recipient,
        ),
    }
    runtime_ready = all(check["status"] == "READY" for check in runtime_checks.values())

    return {
        "status": "PASS" if contract_pass else "FAIL",
        "runtime_ready": runtime_ready,
        "site_count": len(CANONICAL_TISTORY_REGISTRY),
        "contract_checks": contract_checks,
        "runtime_checks": runtime_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Tistory 5 contracts and runtime readiness.")
    parser.add_argument("--rooms", type=Path, default=DEFAULT_ROOMS_PATH)
    parser.add_argument("--portfolio", type=Path, default=DEFAULT_PORTFOLIO_PATH)
    parser.add_argument("--profile-dir", type=Path)
    parser.add_argument("--require-runtime", action="store_true")
    args = parser.parse_args()

    report = build_readiness_report(
        rooms_path=args.rooms,
        portfolio_path=args.portfolio,
        profile_dir=args.profile_dir,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "PASS":
        return 1
    if args.require_runtime and not report["runtime_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
