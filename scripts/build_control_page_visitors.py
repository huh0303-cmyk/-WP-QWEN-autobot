#!/usr/bin/env python3
"""Export only verified daily visitor values for the static CONTROL page."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KST = dt.timezone(dt.timedelta(hours=9))


def main() -> None:
    source = json.loads((ROOT / "daily_site_traffic_result.json").read_text(encoding="utf-8"))
    sites: dict[str, dict[str, object]] = {}
    dates: list[str] = []
    checked_at = str(source.get("checked_at") or "")
    for row in source.get("records", []):
        domain = str(row.get("domain") or "").strip().lower().strip(".")
        count = row.get("yesterday_visitors")
        if not domain or not isinstance(count, int) or count < 0:
            continue
        date = str(row.get("date") or "")
        reference_date = ""
        if date:
            try:
                reference_date = (dt.date.fromisoformat(date) - dt.timedelta(days=1)).isoformat()
                dates.append(reference_date)
            except ValueError:
                pass
        sites[domain] = {
            "yesterday_visitors": count,
            "yesterday_delta": row.get("yesterday_delta") if isinstance(row.get("yesterday_delta"), int) else None,
            "reference_date": reference_date,
            "source": "verified site visitor counter",
            "checked_at": str(row.get("checked_at") or checked_at),
        }

    # Include Blogger native visitor statistics only when their snapshot is current.
    blogger_path = ROOT / "data" / "blogger_traffic_latest.json"
    if blogger_path.exists():
        try:
            blogger = json.loads(blogger_path.read_text(encoding="utf-8"))
            generated = dt.datetime.fromisoformat(str(blogger.get("generated_at", "")).replace("Z", "+00:00"))
            if generated.tzinfo is None:
                generated = generated.replace(tzinfo=KST)
            if generated.astimezone(KST).date() == dt.datetime.now(KST).date():
                for url, values in (blogger.get("sites") or {}).items():
                    domain = str(url).lower().replace("https://", "").replace("http://", "").strip("/")
                    count = values.get("yesterday") if isinstance(values, dict) else None
                    if domain and isinstance(count, int) and count >= 0:
                        sites[domain] = {
                            "yesterday_visitors": count,
                            "yesterday_delta": values.get("yesterday_delta") if isinstance(values.get("yesterday_delta"), int) else None,
                            "reference_date": (dt.datetime.now(KST).date() - dt.timedelta(days=1)).isoformat(),
                            "source": "Blogger native stats",
                            "checked_at": str(blogger.get("generated_at") or ""),
                        }
        except (OSError, ValueError, TypeError):
            pass

    if not sites:
        raise SystemExit("No verified visitor metrics available; refusing to publish an empty snapshot")
    output = {
        "generated_at": checked_at,
        "reference_date": max(dates) if dates else "",
        "source": "verified previous-day site counters; stale platform snapshots are excluded",
        "sites": sites,
    }
    target = ROOT / "docs" / "visitor_metrics.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(sites)} verified visitor metrics to {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
