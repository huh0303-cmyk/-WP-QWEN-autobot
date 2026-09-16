#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("CONTROL_OPERATIONS_DB", ROOT / "data" / "control-operations.sqlite3"))
OUT_JSON = Path(os.environ.get("LONDON_ACTIVITY_REPORT_JSON", ROOT / "data" / "london_project_activity_report.json"))
OUT_MD = Path(os.environ.get("LONDON_ACTIVITY_REPORT_MD", ROOT / "data" / "london_project_activity_report.md"))


def load():
    if not DB.exists():
        return [], []
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    try:
        tasks = [dict(r) for r in db.execute("SELECT * FROM london_tasks ORDER BY updated DESC")]
        events = [dict(r) for r in db.execute("SELECT * FROM london_events ORDER BY event_id DESC LIMIT 500")]
    except sqlite3.OperationalError:
        return [], []
    finally:
        db.close()
    return tasks, events


def main():
    tasks, events = load()
    counts = Counter(str(row.get("state", "UNKNOWN")) for row in tasks)
    payload = {
        "project": "london-project",
        "generated_at": time.time(),
        "task_count": len(tasks),
        "state_counts": dict(sorted(counts.items())),
        "recent_tasks": tasks[:100],
        "recent_events": events[:200],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 런던프로젝트 작업 현황", "", f"총 작업: {len(tasks)}", "", "## 상태별"]
    for state, count in sorted(counts.items()):
        lines.append(f"- {state}: {count}")
    lines.extend(["", "## 최근 작업"])
    for row in tasks[:50]:
        lines.append(
            f"- `{row['task_id']}` · {row.get('state')} · {row.get('platform') or '-'} · "
            f"{row.get('target') or '-'} · {row.get('title') or '-'} · retries={row.get('retry_count', 0)}"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"task_count": len(tasks), "state_counts": dict(counts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
