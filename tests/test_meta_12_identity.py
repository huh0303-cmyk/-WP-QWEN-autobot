import pytest
from scripts.meta_12_identity import validated_user_id, test_already_attempted as attempted


@pytest.mark.parametrize("platform,payload", [
    ("instagram", {"user_id": "123", "username": "seoul_jisoo1"}),
    ("threads", {"id": "123", "username": "Seoul_Jisoo1"}),
])
def test_authenticated_handle_resolves_optional_id(platform, payload):
    assert validated_user_id(platform, payload, "@seoul_jisoo1") == "123"


@pytest.mark.parametrize("payload,configured", [
    ({"id": "123", "username": "japanese_sos1"}, ""),
    ({"id": "123", "username": "seoul_jisoo1"}, "999"),
    ({"id": "", "username": "seoul_jisoo1"}, ""),
    ({"id": "not-an-id", "username": "seoul_jisoo1"}, ""),
])
def test_wrong_account_id_and_invalid_responses_are_blocked(payload, configured):
    with pytest.raises(ValueError, match="identity mismatch"):
        validated_user_id("threads", payload, "seoul_jisoo1", configured)


@pytest.mark.parametrize("row", [
    {"test_attempted_at_kst": "2026-11-25T12:00:00+09:00"},
    {"test_attempted_at": "legacy-reservation"},
    {"test_status": "ATTEMPT_RESERVED"},
    {"test_status": "NEEDS_RECONCILIATION"},
    {"test_public_url": "https://www.threads.com/@example/post/test"},
])
def test_reserved_and_uncertain_tests_are_never_repeated(row):
    assert attempted(row)


def test_unattempted_target_is_eligible():
    assert not attempted({"identity_verified": False, "test_public_url": ""})


def test_preflight_checks_all_handles_without_configured_ids(monkeypatch, tmp_path):
    import importlib
    import json
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    preflight = importlib.import_module("meta_12_preflight")
    responses = {}
    for index, account in enumerate(preflight.POLICY["accounts"]):
        for platform in preflight.POLICY["platforms"]:
            prefix = f"META_{platform.upper()}_{account['key'].upper()}"
            token = "FAKE_SECRET_" + prefix
            monkeypatch.setenv(prefix + "_ACCESS_TOKEN", token)
            monkeypatch.delenv(prefix + "_USER_ID", raising=False)
            field = "user_id" if platform == "instagram" else "id"
            responses[token] = {field: str(1000 + index), "username": account[platform]}
    monkeypatch.setattr(preflight, "get_json", lambda url, token: (200, responses[token]))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    report_path = tmp_path / "report.json"
    monkeypatch.setenv("REPORT_PATH", str(report_path))
    preflight.main()
    report = json.loads(report_path.read_text())
    assert report["identity_verified_count"] == 12
    assert report["publication_attempted"] is False
    assert all(row["resolved_user_id"].isdigit() for row in report["targets"])
    assert "FAKE_SECRET" not in report_path.read_text()


def test_single_publisher_never_calls_api_for_reserved_attempt(monkeypatch, tmp_path):
    import importlib
    import json
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    single = importlib.import_module("meta_12_single_test_publish")
    readiness = tmp_path / "readiness.json"
    readiness.write_text(json.dumps({"targets": [{"platform": "threads",
        "account_key": "seoul_jisoo1", "test_attempted_at_kst": "reserved"}]}))
    monkeypatch.setattr(single, "READINESS", readiness)
    monkeypatch.setenv("PUBLISH_PLATFORM", "threads")
    monkeypatch.setenv("PUBLISH_ACCOUNT", "seoul_jisoo1")
    def unexpected_api(*args, **kwargs):
        pytest.fail("A reserved attempt must not make any Meta API call")
    monkeypatch.setattr(single, "api", unexpected_api)
    single.main()
