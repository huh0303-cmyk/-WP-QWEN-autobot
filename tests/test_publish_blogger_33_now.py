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
