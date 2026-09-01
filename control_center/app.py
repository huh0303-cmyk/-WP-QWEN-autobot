from __future__ import annotations

import hmac
import os
import secrets

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from .registry import load_wordpress_sites
from .service import ControlCenter
from .wordpress import credential_health


def create_app(*, testing: bool = False, db_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("CONTROL_CENTER_SESSION_KEY") or secrets.token_hex(32),
        CONTROL_CENTER_CSRF=os.environ.get("CONTROL_CENTER_CSRF") or secrets.token_urlsafe(24),
        TESTING=testing,
    )
    if db_path:
        os.environ["CONTROL_CENTER_DB"] = db_path
    center = ControlCenter()

    def check_csrf() -> None:
        supplied = request.form.get("csrf", "")
        if not hmac.compare_digest(supplied, app.config["CONTROL_CENTER_CSRF"]):
            abort(403)

    @app.context_processor
    def globals_for_templates():
        return {"csrf": app.config["CONTROL_CENTER_CSRF"]}

    @app.get("/")
    def index():
        sites = load_wordpress_sites()
        health = {site.site_id: credential_health(site) for site in sites}
        return render_template("index.html", sites=sites, health=health, jobs=center.store.list_jobs())

    @app.post("/jobs")
    def create_job():
        check_csrf()
        try:
            job = center.create(request.form.get("site_id", ""), request.form.get("keyword", ""))
            flash("작업을 생성했습니다. 동일 사이트·키워드는 기존 작업을 재사용합니다.", "success")
            return redirect(url_for("job_detail", job_id=job["id"]))
        except Exception as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))

    @app.get("/jobs/<job_id>")
    def job_detail(job_id: str):
        try:
            job = center.store.get(job_id)
        except KeyError:
            abort(404)
        return render_template("job.html", job=job, site=center.sites[job["site_id"]])

    def action(job_id: str, name: str):
        check_csrf()
        try:
            result = getattr(center, name)(job_id)
            flash(f"{name} 작업 완료: {result['state']}", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("job_detail", job_id=job_id))

    @app.post("/jobs/<job_id>/generate")
    def generate(job_id: str):
        return action(job_id, "generate")

    @app.post("/jobs/<job_id>/draft")
    def draft(job_id: str):
        return action(job_id, "draft")

    @app.post("/jobs/<job_id>/approve")
    def approve(job_id: str):
        return action(job_id, "approve")

    @app.post("/jobs/<job_id>/reject")
    def reject(job_id: str):
        return action(job_id, "reject")

    return app


def main() -> None:
    app = create_app()
    port = int(os.environ.get("CONTROL_CENTER_PORT", "8766"))
    print(f"Korea 365 WordPress Control Center: http://127.0.0.1:{port}")
    from waitress import serve
    serve(app, host="127.0.0.1", port=port, threads=4)


if __name__ == "__main__":
    main()
