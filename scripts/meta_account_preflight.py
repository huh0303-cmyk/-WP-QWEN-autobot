from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config" / "meta_five_account_daily_policy.json"


def load_policy():
    data = json.loads(POLICY.read_text(encoding="utf-8-sig"))
    if len(data.get("accounts", [])) != 5:
        raise ValueError("Policy must contain exactly five accounts")
    handles = [a["handle"] for a in data["accounts"]]
    keys = [a["key"] for a in data["accounts"]]
    if len(set(handles)) != 5 or len(set(keys)) != 5:
        raise ValueError("Account handles and keys must be unique")
    if data["platforms"] != ["instagram", "threads"]:
        raise ValueError("Unexpected platform scope")
    return data


def verify_identity(platform: str, token: str) -> dict:
    if platform == "instagram":
        endpoint = "https://graph.instagram.com/v25.0/me"
        fields = "user_id,username"
    elif platform == "threads":
        endpoint = "https://graph.threads.net/v1.0/me"
        fields = "id,username"
    else:
        return {"status": "UNSUPPORTED_PLATFORM"}

    query = urlencode({"fields": fields, "access_token": token})
    request = Request(
        endpoint + "?" + query,
        headers={"User-Agent": "LondonProject-Meta-Preflight/1.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
            http_status = getattr(response, "status", 200)
    except HTTPError as exc:
        category = (
            "INVALID_OR_EXPIRED_TOKEN"
            if exc.code in (400, 401)
            else "MISSING_PERMISSION_OR_TESTER_ACCESS"
            if exc.code == 403
            else "META_API_ERROR"
        )
        return {
            "status": category,
            "http_status": exc.code,
            "error_type": "HTTPError",
        }
    except URLError as exc:
        return {
            "status": "NETWORK_ERROR",
            "error_type": type(exc.reason).__name__,
        }
    except Exception as exc:
        return {
            "status": "API_RESPONSE_ERROR",
            "error_type": type(exc).__name__,
        }

    if not isinstance(payload, dict):
        return {"status": "INVALID_API_RESPONSE", "http_status": http_status}

    user_id = str(payload.get("user_id") or payload.get("id") or "").strip()
    username = str(payload.get("username") or "").strip().lstrip("@")
    if not user_id or not username:
        return {
            "status": "IDENTITY_FIELDS_MISSING",
            "http_status": http_status,
        }
    return {
        "status": "IDENTITY_RESPONSE_OK",
        "http_status": http_status,
        "resolved_user_id": user_id,
        "resolved_username": username,
    }


def readiness(data):
    rows, missing = [], []
    for platform in data["platforms"]:
        for account in data["accounts"]:
            prefix = f"META_{platform.upper()}_{account['key'].upper()}"
            token_name = prefix + "_ACCESS_TOKEN"
            user_id_name = prefix + "_USER_ID"
            token = os.getenv(token_name, "").strip()
            configured_user_id = os.getenv(user_id_name, "").strip()

            row = {
                "platform": platform,
                "handle": account["handle"],
                "token_env_name": token_name,
                "token_present": bool(token),
                "configured_user_id_present": configured_user_id.isdigit(),
                "publish_enabled": False,
                "publication_performed": False,
            }
            if not token:
                row["status"] = "MISSING_ACCESS_TOKEN"
                missing.append(token_name)
                rows.append(row)
                continue

            identity = verify_identity(platform, token)
            row.update(identity)
            resolved_id = str(identity.get("resolved_user_id") or "")
            resolved_handle = str(identity.get("resolved_username") or "")
            if identity.get("status") != "IDENTITY_RESPONSE_OK":
                row["status"] = identity.get("status", "IDENTITY_CHECK_FAILED")
            elif resolved_handle.casefold() != account["handle"].casefold():
                row["status"] = "HANDLE_MISMATCH"
            elif configured_user_id and configured_user_id != resolved_id:
                row["status"] = "USER_ID_MISMATCH"
            else:
                row["status"] = "IDENTITY_VERIFIED_WRITE_SCOPE_UNCONFIRMED"
            rows.append(row)

    verified = sum(
        row["status"] == "IDENTITY_VERIFIED_WRITE_SCOPE_UNCONFIRMED"
        for row in rows
    )
    return {
        "account_count": 5,
        "platform_count": 2,
        "expected_connections": 10,
        "identity_verified_connections": verified,
        "ready_connections": verified,
        "publish_enabled": False,
        "publication_performed": False,
        "write_scope_verified": False,
        "missing_secret_names": missing,
        "connections": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    data = load_policy()
    if args.self_test:
        assert [x["handle"] for x in data["accounts"]] == [
            "seoul_topik",
            "seoul_jisoo",
            "seoul_chris",
            "english_pick1",
            "japanese_pick",
        ]
        assert data["authentication"]["publish_enabled"] is False
        print("SELF_TEST=PASS; exact five handles; no publishing")
        return 0

    result = readiness(data)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    print(
        "STATUS=IDENTITY_VERIFIED_BUT_PUBLISHING_REMAINS_DISABLED"
        if result["ready_connections"] == 10
        else "STATUS=BLOCKED_AUTH; no publishing attempted"
    )
    if args.report_path:
        report_path = Path(args.report_path)
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(rendered + "\n", encoding="utf-8")
        print("SANITIZED_REPORT_WRITTEN=" + str(report_path.relative_to(ROOT)))

    return 0 if result["ready_connections"] == 10 else 1


if __name__ == "__main__":
    raise SystemExit(main())
