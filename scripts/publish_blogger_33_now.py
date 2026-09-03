#!/usr/bin/env python3
"""Sequentially publish one public article to every configured Blogger destination."""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from openai_text import openai_generate_text  # noqa: E402
from replicate_image_provider import generate_image_url  # noqa: E402
from automation_hub.blogger_search_description import build_search_description, validate_search_description
from review_sheet import append_review_rows
from repair_blogger_images import stabilize_html_images

RESULT = ROOT / "artifacts" / "blogger-33-public-results.json"


def load_sites() -> list[dict]:
    profiles = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    sites = [{
        "key": p["site_key"], "id": str(p["blogspot"]["destination_id"]),
        "url": p["blogspot"]["url"], "language": p["language"],
        "theme": p["wordpress"]["theme"], "persona": p["blogspot"]["persona"],
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


def generate(site: dict) -> tuple[str, str, list[str], str]:
    prompt = f"""Write one original evergreen article for {site['url']}.
Topic: {site['theme']}. Persona: {site['persona']}. Tone: {site['tone']}.
Language: {site['language']}. Return JSON only with title, content_html, labels, image_subject.
Use 5 useful H2 sections, an actionable checklist, cautious source-aware wording, and no invented facts.
English: 900-1300 words. Korean: 1800-3000 characters. Provide 8-12 short labels."""
    raw = openai_generate_text(prompt, temperature=0.5, max_retries=3).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].removeprefix("json").strip()
    data = json.loads(raw)
    title, body = str(data["title"]).strip(), str(data["content_html"]).strip()
    labels = [str(x).strip()[:80] for x in data["labels"] if str(x).strip()][:12]
    if not title or len(body) < 1500 or len(labels) < 8:
        raise RuntimeError("GPT-5 mini output failed quality gate")
    image = generate_image_url(str(data.get("image_subject") or title), theme=site["theme"])
    if image:
        body = f'<figure><img src="{html.escape(image, quote=True)}" alt="{html.escape(title, quote=True)}"/></figure>\n' + body
    description = build_search_description(title=title, topic=site["theme"], language=site["language"])
    validate_search_description(description)
    return title, body, labels, description


def main() -> int:
    draft_mode = os.environ.get("BLOGGER_REVIEW_DRAFT_MODE", "false").strip().lower() == "true"
    run_key = os.environ.get("REVIEW_RUN_KEY" if draft_mode else "PUBLIC_RUN_KEY", "").strip()
    if not run_key:
        raise SystemExit("PUBLIC_RUN_KEY is required")
    token = access_token()
    headers = {"Authorization": f"Bearer {token}"}
    results, failed = [], False
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    for site in load_sites():
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
            title, body, labels, description = generate(site)
            body, image_evidence = stabilize_html_images(
                body, repo=os.environ["GITHUB_REPOSITORY"], gh_token=os.environ["GH_ASSET_TOKEN"],
                blog_id=site["id"], asset_key=f"new-{run_key}-{site['key']}",
            )
            if any(item["status"] != "stable" and not item.get("stable_src") for item in image_evidence):
                raise RuntimeError("permanent image hard gate failed")
            body = f"<!-- {marker} -->\n{body}"
            response = requests.post(endpoint, params={"isDraft": "true" if draft_mode else "false"}, headers=headers,
                                     json={"kind": "blogger#post", "title": title, "content": body, "labels": labels}, timeout=30)
            response.raise_for_status()
            post = response.json(); url = post.get("url", "")
            if draft_mode:
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
                                "search_description": description})
            else:
                check = requests.get(url, timeout=30)
                ok = check.status_code == 200 and marker in check.text and title in check.text
                results.append({"site": site["key"], "status": "published" if ok else "verification_failed", "url": url, "post_id": post.get("id", ""), "http": check.status_code})
            failed = failed or not ok
        except Exception as exc:
            failed = True
            results.append({"site": site["key"], "status": "failed", "error": str(exc)[:500]})
        RESULT.write_text(json.dumps({"run_key": run_key, "updated_at": datetime.now(timezone.utc).isoformat(), "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    expected = {"drafted", "drafted_existing"} if draft_mode else {"published", "existing"}
    exact_complete = len(results) == 33 and len({r.get("site") for r in results}) == 33 and all(r.get("status") in expected for r in results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if failed or not exact_complete else 0


if __name__ == "__main__":
    raise SystemExit(main())
