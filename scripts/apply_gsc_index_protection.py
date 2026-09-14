#!/usr/bin/env python3
"""index_audit_manifest.json(audit_gsc_post_index.py 결과)에서 실제로
GSC에 "indexed"로 확인된 글 ID를 뽑아 scripts/data/protected_indexed_posts.json에
병합한다. 사용자 지시(2026-08-21, [[feedback_never_hide_indexed_posts]]) —
27개 사이트 전체로 보호 목록 커버리지를 채우기 위한 1회성 병합 스크립트.
기존 보호 목록은 지우지 않고 합집합으로 유지한다."""
import json
import sys
from pathlib import Path

MANIFEST_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "index_audit_manifest.json")
PROTECTED_PATH = Path("scripts/data/protected_indexed_posts.json")


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    try:
        protected = {k: set(v) for k, v in json.loads(
            PROTECTED_PATH.read_text(encoding="utf-8")).items()}
    except FileNotFoundError:
        protected = {}

    report = []
    for site, entry in manifest.get("sites", {}).items():
        posts = entry.get("posts", {})
        indexed_ids = [int(pid) for pid, p in posts.items() if p.get("state") == "indexed"]
        if not indexed_ids:
            continue
        before = len(protected.get(site, set()))
        protected.setdefault(site, set()).update(indexed_ids)
        after = len(protected[site])
        report.append((site, len(posts), len(indexed_ids), before, after))

    out = {site: sorted(ids) for site, ids in protected.items()}
    PROTECTED_PATH.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{'사이트':40s} {'조사됨':>6s} {'색인됨':>6s} {'기존보호':>8s} {'최종보호':>8s}")
    for site, checked, idx, before, after in sorted(report, key=lambda r: -r[2]):
        print(f"{site:40s} {checked:6d} {idx:6d} {before:8d} {after:8d}")
    total_indexed = sum(r[2] for r in report)
    print(f"\n총 {len(report)}개 사이트, {total_indexed}개 글 보호 목록에 반영 완료")


if __name__ == "__main__":
    main()
