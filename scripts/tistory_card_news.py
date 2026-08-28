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
        language = str(draft.get("language") or "ko")
        kicker = html.escape(str(draft.get("card_kicker") or ("QUICK GUIDE" if language == "en" else "오늘의 핵심 정보")))
        points = draft.get("card_points") or []
        if not points:
            points = [description]
        points_html = "".join(f"<li>{html.escape(str(point))}</li>" for point in points[:4])
        sources = draft.get("sources") or []
        source_label = html.escape(str(draft.get("card_source_label") or ("Official source in article" if language == "en" else "본문의 공식 출처에서 최종 확인")))
        if sources:
            source_label += " · " + html.escape(sources[0].split("/")[2])
        cta_text = html.escape(str(draft.get("card_cta_text") or ("Check the official guide" if language == "en" else "공식 기준 확인하기")))
        cta_url = html.escape(str(draft.get("card_cta_url") or (sources[0] if sources else "#")), quote=True)
        lang = "en" if language == "en" else "ko"
        page = f"""<!doctype html><html lang='{lang}'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{title}</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#e9eff5;font-family:Arial,'Noto Sans KR',sans-serif}}main{{width:720px;min-height:900px;margin:auto;padding:58px 50px;background:linear-gradient(150deg,#09263d 0%,#145d75 58%,#1d8290 100%);color:#fff;display:flex;flex-direction:column;justify-content:space-between}}.kicker{{display:inline-block;padding:9px 16px;border:1px solid rgba(255,255,255,.5);border-radius:999px;font-size:18px;letter-spacing:.05em}}h1{{font-size:48px;line-height:1.18;margin:23px 0 25px;word-break:keep-all}}.summary{{font-size:22px;line-height:1.48;color:#dff4f7}}ul{{list-style:none;margin:25px 0;padding:0;display:grid;gap:12px}}li{{padding:15px 19px;border-radius:15px;background:rgba(255,255,255,.12);font-size:22px;line-height:1.35}}li:before{{content:'✓';font-weight:bold;margin-right:12px;color:#9ff2c8}}.cta{{display:block;margin:22px 0 25px;padding:19px 22px;border-radius:14px;background:#fff;color:#0b5369;text-align:center;text-decoration:none;font-size:24px;font-weight:800;box-shadow:0 8px 24px rgba(0,0,0,.18)}}.cta:after{{content:' →'}}footer{{border-top:1px solid rgba(255,255,255,.3);padding-top:17px;font-size:16px;line-height:1.45;color:#d8edf1}}</style><main><section><span class='kicker'>{kicker}</span><h1>{title}</h1><p class='summary'>{description}</p><ul>{points_html}</ul><a class='cta' href='{cta_url}' target='_blank' rel='noopener noreferrer'>{cta_text}</a></section><footer>{source_label}<br>기준일: {html.escape(str(payload.get('date') or payload.get('target_date') or ''))} · 저장상태: 검토 대기</footer></main></html>"""
        (out / f"card-{index:02d}.html").write_text(page, encoding="utf-8")
    print(json.dumps({"cards": len(payload.get("drafts", [])), "output_dir": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
