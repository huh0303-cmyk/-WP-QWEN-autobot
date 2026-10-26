from scripts.publish_blogger_33_now import RESULT, load_sites


def test_scope_and_priority_are_locked():
    sites = load_sites()
    assert len(sites) == 33
    assert [site["key"] for site in sites[:2]] == ["kwellness_lab", "kskin365"]
    assert sites[1]["url"] == "https://skin.k-health365.com"


def test_all_targets_are_unique():
    sites = load_sites()
    assert len({site["id"] for site in sites}) == 33
    assert len({site["url"].rstrip("/").lower() for site in sites}) == 33


def test_result_artifact_uses_workflow_artifacts_directory():
    assert RESULT.as_posix().endswith("/artifacts/blogger-33-public-results.json")


def test_daily_blogger_generator_rejects_generic_gerund_title(monkeypatch):
    import json
    from scripts import publish_blogger_33_now as publisher

    body = "<p>" + ("Specific practical information for readers. " * 80) + "</p>"
    payload = {
        "title": "Understanding Korea Rental Deposits",
        "content_html": body,
        "labels": ["Korea", "Rent", "Deposits"],
        "image_subject": "rental contract",
    }
    monkeypatch.setattr(publisher, "blogger_generate_with_fallback", lambda *a, **k: json.dumps(payload))
    site = {
        "key": "test", "url": "https://example.blogspot.com",
        "language": "en", "theme": "Korea rental deposits",
        "persona": "practical editor", "tone": "clear",
    }
    import pytest
    with pytest.raises(RuntimeError, match="title quality gate"):
        publisher.generate(site)


def test_daily_blogger_generator_rejects_ai_body_filler(monkeypatch):
    import json
    from scripts import publish_blogger_33_now as publisher

    body = "<p>In today's fast-paced world, readers need answers. " + ("Specific practical information. " * 80) + "</p>"
    payload = {
        "title": "Korea Rental Deposits: What Tenants Pay",
        "content_html": body,
        "labels": ["Korea", "Rent", "Deposits"],
        "image_subject": "rental contract",
    }
    monkeypatch.setattr(publisher, "blogger_generate_with_fallback", lambda *a, **k: json.dumps(payload))
    site = {
        "key": "test", "url": "https://example.blogspot.com",
        "language": "en", "theme": "Korea rental deposits",
        "persona": "practical editor", "tone": "clear",
    }
    import pytest
    with pytest.raises(RuntimeError, match="body quality gate"):
        publisher.generate(site)
