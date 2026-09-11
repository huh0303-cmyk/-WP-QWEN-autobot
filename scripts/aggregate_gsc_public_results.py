"""Aggregate per-site URL Inspection artifacts into a compact final table."""
from __future__ import annotations

import json
from pathlib import Path

rows = []
for path in Path("downloaded-results").rglob("sync_gsc_publish_*.json"):
    payload = json.loads(path.read_text(encoding="utf-8"))
    for site, result in payload.get("sites", {}).items():
        items = result.get("items", [])
        rows.append({
            "site": site,
            "posts_checked": result.get("posts_checked", 0),
            "indexed": sum(1 for item in items if item.get("inspection", {}).get("verdict") == "PASS"),
            "newly_published": result.get("published", 0),
            "uncertain": result.get("uncertain", 0),
            "failed": result.get("failed", 0),
        })

rows.sort(key=lambda row: row["site"])
out = {"source_run": 33284433841, "sites": rows}
Path("gsc_24_final_summary.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
for row in rows:
    print("\t".join(str(row[key]) for key in
          ("site", "posts_checked", "indexed", "newly_published", "uncertain", "failed")))
print(f"SITES={len(rows)} INDEXED_TOTAL={sum(row['indexed'] for row in rows)}")

md = ["## 24개 WP GSC URL 검사 최종 집계", "", "| 사이트 | 검사 글 | 색인 글 | 새 공개 | 미확정 | 실패 |", "|---|---:|---:|---:|---:|---:|"]
for row in rows:
    md.append(f"| {row['site']} | {row['posts_checked']} | {row['indexed']} | {row['newly_published']} | {row['uncertain']} | {row['failed']} |")
md += ["", f"**색인 글 합계: {sum(row['indexed'] for row in rows)}개**"]
Path("gsc_24_final_summary.md").write_text("\n".join(md), encoding="utf-8")
