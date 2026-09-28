from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

from flask import Flask

from control_center import london_gpt_app
from scripts import london_four_agent_pipeline as pipeline
from scripts.london_site_catalog import content_sites, manual_profile


def test_catalog_contains_verified_platform_destinations():
    sites = content_sites()
    assert Counter(item["platform"] for item in sites) == {
        "wordpress": 27, "blogger": 33, "naver": 3, "tistory": 5,
    }
    assert all(item["enabled"] for item in sites)
    assert [item["url"] for item in sites if item["platform"] == "naver"] == [
        "https://blog.naver.com/huh0303", "https://blog.naver.com/huh3", "https://blog.naver.com/huh4",
    ]
    assert next(item for item in sites if item["site_id"] == "naver_n2")["editor_url"].endswith("huh3?Redirect=Write")
    assert next(item for item in sites if item["site_id"] == "tistory_ktrip365")["editor_url"].endswith("/manage/newpost")
    assert all(not item["auto_publish"] for item in sites if item["platform"] in {"naver", "tistory"})
    assert manual_profile("naver_n2")[0] == "naver"
    assert manual_profile("tistory_ktrip365")[0] == "tistory"


def test_web_app_renders_template_and_guards_manual_platform(monkeypatch, tmp_path):
    monkeypatch.setattr(london_gpt_app, "PIPELINE_DIR", tmp_path)
    runtime = SimpleNamespace(**{name: (lambda: []) for name in (
        "get_site_data", "get_blogger_data", "get_tistory_data", "get_youtube_data", "get_sns_data"
    )})
    app = Flask(__name__, template_folder="../control_center/templates")
    app.add_url_rule("/manifest.webmanifest", "pwa_manifest", lambda: "{}")
    london_gpt_app.install(app, runtime)
    client = app.test_client()
    page = client.get("/london-gpt")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert 'value="blogger_ktrip365"' in html
    assert 'value="naver_n2"' in html
    assert 'value="tistory_ktrip365"' in html
    assert 'id="writerModel"' in html and 'id="imageModel"' in html
    assert 'id="openEditor"' in html
    assert "{{ site." not in html
    assert client.post("/api/london-gpt/run", json={"site_id": "naver_n2", "publish_mode": "publish"}).status_code == 400
    monkeypatch.setattr(london_gpt_app.requests, "post", lambda *a, **kw: SimpleNamespace(status_code=200))
    tistory = client.post("/api/london-gpt/run", json={"site_id": "tistory_ktrip365", "publish_mode": "manual"})
    assert tistory.status_code == 202
    assert london_gpt_app._read_run(tistory.json["run_id"])["platform"] == "tistory"
    blogger = client.post("/api/london-gpt/run", json={"site_id": "blogger_ktrip365", "publish_mode": "draft"})
    assert blogger.status_code == 202
    assert london_gpt_app._read_run(blogger.json["run_id"])["platform"] == "blogger"
    assert london_gpt_app._read_run(blogger.json["run_id"])["writer_model"] == "auto_free"
    assert london_gpt_app._read_run(blogger.json["run_id"])["image_model"] == "auto_free"
    assert client.post("/api/london-gpt/run", json={"site_id": "blogger_ktrip365", "writer_model": "unknown"}).status_code == 400


def test_naver_and_tistory_handoff_never_call_auto_publisher(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "STATE_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "_publish_wordpress_via_worker", lambda *a: (_ for _ in ()).throw(AssertionError("WP publish")))
    monkeypatch.setattr(pipeline, "_publish_blogger", lambda *a: (_ for _ in ()).throw(AssertionError("Blogger publish")))
    for site_id, platform in (("naver_n2", "naver"), ("tistory_ktrip365", "tistory")):
        run_id = "lgpt-20260928-120000-" + ("abcdef" if platform == "naver" else "123456")
        pipeline._write_state({"run_id": run_id, "site_id": site_id, "platform": platform,
                               "publish_mode": "manual", "stage_status": {"research": "ok", "write": "ok", "image": "ok"},
                               "article": {"title": "Test article", "content_html": "<p>Body</p>"}})
        assert pipeline.stage_publish(run_id)["status"] == "manual_required"
