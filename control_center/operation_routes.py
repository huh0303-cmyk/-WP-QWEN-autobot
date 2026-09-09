import csv
import hmac
import io
import json
import os
import re
import time
from functools import lru_cache
from pathlib import Path

import requests
from flask import flash, jsonify, redirect, request

from .operation_gateway import GitHubGateway
from .operations import Conflict, Store, Worker
from .rss_watch import RSSWatcher
from automation_hub.sheet_schema import PUBLISH_QUEUE_HEADER


def install(module):
    app = module.app
    root = Path(module.__file__).resolve().parents[1]
    store = Store(os.environ.get("CONTROL_OPERATIONS_DB", str(root / "data/control-operations.sqlite3")))
    # The fallback must be the SAME for every VPS process and after restart.
    app.config["SECRET_KEY"] = os.environ.get("CONTROL_CENTER_SECRET_KEY") or store.secret("session")
    app.config["CONTROL_CENTER_CSRF"] = os.environ.get("CONTROL_CENTER_CSRF") or store.secret("csrf")

    @lru_cache(maxsize=1)
    def queue_rows(bucket):
        response = requests.get(module.REVIEW_QUEUE_CSV, timeout=12)
        response.raise_for_status()
        return [dict(zip(PUBLISH_QUEUE_HEADER, row)) for row in list(csv.reader(io.StringIO(response.text)))[1:]]

    gateway = GitHubGateway(os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-WP-QWEN-autobot"),
                            os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip(), lambda: queue_rows(int(time.time() // 15)))
    worker = Worker(store, gateway)
    app.extensions["operations"] = {"store": store, "worker": worker, "gateway": gateway}

    def targets(group, site_id):
        if group in {"wp25", "news2"} or group.startswith("wp_"):
            # Request acceptance must not wait for 81 visitor/category HTTP
            # requests used to render the dashboard metrics.
            sites = [dict(site_id=s.site_id, domain=s.url.removeprefix("https://").removeprefix("http://"),
                          cadence=module.wordpress_cadence(s)) for s in module.load_wordpress_sites()]
            if group.startswith("wp_"):
                sites = [s for s in sites if s["site_id"] == site_id]
            else:
                sites = [s for s in sites if (s["cadence"]["kind"] == "newsroom") == (group == "news2")]
            result = []
            for site in sites:
                news = site["cadence"]["kind"] == "newsroom"
                inputs = {"newsroom": site["domain"].split(".")[0], "preferred_category": ""} if news else {
                    "target_site_url": "https://" + site["domain"], "publication_approved": "true", "room_id": group}
                result.append(dict(site_id=site["site_id"], site_group="wp_" + site["site_id"], site_url="https://" + site["domain"], label=site["domain"],
                                   platform="news" if news else "wordpress", workflow="newsrooms-daily-publisher.yml" if news else "daily-network-publish.yml", inputs=inputs))
            return result
        if group == "blogspot33" or group.startswith("blogspot_"):
            sites = module.get_blogger_data()
            sites = [s for s in sites if s["connected"] and (group == "blogspot33" or s["site_id"] == site_id)]
            result = []
            for site in sites:
                workflow, inputs = module._build_draft_workflow_call({"platform": "blogger", "selection_mode": "auto", "site_id": site["site_id"], "keyword": "", "jitter_max_seconds": "60" if group == "blogspot33" else "0"})
                result.append(dict(site_id=site["site_id"], site_group="blogspot_" + site["site_id"], site_url=site["url"], label=site["name"], platform="blogger", workflow=workflow, inputs=inputs))
            return result
        sites = [dict(s, name=s["title"]) for s in json.loads((root / "config/tistory_portfolio.json").read_text(encoding="utf-8"))["sites"] if s.get("launch_enabled")]
        return [dict(site_id=s["site_id"], site_group="tistory_" + s["site_id"], site_url=s["url"], label=s["name"], platform="tistory",
                     workflow="tistory-daily-plan.yml", inputs={"site_ids": s["site_id"]}) for s in sites if group == "tistory5" or s["site_id"] == site_id]

    def reply(payload, code):
        if request.accept_mimetypes.best == "application/json":
            return jsonify(payload), code
        flash({"text": payload.get("message", "요청 접수"), "target": payload.get("target", "operation-summary")}, "success" if code < 300 else "error")
        return redirect("/#" + payload.get("target", "operation-summary"))

    rss = RSSWatcher(store, root / "config/newsroom_rss_watch.json", lambda: targets("news2", ""))
    app.extensions["operations"]["rss"] = rss
    imported_history = False

    def discover_news():
        nonlocal imported_history
        rss.scan()
        if imported_history:
            return
        try:
            listing = gateway.get("/actions/workflows/newsrooms-daily-publisher.yml/runs?event=schedule&per_page=8")
            sites = {s["label"].split(".")[0]: s for s in targets("news2", "")}
            for run in listing.get("workflow_runs", []):
                match = re.match(r"newsroom:(koreanews365|theseouljournal)\b", run.get("display_title", ""))
                key = match.group(1) if match else None
                if not key and run.get("status") == "completed":
                    # Older runs did not name the selected newsroom. Use the
                    # exact run's artifact name, never guess from its timestamp.
                    artifacts = gateway.get(f"/actions/runs/{run['id']}/artifacts?per_page=100")
                    keys = {k for k in sites if any(a["name"].startswith("newsroom-result-" + k + "-") for a in artifacts.get("artifacts", []))}
                    if len(keys) == 1:
                        key = keys.pop()
                if key in sites:
                    store.observe_run(sites[key], run)
            imported_history = True
        except Exception:
            raise

    worker.discover = discover_news

    @app.before_request
    def tracked_publication_request():
        if request.method != "POST":
            return None
        names = {"/trigger/wp-single": "wp_", "/trigger/blogspot-single": "blogspot_", "/trigger/tistory-single": "tistory_"}
        site_id = request.form.get("site_id", "").strip()
        group = names[request.path] + site_id if request.path in names else request.path.removeprefix("/trigger/publish-group/")
        if request.path not in names and not (request.path.startswith("/trigger/publish-group/") and group in {"wp25", "news2", "blogspot33", "tistory5"}):
            return None
        target = "bulk-status-" + group
        if not hmac.compare_digest(request.form.get("csrf_token", ""), app.config["CONTROL_CENTER_CSRF"]):
            return reply({"message": "요청이 접수되지 않았습니다. 화면을 새로고침한 뒤 다시 눌러주세요.", "target": target}, 403)
        if not os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip():
            return reply({"message": "실행 서버 연결이 설정되지 않아 요청을 접수하지 않았습니다.", "target": target}, 503)
        try:
            descriptors = targets(group, site_id)
            if not descriptors:
                raise ValueError("등록된 실행 대상이 없습니다.")
            request_id = request.form.get("operation_request_id") or module.secrets.token_hex(16)
            if not re.fullmatch(r"[a-zA-Z0-9-]{16,80}", request_id):
                raise ValueError("요청 번호 형식이 올바르지 않습니다.")
            store.submit(group, descriptors, request_id)
        except Conflict as exc:
            return reply({"message": str(exc), "target": target}, 409)
        except (ValueError, RuntimeError) as exc:
            return reply({"message": str(exc), "target": target}, 422)
        worker.start()
        return reply({"accepted": True, "request_id": request_id, "group": group, "target": target,
                      "message": f"{descriptors[0]['label'] if len(descriptors) == 1 else str(len(descriptors)) + '개 사이트'} 요청을 접수했습니다. 작업 상태에서 진행 상황을 확인하세요."}, 202)

    @app.get("/api/operations")
    def operation_status():
        if os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip():
            worker.start()
        return jsonify(jobs=store.snapshot(), server_time=time.time(), automatic_news=rss.status())

    return worker
