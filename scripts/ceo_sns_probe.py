"""Read SNS statistics with existing secrets; never publish or send messages.

Produces a sanitized receipt for updating the CEO sheet. Partial collection is
explicitly marked; missing values and unverified deltas are never zero-filled.
"""
import json
import os
from datetime import datetime
from pathlib import Path

from social_stats_daily import (
    KST, get_tiktok_followers_multi, get_facebook_followers_multi,
    get_instagram_followers_multi, get_threads_followers_multi,
)


def safe_error(error):
    text = str(error or "")
    for key, value in os.environ.items():
        if any(part in key.upper() for part in ("TOKEN", "SECRET", "PASSWORD", "API_KEY")) and value:
            text = text.replace(value, "[REDACTED]")
    # Do not export exception URLs, which may contain truncated credentials.
    if "access_token" in text.lower() or "https://" in text.lower():
        return "요청 실패 — 인증정보 보호를 위해 상세 URL 생략"
    return text[:240]


def format_metric(value, delta=None):
    if value is None:
        return "미집계(증감 미확인)"
    change = "증감 미확인" if delta is None else "0" if delta == 0 else f"{delta:+,}"
    return f"{value:,}({change})"


def main():
    rows = []
    for name, collect in (
        ("TikTok", get_tiktok_followers_multi),
        ("Facebook", get_facebook_followers_multi),
        ("Instagram", get_instagram_followers_multi),
        ("Threads", get_threads_followers_multi),
    ):
        for brand, info in collect().items():
            count = info.get("count")
            rows.append({
                "platform": name, "brand": brand,
                "followers": count, "formatted_followers": format_metric(count),
                "delta": None,
                "delta_reason": "동일 마감 기준의 전일 스냅샷 미검증",
                "source": "공개 프로필 참고값; 공식 인사이트 아님" if name == "TikTok" else "공식 API",
                "status": safe_error(info.get("error")) or "조회 성공",
                "period_views": "미집계(증감 미확인)",
            })
    result = {
        "checked_at_kst": datetime.now(KST).isoformat(),
        "collection_status": "complete" if all(r["followers"] is not None for r in rows) else "partial",
        "rows": rows,
        "scope": "Read-only SNS statistics; no publications, messages, permission changes, or secret values",
    }
    Path("ceo_sns_probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
