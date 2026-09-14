#!/usr/bin/env python3
"""Create mobile card-news HTML from Tistory drafts without external image APIs."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from string import Template


THEMES = {
    "tistory_insurance_lab": {"bg1": "#071b33", "bg2": "#174b83", "accent": "#62d5ff", "soft": "#d9f4ff", "mark": "INSURANCE"},
    "tistory_health_info": {"bg1": "#2d123f", "bg2": "#8e3f73", "accent": "#ffcf75", "soft": "#fff0d5", "mark": "HEALTH"},
    "tistory_finance_housing": {"bg1": "#13271f", "bg2": "#357052", "accent": "#d5f071", "soft": "#efffc7", "mark": "HOUSING"},
    "tistory_life365": {"bg1": "#32120c", "bg2": "#b64b2b", "accent": "#ffd166", "soft": "#fff1c7", "mark": "BENEFIT"},
    "tistory_ktrip365": {"bg1": "#0b2340", "bg2": "#2368a2", "accent": "#ff8d6b", "soft": "#e0f1ff", "mark": "K-TRIP"},
}


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
        theme = THEMES.get(str(draft.get("site_id")), THEMES["tistory_life365"])
        bg1, bg2 = theme["bg1"], theme["bg2"]
        accent, soft, mark = theme["accent"], theme["soft"], theme["mark"]
        card_no = f"{index:02d}"
        lang = "en" if language == "en" else "ko"
        date_label = html.escape(str(payload.get("date") or payload.get("target_date") or ""))
        page = Template("""<!doctype html><html lang='$lang'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>$title</title><style>*{box-sizing:border-box}body{margin:0;background:#edf1f5;font-family:Arial,'Noto Sans KR',sans-serif}main{position:relative;overflow:hidden;width:720px;min-height:900px;margin:auto;padding:48px 48px 42px;background:linear-gradient(145deg,$bg1 0%,$bg2 100%);color:#fff;display:flex;flex-direction:column;justify-content:space-between}main:before{content:'';position:absolute;width:330px;height:330px;border:80px solid $accent;opacity:.10;border-radius:50%;right:-185px;top:-170px}main:after{content:'';position:absolute;width:190px;height:190px;background:radial-gradient(circle,$accent 2px,transparent 3px);background-size:18px 18px;opacity:.16;left:-25px;bottom:80px}section,footer{position:relative;z-index:1}.topline{display:flex;align-items:center;justify-content:space-between}.brand{font-size:17px;font-weight:800;letter-spacing:.15em;color:$accent}.number{font-size:28px;font-weight:900;color:$accent}.kicker{display:inline-block;margin-top:28px;padding:9px 15px;background:$accent;color:$bg1;border-radius:8px;font-size:17px;font-weight:900;letter-spacing:.04em}h1{font-size:47px;line-height:1.16;margin:21px 0 18px;word-break:keep-all;letter-spacing:-.025em}.rule{width:72px;height:6px;border-radius:8px;background:$accent;margin-bottom:19px}.summary{font-size:21px;line-height:1.45;color:$soft;margin:0}ul{list-style:none;margin:24px 0 0;padding:0;display:grid;grid-template-columns:1fr 1fr;gap:12px}li{min-height:94px;padding:15px 16px;border:1px solid rgba(255,255,255,.16);border-radius:16px;background:rgba(255,255,255,.10);font-size:20px;line-height:1.33;backdrop-filter:blur(4px)}li:before{display:block;content:'0' counter(list-item);font-size:14px;font-weight:900;margin-bottom:7px;color:$accent;letter-spacing:.08em}.cta{display:block;margin:22px 0 22px;padding:18px 22px;border-radius:14px;background:$accent;color:$bg1;text-align:center;text-decoration:none;font-size:23px;font-weight:900;box-shadow:0 10px 28px rgba(0,0,0,.22)}.cta:after{content:'  →'}footer{display:flex;justify-content:space-between;gap:20px;border-top:1px solid rgba(255,255,255,.25);padding-top:16px;font-size:14px;line-height:1.42;color:$soft}footer span:last-child{text-align:right;white-space:nowrap}</style><main><section><div class='topline'><span class='brand'>$mark · INFO CARD</span><span class='number'>$card_no/05</span></div><span class='kicker'>$kicker</span><h1>$title</h1><div class='rule'></div><p class='summary'>$description</p><ul>$points_html</ul><a class='cta' href='$cta_url' target='_blank' rel='noopener noreferrer'>$cta_text</a></section><footer><span>$source_label</span><span>$date_label<br>검토 대기</span></footer></main></html>""").substitute(
            lang=lang, title=title, bg1=bg1, bg2=bg2, accent=accent, soft=soft,
            mark=mark, card_no=card_no, kicker=kicker, description=description,
            points_html=points_html, cta_url=cta_url, cta_text=cta_text,
            source_label=source_label, date_label=date_label,
        )
        (out / f"card-{index:02d}.html").write_text(page, encoding="utf-8")
    print(json.dumps({"cards": len(payload.get("drafts", [])), "output_dir": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
