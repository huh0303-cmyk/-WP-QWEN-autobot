"""Update the live control-room YouTube audit without uploading or publishing."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(os.environ.get("KOREA365_ROOT", "/opt/korea365"))
SOURCE = ROOT / "control_center" / "channel_check.py"
AUDIT = ROOT / "data" / "operations-channel-audit.json"

ACTUAL_NAMES = {
    "UCbJfEtsffpgI5MsKkB7BYvQ": "CAFE_ROMANTIC",
    "UC7yEsLM-HoXudngrD-4FIqg": "CAFE_HEALING",
    "UC_e-sbLkVgwJNYEeobolNog": "CAFE_STARBUCKSVIBES",
    "UC7jOhyMa-FIrzZuea97z1Pw": "CAFE_MOZART",
    "UCKZsfAWyCmY0jckf4IWZrqw": "CAFE_KPOP",
    "UCtNLZO07Oh3UnXPI2CjOgNg": "NASA_XFILES",
    "UCVBvZwodUF4s57KeNicxQ3w": "HISTORY_TV_TODAY",
    "UCgNj-yS93A_fOHXXvG49fww": "INVENTION_STORY1",
    "UCLvy6kSpC8-7o3hnSrfQ47g": "SILENT_ERA_FILM",
    "UCwh49EokdWFJqYFE_zA6XDQ": "RETRO_USA1",
}

OAUTH_OK = {
    "UCbJfEtsffpgI5MsKkB7BYvQ",
    "UC7yEsLM-HoXudngrD-4FIqg",
}


def update_source() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    if "oauth_ok=c.get('oauth_ok'" in text and "public_count=sum(1 for c in d.get('youtube',[])" in text:
        return
    text, count_ok = re.subn(
        r"(?m)^(\s*)ok=c\.get\('status'\)=='채널 일치 · 읽기 확인'\s*$",
        r"\1oauth_ok=c.get('oauth_ok',c.get('status')=='채널 일치 · 읽기 확인')",
        text,
        count=1,
    )
    text, count_next = re.subn(
        r"ok=ok,(.*?)next='완성본·권리 검수 후 비공개 업로드 시험' if ok else '채널 신원 조회 권한 보완 후 대상 계정 재확인'",
        r"ok=oauth_ok,\1next='완성본·권리 검수 후 비공개 업로드 시험' if oauth_ok else 'OAuth 읽기 범위 재승인 필요 · 자동 공개 안 함'",
        text,
        count=1,
    )
    note_replacement = """   public_count=sum(1 for c in d.get('youtube',[]) if c.get('public_ok'))
   oauth_count=sum(1 for c in d.get('youtube',[]) if c.get('oauth_ok'))
   note=f'10개 채널 공개 조회: {public_count}개 존재·실제명 확인. OAuth 신원 조회: {oauth_count}개 정상, {len(d.get("youtube",[]))-oauth_count}개 읽기 범위 재승인 필요. 업로드·공개는 수행하지 않았습니다.'"""
    text, count_note = re.subn(
        r"(?m)^\s*note='10개 채널 읽기 검사:.*$",
        note_replacement,
        text,
        count=1,
    )
    if (count_ok, count_next, count_note) != (1, 1, 1):
        raise RuntimeError(f"Expected edits not found: ok={count_ok}, next={count_next}, note={count_note}")
    SOURCE.write_text(text, encoding="utf-8")


def update_audit() -> None:
    data = json.loads(AUDIT.read_text(encoding="utf-8"))
    records = data.get("youtube", [])
    found = {record.get("channel_id") for record in records}
    if found != set(ACTUAL_NAMES):
        raise RuntimeError("Live YouTube channel set differs from the approved ten-channel set")
    for record in records:
        channel_id = record["channel_id"]
        oauth_ok = channel_id in OAUTH_OK
        record.update(
            actual_name=ACTUAL_NAMES[channel_id],
            public_ok=True,
            oauth_ok=oauth_ok,
            status=(
                "채널 일치 · OAuth 읽기 확인"
                if oauth_ok
                else "공개 채널 확인 · OAuth 읽기 범위 부족"
            ),
        )
        if oauth_ok:
            record.pop("oauth_error", None)
        else:
            record["oauth_error"] = "ACCESS_TOKEN_SCOPE_INSUFFICIENT"
    data["checked_at"] = datetime.now(timezone.utc).isoformat()
    data["scope"] = "Public YouTube channel identity plus OAuth read-scope check; no upload or publication"
    AUDIT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    update_source()
    update_audit()
