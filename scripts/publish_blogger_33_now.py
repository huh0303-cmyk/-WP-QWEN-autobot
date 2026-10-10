#!/usr/bin/env python3
"""Sequentially publish one public article to every configured Blogger destination."""
from __future__ import annotations

import html
import json
import os
import time
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from blogger_free_text import blogger_generate_with_fallback  # noqa: E402
from automation_hub.blogger_search_description import build_search_description, validate_search_description
from automation_hub.editorial_language_policy import language_mismatch_fields
from review_sheet import append_review_rows
from repair_blogger_images import stabilize_html_images
from blogger_free_image import pick_image, insert_image
from blogger_adsense_structure import rules_for, structure_issues

RESULT = ROOT / "artifacts" / "blogger-33-public-results.json"


def load_sites() -> list[dict]:
    profiles = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    sites = [{
        "key": p["site_key"], "id": str(p["blogspot"]["destination_id"]),
        "url": p["blogspot"]["url"], "language": p["language"],
        "theme": p["blogspot"].get("theme") or p["wordpress"]["theme"], "persona": p["blogspot"]["persona"],
        "tone": p["blogspot"]["tone"],
    } for p in profiles if p["blogspot"].get("ready_for_automation")]
    if len(sites) != 33 or len({s["id"] for s in sites}) != 33 or len({s["url"].rstrip('/').lower() for s in sites}) != 33:
        raise RuntimeError("scope guard: exactly 33 unique Blogger IDs and URLs are required")
    priority = {"kwellness_lab": 0, "kskin365": 1}
    return sorted(sites, key=lambda s: (priority.get(s["key"], 2), s["key"]))


def access_token() -> str:
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


import re as _re
_HANGUL = r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7a3]"


def strip_hangul_parentheticals(text: str) -> str:
    """English articles: drop '(경복궁)' style Hangul glosses; the romanization before them stays."""
    text = _re.sub(r"\s*[\(（][^()（）]*" + _HANGUL + r"[^()（）]*[\)）]", "", text)
    text = _re.sub(r"\s*[\[「『][^\]」』]*" + _HANGUL + r"[^\]」』]*[\]」』]", "", text)
    return text


def generate(site: dict, hint: str = "") -> tuple[str, str, list[str], str, str]:
    if str(site["language"]).lower().startswith("ko"):
        lang_rule = ("반드시 한국어로만 작성하세요. 제목·본문·소제목·라벨 전부 한글이어야 하며 영어 문장은 절대 쓰지 않습니다 "
                     "(고유명사·약어만 예외). 본문 분량은 한글 2400~3500자. 영어로 쓰면 폐기됩니다. "
                     "image_subject 만 영어 단어 2~5개로 씁니다.")
    else:
        lang_rule = ("English: 1400-1800 words (never fewer than 1200; count them). For English articles use Latin script only: "
                     "write Korean names and terms in romanization (e.g. Gyeongbokgung), with no Hangul characters anywhere in title, body or labels.")
    requested_topic = os.environ.get("BLOGGER_TOPIC_HINT", "").strip()
    topic = requested_topic or site["theme"]
    prompt = f"""Write one original evergreen article for {site['url']}.
Topic: {topic}. Site theme: {site['theme']}. Persona: {site['persona']}. Tone: {site['tone']}.
Language: {site['language']}. Return JSON only with title, content_html, labels, image_subject (2-5 plain English words describing one concrete photographable subject for the article, e.g. 'Seoul palace autumn').
{rules_for(site['language'], site['theme'])}
Cautious source-aware wording and no invented facts.
Write in a natural editorial voice with varied sentence structure. Never mention AI, language models,
automatic generation, prompts, or how the article was produced.
{lang_rule}
Provide 1-3 short, highly relevant labels only.{hint}"""
    raw = blogger_generate_with_fallback(prompt, temperature=0.5).strip()
    try:
        import economy_text
        print(f"writer engine for {site['key']}: {economy_text.last_writer_model}")
    except Exception:
        pass
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].removeprefix("json").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Models occasionally return a literal backslash in otherwise valid JSON.
        # Preserve the character instead of losing the whole site's draft.
        import re
        data = json.loads(re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw))
    title, body = str(data["title"]).strip(), str(data["content_html"]).strip()
    labels = [str(x).strip()[:80] for x in data["labels"] if str(x).strip()][:3]
    if str(site["language"]).lower().startswith("en"):
        title, body = strip_hangul_parentheticals(title), strip_hangul_parentheticals(body)
        labels = [strip_hangul_parentheticals(x) for x in labels]
    if str(site["language"]).lower().startswith("ko"):
        import re as _r2
        _t = _r2.sub(r"<[^>]+>", "", body)
        if len(_r2.findall(r"[가-힣]", _t)) < 0.5 * max(1, len(_r2.findall(r"[A-Za-z가-힣]", _t))) or not _r2.search(r"[가-힣]", title):
            raise RuntimeError("language mismatch: Korean site produced non-Korean output")
    if not title or len(body) < 1500 or not (1 <= len(labels) <= 3):
        raise RuntimeError("Gemini Flash output failed quality gate")
    issues = structure_issues(body, site["theme"], site["language"])
    if issues:
        raise RuntimeError("adsense structure gate: " + "; ".join(issues))
    disclosure_phrases = (
        "as an ai", "ai-generated", "generated by ai", "language model",
        "인공지능으로 생성", "ai가 작성", "ai로 작성", "자동 생성된 글",
    )
    visible_copy = f"{title}\n{body}".casefold()
    if any(phrase in visible_copy for phrase in disclosure_phrases):
        raise RuntimeError("editorial output contains a generation disclosure phrase")
    mismatches = language_mismatch_fields(
        language=site["language"], title=title, meta_description="",
        content=body, labels=labels,
    )
    if mismatches:
        for m in list(_re.finditer(_HANGUL + r"+", body))[:4]:
            print("hangul context:", repr(body[max(0, m.start() - 40):m.end() + 20]))
        raise RuntimeError("language mismatch: English output contains Korean text in " + ", ".join(mismatches))
    description = build_search_description(title=title, topic=site["theme"], language=site["language"])
    validate_search_description(description)
    image_subject = str(data.get("image_subject") or "").strip()[:100]
    return title, body, labels, description, image_subject


def main() -> int:
    draft_mode = os.environ.get("BLOGGER_REVIEW_DRAFT_MODE", "false").strip().lower() == "true"
    run_key = os.environ.get("REVIEW_RUN_KEY" if draft_mode else "PUBLIC_RUN_KEY", "").strip()
    if not run_key:
        raise SystemExit("PUBLIC_RUN_KEY is required")
    token = access_token()
    headers = {"Authorization": f"Bearer {token}"}
    sites = load_sites()
    requested_site = os.environ.get("BLOGGER_SITE_KEY", "").strip()
    if requested_site:
        sites = [site for site in sites if site["key"] == requested_site]
        if len(sites) != 1:
            raise SystemExit(f"unknown BLOGGER_SITE_KEY: {requested_site}")
    expected_count = len(sites)
    results, failed = [], False
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    pace = float(os.environ.get("BLOGGER_PACE_SECONDS", "0") or 0)
    for site_no, site in enumerate(sites):
        if pace and site_no:
            time.sleep(pace)  # keeps free-tier writers under their per-minute token limits
        marker = f"blogger33-{'review' if draft_mode else 'public'}:{run_key}:{site['key']}"
        endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{site['id']}/posts"
        try:
            existing = requests.get(endpoint, params={"status": ["draft", "live", "scheduled"], "view": "ADMIN", "fetchBodies": "true", "maxResults": 100}, headers=headers, timeout=30)
            existing.raise_for_status()
            match = next((p for p in existing.json().get("items", []) if marker in str(p.get("content", ""))), None)
            if match:
                if draft_mode:
                    review_url = f"https://www.blogger.com/blog/post/edit/{site['id']}/{match.get('id', '')}"
                    queued = append_review_rows([{
                        "platform": "Blogspot", "channel": site["key"],
                        "title": match.get("title", ""), "review_url": review_url,
                        "status": "비공개 초안", "decision": "검토대기",
                        "note": "33개 Blogger 검토 초안 (기존 초안 복구)",
                    }])
                    if not queued:
                        raise RuntimeError("control-room review queue sync failed")
                    results.append({"site": site["key"], "status": "drafted_existing",
                                    "review_url": review_url, "post_id": match.get("id", "")})
                else:
                    results.append({"site": site["key"], "status": "existing", "url": match.get("url", ""), "post_id": match.get("id", "")})
                RESULT.write_text(json.dumps({"run_key": run_key, "updated_at": datetime.now(timezone.utc).isoformat(), "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
                continue
            hint = ""
            for attempt in range(4):
                try:
                    title, body, labels, description, image_subject = generate(site, hint)
                    break
                except (RuntimeError, ValueError) as gate_exc:  # ValueError covers JSONDecodeError (empty/non-JSON model output)
                    retriable = isinstance(gate_exc, ValueError) or any(
                        k in str(gate_exc) for k in ("adsense structure gate", "language mismatch", "quality gate"))
                    if not retriable or attempt == 3:
                        raise
                    print(f"generation retry {attempt + 1} for {site['key']}: {str(gate_exc)[:120]}")
                    if "too short" in str(gate_exc):
                        hint = ("\nIMPORTANT: your previous draft was too short (" + str(gate_exc).split("(")[-1].rstrip(")") +
                                "). Write a clearly LONGER article: at least 1500 words in English or 3000 characters in Korean, "
                                "with fuller paragraphs of practical detail under every heading.")
                    else:
                        hint = "\nIMPORTANT: return one valid JSON object only, no commentary, and follow every structure rule."
            try:  # free image chain; failure must never block publication
                image_policy = os.environ.get("BLOGGER_IMAGE_POLICY", "auto_free").strip().lower()
                found = None if image_policy == "none" else pick_image(image_subject or site['theme'], alternates=[site['theme']])
                # Free-only rule: relevant free stock/AI image or no image; never a generic topic card.
                if found and found.get("url"):
                    body = insert_image(body, found, title)
            except Exception as exc:
                print(f"image step skipped: {type(exc).__name__}")
            body = f"<!-- {marker} -->\n{body}"
            schedule_at_raw = os.environ.get("BLOGGER_SCHEDULE_AT", "").strip()
            scheduled_kst = None
            if schedule_at_raw:
                try:
                    candidate = datetime.strptime(schedule_at_raw[:16], "%Y-%m-%dT%H:%M")
                    now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
                    if candidate > now_kst:
                        scheduled_kst = candidate
                except ValueError:
                    scheduled_kst = None
            schedule_mode = bool(scheduled_kst) and not draft_mode
            insert_is_draft = draft_mode or schedule_mode
            response = requests.post(endpoint, params={"isDraft": "true" if insert_is_draft else "false"}, headers=headers,
                                     json={"kind": "blogger#post", "title": title, "content": body, "labels": labels}, timeout=30)
            response.raise_for_status()
            post = response.json(); url = post.get("url", "")
            if schedule_mode:
                publish_endpoint = f"{endpoint}/{post.get('id', '')}/publish"
                publish_date = scheduled_kst.replace(tzinfo=timezone(timedelta(hours=9))).astimezone(timezone.utc).isoformat().replace("+00:00","Z")
                scheduled = requests.post(publish_endpoint, params={"publishDate": publish_date}, headers=headers, timeout=30)
                scheduled.raise_for_status()
                post = scheduled.json()
                ok = bool(post.get("id")) and str(post.get("status", "")).upper() == "SCHEDULED"
                results.append({"site": site["key"], "status": "scheduled" if ok else "verification_failed",
                                "url": post.get("url", url), "post_id": post.get("id", ""),
                                "scheduled_at": scheduled_kst.strftime("%Y-%m-%dT%H:%M")})
            elif draft_mode:
                review_url = f"https://www.blogger.com/blog/post/edit/{site['id']}/{post.get('id', '')}"
                queued = append_review_rows([{
                    "platform": "Blogspot", "channel": site["key"], "title": title,
                    "review_url": review_url, "status": "비공개 초안", "decision": "검토대기",
                    "note": f"검색 설명(붙여넣기용): {description}",
                }])
                ok = bool(post.get("id")) and queued
                if not queued:
                    raise RuntimeError("draft created but control-room review queue sync failed")
                results.append({"site": site["key"], "status": "drafted" if ok else "verification_failed",
                                "review_url": review_url, "post_id": post.get("id", ""),
                                "search_description": description,
                                "search_description_length": len(description),
                                "search_description_status": "required_in_blogger_editor"})
            else:
                import time as _t
                check = requests.get(url, timeout=30)
                for _n in range(3):  # Blogger throttles shared runner IPs (429) and lags briefly (404)
                    if check.status_code == 200:
                        break
                    _t.sleep(8 * (_n + 1))
                    check = requests.get(url, timeout=30)
                ok = check.status_code == 200 and marker in check.text and title in check.text
                if not ok and check.status_code in (404, 429):
                    # public page unreachable from this IP: confirm through the authenticated API instead
                    api_status = str(post.get("status", ""))  # insert response already reports LIVE
                    try:
                        api_post = requests.get(f"{endpoint}/{post.get('id', '')}", headers=headers, timeout=30)
                        if api_post.ok:
                            api_status = str(api_post.json().get("status", api_status))
                    except requests.RequestException:
                        pass
                    ok = api_status == "LIVE" and bool(post.get("id"))
                    print(f"verify {site['key']}: public HTTP {check.status_code}, api status {api_status}")
                results.append({"site": site["key"], "status": "published" if ok else "verification_failed", "url": url, "post_id": post.get("id", ""), "http": check.status_code})
            failed = failed or not ok
        except Exception as exc:
            failed = True
            results.append({"site": site["key"], "status": "failed", "error": str(exc)[:500]})
        RESULT.write_text(json.dumps({"run_key": run_key, "updated_at": datetime.now(timezone.utc).isoformat(), "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    expected = {"drafted", "drafted_existing"} if draft_mode else ({"scheduled"} if os.environ.get("BLOGGER_SCHEDULE_AT", "").strip() else {"published", "existing"})
    exact_complete = len(results) == expected_count and len({r.get("site") for r in results}) == expected_count and all(r.get("status") in expected for r in results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if failed or not exact_complete else 0


if __name__ == "__main__":
    raise SystemExit(main())
