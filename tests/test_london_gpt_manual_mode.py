from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from flask import Flask

from control_center import london_gpt_app
from scripts import london_four_agent_pipeline as pipeline


ROOT = Path(__file__).resolve().parents[1]


def _app(monkeypatch, tmp_path):
    monkeypatch.setattr(london_gpt_app, "PIPELINE_DIR", tmp_path)
    monkeypatch.setattr(london_gpt_app, "_content_sites", lambda: [{
        "site_id": "wp_test", "url": "https://example.com", "categories": ["Health"],
    }])
    runtime = SimpleNamespace(**{name: (lambda: []) for name in (
        "get_site_data", "get_blogger_data", "get_tistory_data", "get_youtube_data", "get_sns_data"
    )})
    app = Flask(__name__, template_folder="../control_center/templates")
    london_gpt_app.install(app, runtime)
    return app.test_client()


def test_manual_pipeline_never_calls_publisher(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "STATE_DIR", tmp_path)
    run_id = "lgpt-20260928-120000-abcdef"
    pipeline._write_state({
        "run_id": run_id, "site_id": "wp_test", "publish_mode": "manual",
        "stage_status": {"research": "ok", "write": "ok", "image": "ok", "publish": "waiting"},
        "article": {"title": "Test title", "content_html": "<p>Test body</p>"},
    })
    monkeypatch.setattr(pipeline, "_publish_wordpress_via_worker", lambda *a: (_ for _ in ()).throw(AssertionError("published")))
    monkeypatch.setattr(pipeline, "_publish_blogger", lambda *a: (_ for _ in ()).throw(AssertionError("published")))
    result = pipeline.stage_publish(run_id)
    state = pipeline._read_state(run_id)
    assert result["status"] == "manual_required"
    assert state["stage_status"]["publish"] == "manual_required"
    assert "receipt" not in state


def test_manual_url_verification(monkeypatch, tmp_path):
    client = _app(monkeypatch, tmp_path)
    run_id = "lgpt-20260928-120000-abcdef"
    state = {"run_id": run_id, "site_id": "wp_test", "publish_mode": "manual",
             "stage_status": {"research": "ok", "write": "ok", "image": "ok", "publish": "manual_required"},
             "article": {"title": "Test title", "content_html": "<p>Test body</p>"}}
    london_gpt_app._write_run(state)
    assert client.post("/api/london-gpt/manual-published", json={"run_id": run_id, "url": "https://other.com/post/"}).status_code == 400
    monkeypatch.setattr(london_gpt_app.requests, "get", lambda *a, **kw: SimpleNamespace(
        status_code=200, headers={"content-type": "text/html"}, text="<h1>Test title</h1>"))
    result = client.post("/api/london-gpt/manual-published", json={"run_id": run_id, "url": "https://example.com/post/"})
    assert result.status_code == 200
    assert london_gpt_app._read_run(run_id)["stage_status"]["publish"] == "ok"


def test_manual_run_and_publish_rerun_guard(monkeypatch, tmp_path):
    client = _app(monkeypatch, tmp_path)
    monkeypatch.setattr(london_gpt_app.requests, "post", lambda *a, **kw: SimpleNamespace(status_code=200))
    response = client.post("/api/london-gpt/run", json={"site_id": "wp_test", "category": "Health", "publish_mode": "manual"})
    assert response.status_code == 202
    run_id = response.json["run_id"]
    assert london_gpt_app._read_run(run_id)["publish_mode"] == "manual"
    assert client.post("/api/london-gpt/rerun/publish", json={"run_id": run_id}).status_code == 409


def test_image_clipboard_endpoint_reads_only_trusted_run_image(monkeypatch, tmp_path):
    client = _app(monkeypatch, tmp_path)
    run_id = "lgpt-20260928-120000-abcdef"
    london_gpt_app._write_run({"run_id": run_id, "image": {"url": "https://raw.githubusercontent.com/example/photo.webp"}})
    class FakeResponse:
        status_code = 200
        headers = {"content-type": "image/webp"}
        def iter_content(self, size): return iter([b"RIFFimage"])
        def __enter__(self): return self
        def __exit__(self, *args): return None
    monkeypatch.setattr(london_gpt_app.requests, "get", lambda *a, **kw: FakeResponse())
    copied = client.get(f"/api/london-gpt/image/{run_id}")
    assert copied.status_code == 200 and copied.data == b"RIFFimage"
    london_gpt_app._write_run({"run_id": run_id, "image": {"url": "http://127.0.0.1/private"}})
    assert client.get(f"/api/london-gpt/image/{run_id}").status_code == 404


def test_medical_auto_run_hands_off_before_publication(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "STATE_DIR", tmp_path)
    run_id = "lgpt-20260928-120000-abcdef"
    pipeline._write_state({"run_id": run_id, "site_id": "blogger_koreanews", "platform": "blogger",
                           "publish_mode": "publish", "research": {"keyword": "코로나 백신 접종 현황"},
                           "stage_status": {"research": "ok", "write": "ok", "image": "ok"},
                           "article": {"title": "Test", "content_html": "<p>Test</p>"}})
    monkeypatch.setattr(pipeline, "_publish_blogger", lambda *args: (_ for _ in ()).throw(AssertionError("published")))
    result = pipeline.stage_publish(run_id)
    state = pipeline._read_state(run_id)
    assert result["status"] == "manual_required"
    assert state["publish_mode"] == "manual" and "receipt" not in state


def test_manual_copy_package_contains_complete_seo_fields_and_login_notice():
    template = (ROOT / "control_center" / "templates" / "london_gpt.html").read_text(encoding="utf-8")
    for value in ("focusKeyword", "tags", "alt"):
        assert f"data-copy=\"{value}\"" in template
    assert "검색설명/메타 설명" in template
    assert "키워드·태그" in template
    assert "이미지 ALT" in template
    assert "네이버·티스토리는 먼저 해당 계정에 로그인해야 합니다" in template
