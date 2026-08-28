#!/usr/bin/env python3
"""Create mobile card-news HTML from Tistory drafts without external image APIs."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drafts", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.drafts).read_text(encoding="utf-8"))
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for index, draft in enumerate(payload.get("drafts", []), start=1):
        title = html.escape(str(draft.get("title") or draft.get("site_title") or "오늘의 생활정보"))
        description = html.escape(str(draft.get("meta_description") or draft.get("summary") or "본문에서 신청 조건과 확인 방법을 확인하세요."))
        source = html.escape(str(draft.get("source_url") or "공식 출처 확인 필수"))
        page = f"""<!doctype html><html lang='ko'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{title}</title><style>body{{margin:0;background:#eef3f8;font-family:Arial,'Noto Sans KR',sans-serif}}main{{box-sizing:border-box;max-width:720px;min-height:900px;margin:auto;padding:72px 48px;background:linear-gradient(145deg,#102a43,#246b86);color:white;display:flex;flex-direction:column;justify-content:space-between}}h1{{font-size:54px;line-height:1.2;margin:0}}p{{font-size:28px;line-height:1.55}}small{{font-size:18px;color:#d9edf3}}</style><main><div><small>오늘 확인한 생활정보</small><h1>{title}</h1></div><p>{description}</p><small>기준일과 신청 조건은 본문 및 공식 출처에서 다시 확인하세요.<br>{source}</small></main></html>"""
        (out / f"card-{index:02d}.html").write_text(page, encoding="utf-8")
    print(json.dumps({"cards": len(payload.get("drafts", [])), "output_dir": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
