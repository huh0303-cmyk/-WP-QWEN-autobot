#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import subprocess
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


def _ensure_wordpress_category(profile: dict, state: dict) -> int:
    """Resolve/create the selected category before image generation."""
    selected = str(state.get("category") or "").strip()
    if not selected:
        raise RuntimeError("WordPress category must be selected before writing completes")
    settings = profile["wordpress"]
    password = os.environ.get(settings["secret_name"], "")
    if not password:
        raise RuntimeError(f"WordPress credential missing for category validation: {settings['secret_name']}")

    from scripts.create_manual_wp_draft import WP_USER, resolve_category_id
    category_id = resolve_category_id(settings["url"], password, selected)
    if not category_id:
        last_error = ""
        for attempt in range(3):
            try:
                response = requests.post(
                    f"{settings['url'].rstrip('/')}/wp-json/wp/v2/categories",
                    auth=(WP_USER, password),
                    json={"name": selected},
                    timeout=30,
                )
                if response.status_code in (200, 201):
                    category_id = int(response.json().get("id") or 0)
                    break
                if response.status_code == 400:
                    category_id = resolve_category_id(settings["url"], password, selected)
                    if category_id:
                        break
                last_error = f"HTTP {response.status_code}: {response.text[:300]}"
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(2 + attempt)
        if not category_id:
            raise RuntimeError(f"WordPress category could not be resolved/created before image stage: {selected}; {last_error}")

    state["category_assignment"] = {
        "status": "ok",
        "name": selected,
        "id": int(category_id),
        "completed_at": datetime.now(KST).isoformat(),
    }
    _write_state(state)
    return int(category_id)


def _publish_wordpress_via_worker(state: dict, profile: dict, public: bool) -> dict:
    """Hand publication to the existing durable VPS WordPress worker."""
    queue = Path(os.environ.get("VPS_WP_QUEUE", ROOT / "data/vps-wp-queue"))
    queue.mkdir(parents=True, exist_ok=True)
    article = state["article"]
    category = state.get("category_assignment") or {}
    if category.get("status") != "ok" or not category.get("id"):
        raise RuntimeError("category assignment is not complete; publication blocked")

    attempt = int(state.get("publish_attempt") or 0) + 1
    state["publish_attempt"] = attempt
    _write_state(state)
    safe_run = re.sub(r"[^a-zA-Z0-9._-]+", "-", state["run_id"])
    job_id = f"london-{safe_run}-p{attempt}"
    payload = {
        "job_id": job_id,
        "site_url": profile["wordpress"]["url"].rstrip("/"),
        "secret_name": profile["wordpress"]["secret_name"],
        "title": article["title"],
        "content_html": article["content_html"],
        "image_url": state.get("image", {}).get("url", ""),
        "category_id": int(category["id"]),
        "category_name": category.get("name", ""),
        "focus_keyword": state["research"]["keyword"],
        "meta_description": article.get("meta_description", ""),
        "status_after_review": "publish" if public else "draft",
        "source": "london-four-agent",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "retries": 0,
    }
    tmp = queue / f".{job_id}.tmp"
    queued = queue / f"{job_id}.queued.json"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, queued)

    # Worker normally runs continuously; recover it if it is down.
    check = subprocess.run(
        ["systemctl", "is-active", "--quiet", "korea365-wp-publisher.service"],
        capture_output=True,
    )
    if check.returncode != 0:
        subprocess.run(["systemctl", "start", "korea365-wp-publisher.service"], check=True)

    deadline = time.time() + 220
    suffixes = ("published", "drafted", "failed", "credential_required")
    while time.time() < deadline:
        for suffix in suffixes:
            result_path = queue / f"{job_id}.{suffix}.json"
            if not result_path.exists():
                continue
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if suffix in {"failed", "credential_required"}:
                raise RuntimeError(
                    result.get("last_output")
                    or result.get("error")
                    or f"WordPress worker ended with {suffix}"
                )
            post_id = result.get("remote_id")
            url = result.get("public_url")
            if not post_id or not url:
                raise RuntimeError("WordPress worker receipt missing post ID or URL")
            return {
                "status": "published" if suffix == "published" else "draft",
                "platform": "wordpress",
                "site": profile["wordpress"]["url"],
                "url": url,
                "post_id": post_id,
                "title": article["title"],
                "worker_job_id": job_id,
            }
        time.sleep(2)
    raise RuntimeError(f"WordPress worker timeout waiting for receipt: {job_id}")


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
    if platform == "wordpress":
        category_id = _ensure_wordpress_category(profile, state)
    else:
        state["category_assignment"] = {
            "status": "ok",
            "name": str(state.get("category") or "").strip(),
            "id": None,
            "completed_at": datetime.now(KST).isoformat(),
        }
        _write_state(state)
        category_id = None
    state.setdefault("stage_status", {})["write"] = "ok"
    _write_state(state)
    return {
        "ok": True,
        "stage": "write",
        "site_id": site_id,
        "run_id": run_id,
        "quality_score": score,
        "provider": provider,
        "category": state["category_assignment"],
    }


def stage_image(run_id: str) -> dict:
    _load_runtime_env()
    state = _read_state(run_id)
    state.setdefault("stage_status", {})["image"] = "running"
    _write_state(state)
    site_id = state["site_id"]
    if state.get("platform") == "wordpress" and state.get("category_assignment", {}).get("status") != "ok":
        raise RuntimeError("category assignment must complete before image generation")
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
    if platform == "wordpress":
        receipt = _publish_wordpress_via_worker(state, profile, public)
    else:
        receipt = _publish_blogger(state, profile, public)
    if not receipt.get("post_id"):
        raise RuntimeError("publisher receipt missing post_id")
    if not receipt.get("url"):
        raise RuntimeError("publisher receipt missing url")
    receipt["verified_at"] = datetime.now(KST).isoformat()
    state = _read_state(run_id)
    state["receipt"] = receipt
    state.setdefault("stage_status", {})["publish"] = "ok"
    state.pop("last_error", None)
    state["completed_at"] = datetime.now(KST).isoformat()
    _write_state(state)
    return {
        "ok": True,
        "stage": "publish",
        "site_id": state["site_id"],
        "run_id": run_id,
        "status": receipt["status"],
        "url": receipt["url"],
        "post_id": receipt["post_id"],
    }

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
