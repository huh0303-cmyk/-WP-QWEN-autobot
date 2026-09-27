#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
STATE_DIR = ROOT / "data" / "london-pipeline"
KST = timezone(timedelta(hours=9))


def _load_runtime_env() -> None:
    os.environ.setdefault("FORCE_SOURCE_IPV4", "true")
    if os.environ.get("FORCE_SOURCE_IPV4", "false").strip().lower() in {"1", "true", "yes", "on"}:
        import socket
        if not getattr(socket, "_korea365_ipv4_patched", False):
            original = socket.getaddrinfo
            def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
                return original(host, port, socket.AF_INET, type, proto, flags)
            socket.getaddrinfo = _ipv4_only_getaddrinfo
            socket._korea365_ipv4_patched = True

    for path in (Path("/etc/korea365/control.env"), Path("/etc/korea365/n8n.env")):
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    for path in (Path("/etc/korea365/article-runtime.json"), Path("/etc/korea365/wp-sites.json")):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (str, int, float)) and str(value).strip():
                    os.environ.setdefault(str(key), str(value))
    os.environ.setdefault("GITHUB_REPOSITORY", "huh0303-cmyk/-WP-QWEN-autobot")


def _state_path(run_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", run_id)
    return STATE_DIR / f"{safe}.json"


def _read_state(run_id: str) -> dict:
    path = _state_path(run_id)
    if not path.exists():
        raise RuntimeError(f"pipeline state not found: {run_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = _state_path(state["run_id"])
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _profile(site_id: str) -> tuple[str, dict]:
    from scripts.auto_write_and_draft import _profile_for
    return _profile_for(site_id)


def _parse_keyword(text: str) -> str:
    match = re.search(r"(?im)^KEYWORD:\s*(.+?)\s*$", text)
    if not match:
        raise RuntimeError("research output missing KEYWORD line")
    keyword = match.group(1).strip(" \t\"'")
    if not 3 <= len(keyword) <= 80:
        raise RuntimeError("research keyword length invalid")
    return keyword


def _network_titles() -> list[str]:
    cache = STATE_DIR / f"network-titles-{datetime.now(KST).date().isoformat()}.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8")).get("titles", [])
        except Exception:
            pass
    from scripts.refresh_keyword_pool import fetch_published_titles
    profiles = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    urls = []
    for item in profiles:
        wp = item.get("wordpress") or {}
        if wp.get("content_type") == "blog" and wp.get("url"):
            urls.append(wp["url"])
    titles: list[str] = []
    for url in sorted(set(urls)):
        titles.extend(fetch_published_titles(url))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"created_at": datetime.now(KST).isoformat(), "titles": titles}, ensure_ascii=False), encoding="utf-8")
    return titles


def stage_research(site_id: str, run_id: str, category: str = "") -> dict:
    _load_runtime_env()
    platform, profile = _profile(site_id)
    settings = profile["wordpress"] if platform == "wordpress" else profile["blogspot"]
    site_url = profile["wordpress"]["url"]
    state = {
        "run_id": run_id,
        "site_id": site_id,
        "platform": platform,
        "created_at": datetime.now(KST).isoformat(),
        "publish_mode": os.environ.get("PIPELINE_PUBLISH_MODE", "draft").strip().lower(),
        "category": category.strip(),
        "stage_status": {"research": "running"},
    }
    _write_state(state)
    from scripts.collect_keyword_search_demand import demand_context
    from scripts.refresh_keyword_pool import call_search_llm, overlaps_corpus, build_network_corpus

    recent_titles = _network_titles()
    corpus_norms, corpus_wordsets = build_network_corpus({"network": recent_titles})
    demand = demand_context(site_url)
    avoid = ""
    last_text = ""
    keyword = ""
    research_provider = ""
    direct_error = ""

    # Primary path: zero-cost direct evidence collection + local Ollama.
    try:
        from scripts.direct_topic_research import collect as collect_direct, choose_keyword as choose_direct
        evidence = collect_direct(profile, demand)
        for attempt in range(3):
            last_text = choose_direct(profile, evidence, avoid=avoid)
            keyword = _parse_keyword(last_text)
            if not overlaps_corpus(keyword, corpus_norms, corpus_wordsets):
                research_provider = "direct-google-naver-media+ollama"
                break
            avoid = f"Do not use '{keyword}' or close variants."
            keyword = ""
    except Exception as exc:
        direct_error = f"{type(exc).__name__}: {str(exc)[:300]}"

    # Bounded cloud fallback only when the zero-cost path is unavailable.
    if not keyword:
        from scripts.budget_guard import check_and_record
        check_and_record(0.02, label=f"london-agent1:{site_id}")
        client = None
        if os.environ.get("GEMINI_API_KEY"):
            from google import genai
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        today = datetime.now(KST).date().isoformat()
        avoid = ""
        for attempt in range(3):
            prompt = f"""Research a current article topic for {settings.get('persona','editor')}.
Date: {today}
Site theme: {profile['wordpress'].get('theme','')}
Selected category: {category or 'auto-select from site categories'}
Language: {profile.get('language','en')}
Tone: {settings.get('tone','')}

You MUST investigate current signals before choosing the topic:
- Google Search/Google News/Google Trends signals when observable
- Naver Search/Naver News/Naver DataLab signals when observable
- independent current media coverage
- site-specific GSC evidence below

Do not invent absolute Google or Naver search volume. If exact volume is not available, say unavailable and use only observed relative/search/media signals.
Do not confuse GSC impressions, media mentions, result counts, Trends indices, or ad keyword volume.
Choose a practical, non-duplicate search-intent topic for this site's audience.
Avoid topics already covered in this network. {avoid}

GSC context:
{demand}

Return exactly these six lines:
KEYWORD: <3-6 word search-style phrase>
GOOGLE: <observed signal or unavailable>
NAVER: <observed signal or unavailable>
MEDIA: <brief independent-media evidence>
VOLUME: <verified volume if actually available, otherwise unavailable>
RATIONALE: <why this topic fits now>
"""
            last_text, grounded = call_search_llm(client, prompt)
            keyword = _parse_keyword(last_text)
            if not overlaps_corpus(keyword, corpus_norms, corpus_wordsets):
                research_provider = "cloud-search-fallback"
                break
            avoid = f"Do not use '{keyword}' or close variants."
            keyword = ""

    if not keyword:
        raise RuntimeError(f"research exhausted; direct_error={direct_error}")
    state.update({
        "research": {
            "keyword": keyword,
            "evidence": last_text,
            "provider": research_provider,
            "direct_error": direct_error,
            "required_surfaces": ["google", "naver", "media", "gsc"],
            "exact_volume_policy": "never fabricated",
        },
    })
    state.setdefault("stage_status", {})["research"] = "ok"
    _write_state(state)
    return {"ok": True, "stage": "research", "site_id": site_id, "run_id": run_id, "keyword": keyword, "provider": research_provider}

def stage_write(run_id: str) -> dict:
    _load_runtime_env()
    state = _read_state(run_id)
    state.setdefault("stage_status", {})["write"] = "running"
    _write_state(state)
    site_id = state["site_id"]
    keyword = state["research"]["keyword"]
    platform, profile = _profile(site_id)
    settings = profile["wordpress"] if platform == "wordpress" else profile["blogspot"]
    from scripts.budget_guard import check_and_record
    from automation_hub.medical_editorial import require_medical_topic
    check_and_record(0.02, label=f"london-agent2:{site_id}")
    if os.environ.get("OPENAI_API_KEY", "").strip():
        os.environ["OPENAI_ENABLED"] = "true"
        os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")
    os.environ["LOCAL_TEXT_FALLBACK_ENABLED"] = "true"
    os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:3b")
    from scripts.auto_write_and_draft import _write_article
    require_medical_topic(profile, keyword)
    funnel = settings.get("editorial_funnel") or profile["wordpress"].get("editorial_funnel") or {}
    article, score, failures, provider = _write_article(
        keyword=keyword,
        site_theme=profile["wordpress"]["theme"] + (f". Editorial funnel: {json.dumps(funnel, ensure_ascii=False)}" if funnel else ""),
        language=profile["language"],
        persona=settings["persona"],
        tone=settings["tone"],
        min_chars=settings["min_chars"],
        target_chars=settings["target_chars"],
        max_chars=settings["max_chars"],
    )
    if article is None:
        raise RuntimeError(f"writer quality gate failed: score={score} failures={failures}")
    state["article"] = article
    state["writer"] = {"quality_score": score, "provider": provider, "failures": failures}
    state.setdefault("stage_status", {})["write"] = "ok"
    _write_state(state)
    return {"ok": True, "stage": "write", "site_id": site_id, "run_id": run_id, "quality_score": score, "provider": provider}


def stage_image(run_id: str) -> dict:
    _load_runtime_env()
    state = _read_state(run_id)
    state.setdefault("stage_status", {})["image"] = "running"
    _write_state(state)
    site_id = state["site_id"]
    article = state["article"]
    image_url = ""
    status = "no_image"
    image_enabled = not run_id.startswith("canary-") and os.environ.get("PIPELINE_IMAGE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    if image_enabled:
        try:
            from scripts.budget_guard import check_and_record
            from scripts.replicate_image_provider import generate_image_url
            check_and_record(0.01, label=f"london-agent3:{site_id}")
            subject = (article.get("image_queries") or [article["title"]])[0]
            image_url = generate_image_url(subject, theme=article["title"]) or ""
            status = "generated" if image_url else "no_image"
            if image_url and state["platform"] == "blogger":
                from scripts.stable_image_hosting import is_temporary, host_permanently
                if is_temporary(image_url):
                    if os.environ.get("GH_ASSET_TOKEN"):
                        image_url = host_permanently(image_url, asset_key=run_id, folder="blogger_images")
                        status = "generated_and_stabilized"
                    else:
                        image_url = ""
                        status = "discarded_temporary_url"
        except Exception as exc:
            image_url = ""
            status = f"image_failed_continue_without_image:{type(exc).__name__}"
    if not image_enabled and run_id.startswith("canary-"):
        status = "canary_no_image"
    state["image"] = {"url": image_url, "status": status}
    state.setdefault("stage_status", {})["image"] = "ok"
    _write_state(state)
    return {"ok": True, "stage": "image", "site_id": site_id, "run_id": run_id, "image_status": status}


def _publish_blogger(state: dict, profile: dict, public: bool) -> dict:
    from automation_hub.blogger_adapter import BloggerPublisher
    from automation_hub.publishing import PublishJob
    from scripts.process_platform_queue import _access_token
    article = state["article"]
    keyword = state["research"]["keyword"]
    image_url = state.get("image", {}).get("url", "")
    content = article["content_html"]
    if image_url:
        alt = f"Scene related to {(article.get('image_queries') or [keyword])[0]}"
        if profile["language"].lower().startswith("ko"):
            alt = f"{(article.get('image_queries') or [keyword])[0]} 관련 장면"
        content = f'<p><img src="{html.escape(image_url, quote=True)}" alt="{html.escape(str(alt), quote=True)}" /></p>' + content
    settings = profile["blogspot"]
    token = _access_token("")
    job = PublishJob(
        job_id=f"london-{state['run_id']}",
        site_id=state["site_id"],
        title=article["title"],
        content_html=content,
        labels=article.get("labels", []),
        publish_now=public,
        source_keyword=keyword,
        search_description=article.get("meta_description", ""),
    )
    result = BloggerPublisher(
        state["site_id"], settings["destination_id"], token, site_url=settings["url"]
    ).publish(job)
    if not result.ok:
        raise RuntimeError(f"Blogger publish failed: {result.error_code} {result.message}")
    return {
        "status": result.status,
        "platform": "blogger",
        "url": result.public_url,
        "post_id": result.remote_id,
        "title": article["title"],
    }


def stage_publish(run_id: str) -> dict:
    _load_runtime_env()
    state = _read_state(run_id)
    state.setdefault("stage_status", {})["publish"] = "running"
    _write_state(state)
    platform, profile = _profile(state["site_id"])
    public = state.get("publish_mode", "draft") == "publish"
    article = state["article"]
    keyword = state["research"]["keyword"]
    image_url = state.get("image", {}).get("url", "")
    if platform == "wordpress":
        from scripts.auto_write_and_draft import _publish_wordpress
        receipt = _publish_wordpress(
            site_url=profile["wordpress"]["url"],
            secret_name=profile["wordpress"]["secret_name"],
            article=article,
            image_url=image_url,
            keyword=keyword,
        )
        selected_category = str(state.get("category") or "").strip()
        if selected_category:
            from scripts.create_manual_wp_draft import resolve_category_id
            password = os.environ.get(profile["wordpress"]["secret_name"], "")
            category_id = resolve_category_id(profile["wordpress"]["url"], password, selected_category)
            if not category_id:
                raise RuntimeError(f"selected WordPress category not found: {selected_category}")
            response = requests.post(
                f"{profile['wordpress']['url'].rstrip('/')}/wp-json/wp/v2/posts/{receipt['post_id']}",
                auth=("huh0303@gmail.com", password),
                json={"categories": [category_id]},
                timeout=30,
            )
            response.raise_for_status()
        if public:
            password = os.environ.get(profile["wordpress"]["secret_name"], "")
            post_id = receipt["post_id"]
            response = requests.post(
                f"{profile['wordpress']['url'].rstrip('/')}/wp-json/wp/v2/posts/{post_id}",
                auth=("huh0303@gmail.com", password),
                json={"status": "publish"},
                timeout=40,
            )
            response.raise_for_status()
            row = response.json()
            from automation_hub.public_verifier import verify_publication
            verification = verify_publication(row.get("link", ""), article["title"], site_url=profile["wordpress"]["url"], attempts=3)
            if not verification.ok:
                raise RuntimeError(f"WordPress public verification failed: {verification.error_code}")
            receipt.update(status="published", url=verification.final_url or row.get("link", ""))
    else:
        receipt = _publish_blogger(state, profile, public)
    if not receipt.get("post_id"):
        raise RuntimeError("publisher receipt missing post_id")
    if not receipt.get("url"):
        raise RuntimeError("publisher receipt missing url")
    receipt["verified_at"] = datetime.now(KST).isoformat()
    state["receipt"] = receipt
    state.setdefault("stage_status", {})["publish"] = "ok"
    state["completed_at"] = datetime.now(KST).isoformat()
    _write_state(state)
    return {"ok": True, "stage": "publish", "site_id": state["site_id"], "run_id": run_id, "status": receipt["status"], "url": receipt["url"], "post_id": receipt["post_id"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["research", "write", "image", "publish"])
    parser.add_argument("--site-id", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--publish-mode", choices=["draft", "publish"], default=os.environ.get("PIPELINE_PUBLISH_MODE", "draft"))
    parser.add_argument("--category", default="")
    args = parser.parse_args()
    os.environ["PIPELINE_PUBLISH_MODE"] = args.publish_mode
    try:
        if args.stage == "research":
            if not args.site_id:
                raise SystemExit("--site-id is required for research")
            result = stage_research(args.site_id, args.run_id, args.category)
        elif args.stage == "write":
            result = stage_write(args.run_id)
        elif args.stage == "image":
            result = stage_image(args.run_id)
        else:
            result = stage_publish(args.run_id)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        try:
            state = _read_state(args.run_id)
        except Exception:
            state = {
                "run_id": args.run_id,
                "site_id": args.site_id,
                "created_at": datetime.now(KST).isoformat(),
                "stage_status": {},
            }
        state.setdefault("stage_status", {})[args.stage] = "failed"
        state["last_error"] = {
            "stage": args.stage,
            "type": type(exc).__name__,
            "message": str(exc)[:1200],
            "at": datetime.now(KST).isoformat(),
        }
        _write_state(state)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
