#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urljoin

import requests


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "automation_hub_sites.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "huh0303-cmyk/-WP-QWEN-autobot")
USER = os.environ.get("WP_USER", "huh0303@gmail.com")
REAL_PASSWORD = os.environ.get("WP_REAL_PASSWORD", "").strip()
ADMIN_PASSWORD = os.environ.get("WP_ADMIN_PASSWORD", "").strip()
GH_TOKEN = os.environ.get("GH_PAT", "").strip()
MODE = os.environ.get("BOOTSTRAP_MODE", "canary").strip().lower()
TARGET_SECRET_NAMES = {name.strip() for name in os.environ.get("TARGET_SECRET_NAMES", "").split(",") if name.strip()}
RESULT_PATH = ROOT / "wp_auth_bootstrap_result.json"


def wp_sites() -> list[dict]:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return [row for row in payload.get("sites", []) if row.get("platform") == "wordpress"]


def registered_secret_names() -> set[str]:
    env = os.environ.copy()
    env["GH_TOKEN"] = GH_TOKEN
    proc = subprocess.run(
        ["gh", "secret", "list", "--repo", REPO, "--json", "name"],
        capture_output=True, text=True, env=env, check=True,
    )
    return {row["name"] for row in json.loads(proc.stdout)}


def find_nonce(html: str) -> str:
    patterns = (
        r'wpApiSettings\s*=\s*\{[^;]*?"nonce"\s*:\s*"([^"]+)"',
        r'createNonceMiddleware\(\s*"([^"]+)"\s*\)',
        r'"nonce"\s*:\s*"([a-zA-Z0-9]+)"',
    )
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.S)
        if match:
            return match.group(1)
    return ""


def create_application_password(site: dict) -> tuple[str, str]:
    base = site["url"].rstrip("/")
    login_url = f"{base}/wp-login.php"
    profile_url = f"{base}/wp-admin/profile.php"
    session = None
    for candidate in dict.fromkeys(password for password in (REAL_PASSWORD, ADMIN_PASSWORD) if password):
        attempt = requests.Session()
        attempt.headers.update({"User-Agent": "SIS-Control-Center-Auth/1.0"})
        attempt.get(login_url, timeout=30)
        login = attempt.post(
            login_url,
            data={
                "log": USER, "pwd": candidate, "rememberme": "forever",
                "wp-submit": "Log In", "redirect_to": profile_url, "testcookie": "1",
            },
            timeout=45, allow_redirects=True,
        )
        if "wp-login.php" not in login.url and "login_error" not in login.text:
            session = attempt
            break
    if session is None:
        raise RuntimeError("administrator_login_failed")
    profile = session.get(profile_url, timeout=30)
    if profile.status_code != 200 or "wp-login.php" in profile.url:
        raise RuntimeError(f"profile_access_failed_http_{profile.status_code}")
    nonce = find_nonce(profile.text)
    if not nonce:
        raise RuntimeError("rest_nonce_not_found")
    headers = {"X-WP-Nonce": nonce, "Content-Type": "application/json"}
    me = session.get(f"{base}/wp-json/wp/v2/users/me", headers=headers, params={"context": "edit"}, timeout=30)
    if me.status_code != 200:
        raise RuntimeError(f"rest_user_check_failed_http_{me.status_code}")
    user_id = int(me.json()["id"])
    app_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"sis-control-center:{base}"))
    created = session.post(
        f"{base}/wp-json/wp/v2/users/{user_id}/application-passwords",
        headers=headers,
        json={"name": "SIS Control Center", "app_id": app_id}, timeout=30,
    )
    if created.status_code == 409:
        session.delete(
            f"{base}/wp-json/wp/v2/users/{user_id}/application-passwords/introspect",
            headers=headers, timeout=30,
        )
        raise RuntimeError("application_password_name_conflict")
    if created.status_code not in {200, 201}:
        raise RuntimeError(f"application_password_create_failed_http_{created.status_code}")
    password = str(created.json().get("password", "")).strip()
    if not password:
        raise RuntimeError("application_password_missing_from_response")
    check = requests.get(
        f"{base}/wp-json/wp/v2/users/me", auth=(USER, password),
        params={"context": "edit"}, timeout=30,
    )
    if check.status_code != 200:
        raise RuntimeError(f"application_password_validation_failed_http_{check.status_code}")
    return password, str(user_id)


def store_secret(name: str, password: str) -> None:
    env = os.environ.copy()
    env["GH_TOKEN"] = GH_TOKEN
    subprocess.run(
        ["gh", "secret", "set", name, "--repo", REPO],
        input=password, text=True, env=env, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )


def main() -> int:
    if not (REAL_PASSWORD or ADMIN_PASSWORD) or not GH_TOKEN:
        raise SystemExit("required bootstrap credentials are unavailable")
    targets = [row for row in wp_sites() if row.get("secret_name") in TARGET_SECRET_NAMES]
    if not targets:
        raise SystemExit("no bootstrap target names were supplied")
    if MODE == "canary":
        targets = targets[:1]
    results = []
    for site in targets:
        item = {"domain": site["url"].replace("https://", "").replace("http://", ""), "secret": site["secret_name"]}
        try:
            password, user_id = create_application_password(site)
            store_secret(site["secret_name"], password)
            item.update({"status": "registered_and_validated", "user_id": user_id})
        except Exception as exc:
            item.update({"status": "failed", "error": str(exc)[:180]})
        results.append(item)
    RESULT_PATH.write_text(json.dumps({"mode": MODE, "targets": len(targets), "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"mode": MODE, "targets": len(targets), "succeeded": sum(r["status"] == "registered_and_validated" for r in results), "failed": sum(r["status"] == "failed" for r in results)}))
    return 1 if any(r["status"] == "failed" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
