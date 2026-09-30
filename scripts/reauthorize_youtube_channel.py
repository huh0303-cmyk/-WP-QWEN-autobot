"""Interactive one-channel OAuth renewal with exact-ID check and secret storage.

Never prints a refresh token. Run one locked channel key at a time while the
owner selects the matching Google/brand account in the browser.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path

import requests
from google_auth_oauthlib.flow import InstalledAppFlow


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "config/YOUTUBE_23_CHANNEL_MASTER_LOCK_2026-09-27.json"
HOST = "root@187.127.121.57"
SSH_KEY = Path.home() / ".ssh" / "id_ed25519"
PROFILES = {
    "globalmusic": "GLOBALMUSIC", "healing": "HEALING",
    "starbucks": "STARBUCKS", "mbb": "MBB", "kpop": "KPOP",
    "nasa": "NASA_SPACE_TIMES", "history": "HISTORY_TODAY_TIMES",
    "invention": "INVENTION_TIMES", "silent_era": "SILENT_ERA_TIMES",
    "retro_reels": "RETRO_REELS_TIMES",
    "health_japan": "HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_JP",
    "health_usa": "HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_EN",
    "ko": "LANGUAGE_KO", "en": "LANGUAGE_EN",
    "ja": "LANGUAGE_JA", "zh": "LANGUAGE_ZH",
    "vi": "LANGUAGE_VI", "es": "LANGUAGE_ES",
    "fr": "LANGUAGE_FR", "de": "LANGUAGE_DE",
    "it": "LANGUAGE_IT", "pt": "LANGUAGE_PT",
    "shopping": "SHOPPING_SEOUL_JISOO1",
}


def _ssh(*args: str, input_text: str | None = None) -> str:
    result = subprocess.run(
        ["ssh", "-i", str(SSH_KEY), "-o", "BatchMode=yes", HOST,
         shlex.join(args)],
        input=input_text, text=True, capture_output=True, check=True,
    )
    return result.stdout


def _client() -> dict:
    code = (
        "import json;d=json.load(open('/etc/korea365/youtube-runtime.json'));"
        "print(json.dumps({'id':d['YOUTUBE_OAUTH_CLIENT_ID'],"
        "'secret':d['YOUTUBE_OAUTH_CLIENT_SECRET']}))"
    )
    return json.loads(_ssh("python3", "-c", code))


def _expected(key: str) -> tuple[str, str]:
    groups = json.loads(MASTER.read_text(encoding="utf-8"))["groups"]
    for entries in groups.values():
        for entry in entries:
            if entry["key"] == key:
                return entry["channel_id"], entry["title"]
    raise ValueError(f"unknown locked channel key: {key}")


def _require_exact_channel(items: list[dict], expected: str) -> None:
    found = {entry.get("id") for entry in items}
    if found != {expected}:
        raise RuntimeError(f"Wrong or ambiguous account/channel selected ({sorted(str(x) for x in found)}); nothing stored")


def _store_vps(name: str, token: str) -> None:
    code = (
        "import json,os,sys,shutil,datetime;from pathlib import Path;"
        "p=Path('/etc/korea365/youtube-runtime.json');"
        "backup=p.with_name(p.name+'.bak-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S'));"
        "shutil.copy2(p,backup);os.chmod(backup,0o600);"
        "d=json.loads(p.read_text());d[sys.argv[1]]=sys.stdin.read().strip();"
        "t=p.with_suffix('.tmp');t.write_text(json.dumps(d));os.chmod(t,0o600);os.replace(t,p)"
    )
    _ssh("python3", "-c", code, name, input_text=token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("channel", choices=sorted(PROFILES))
    args = parser.parse_args()
    expected, title = _expected(args.channel)
    client = _client()
    print(f"OAuth 승인 대상: {args.channel} / {title} / {expected}", flush=True)
    config = {"installed": {
        "client_id": client["id"], "client_secret": client["secret"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }}
    flow = InstalledAppFlow.from_client_config(
        config, scopes=["https://www.googleapis.com/auth/youtube"])
    creds = flow.run_local_server(port=0, open_browser=True,
                                  access_type="offline", prompt="consent")
    if not creds.refresh_token:
        raise RuntimeError("Google did not return a refresh token; nothing stored")
    response = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "id", "mine": "true"},
        headers={"Authorization": f"Bearer {creds.token}"}, timeout=30,
    )
    response.raise_for_status()
    _require_exact_channel(response.json().get("items", []), expected)
    profile = PROFILES[args.channel]
    secret_name = (profile if profile.startswith("HEALTH_CLINIC_")
                   else f"YOUTUBE_OAUTH_REFRESH_TOKEN_{profile}")
    _store_vps(secret_name, creds.refresh_token)
    subprocess.run(["gh", "secret", "set", secret_name], input=creds.refresh_token,
                   text=True, capture_output=True, check=True, cwd=ROOT)
    print(f"Verified {expected}; stored {secret_name} in approved secret stores", flush=True)


if __name__ == "__main__":
    main()
