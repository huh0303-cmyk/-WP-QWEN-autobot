import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import restore_khealth_public as restore

FAKE_POSTS = {
    "private": [{"id": 1, "link": "https://k-health365.com/a/", "status": "private", "title": {}}],
    "pending": [{"id": 2, "link": "https://k-health365.com/b/", "status": "pending", "title": {}}],
    "draft": [{"id": 3, "link": "https://k-health365.com/c/", "status": "draft", "title": {}}],
}


def _fake_fetch(status):
    return FAKE_POSTS.get(status, [])


def test_default_run_is_dry_run_and_never_calls_the_publish_endpoint():
    with patch.object(restore, "PASSWORD", "x"), \
         patch.object(restore, "fetch_hidden_posts", side_effect=_fake_fetch), \
         patch.object(restore, "restore_post") as post_call:
        report = restore.run(apply_changes=False)
    post_call.assert_not_called()
    assert report["apply_changes"] is False
    assert report["total_found"] == 3
    assert all(r["action"] == "WOULD_PUBLISH" for r in report["results"])


def test_pending_status_is_included_not_just_private_and_draft():
    # The original version of this script only checked private/draft and
    # missed every "pending" post — regression guard for that gap.
    assert "pending" in restore.HIDDEN_STATUSES
    with patch.object(restore, "PASSWORD", "x"), \
         patch.object(restore, "fetch_hidden_posts", side_effect=_fake_fetch):
        report = restore.run(apply_changes=False)
    statuses_seen = {r["status"] for r in report["results"]}
    assert "pending" in statuses_seen


def test_apply_changes_true_actually_calls_restore_post_for_every_item():
    with patch.object(restore, "PASSWORD", "x"), \
         patch.object(restore, "fetch_hidden_posts", side_effect=_fake_fetch), \
         patch.object(restore, "restore_post", return_value=(True, 200)) as post_call:
        report = restore.run(apply_changes=True)
    assert post_call.call_count == 3
    assert all(r["action"] == "PUBLISHED" for r in report["results"])


def test_failed_publish_call_is_reported_not_hidden():
    with patch.object(restore, "PASSWORD", "x"), \
         patch.object(restore, "fetch_hidden_posts", side_effect=_fake_fetch), \
         patch.object(restore, "restore_post", return_value=(False, 500)):
        report = restore.run(apply_changes=True)
    assert all(r["action"] == "FAILED" for r in report["results"])


def test_restore_post_retries_transient_connection_errors_instead_of_dying():
    # The real run hit RemoteDisconnected on the very first post and the
    # whole 307-post batch died with it. restore_post must retry instead.
    import requests

    with patch.object(restore, "PASSWORD", "x"), \
         patch("restore_khealth_public.time.sleep"), \
         patch("restore_khealth_public.requests.post", side_effect=[
             requests.exceptions.ConnectionError("boom"),
             requests.exceptions.ConnectionError("boom"),
             type("R", (), {"status_code": 200})(),
         ]) as post_call:
        ok, code = restore.restore_post(1)
    assert ok is True
    assert code == 200
    assert post_call.call_count == 3


def test_restore_post_gives_up_after_max_retries():
    import requests

    with patch.object(restore, "PASSWORD", "x"), \
         patch("restore_khealth_public.time.sleep"), \
         patch("restore_khealth_public.requests.post", side_effect=requests.exceptions.ConnectionError("boom")):
        ok, code = restore.restore_post(1, max_retries=3)
    assert ok is False
    assert code == -1


def test_script_never_issues_a_delete_request():
    source = Path(restore.__file__).read_text(encoding="utf-8")
    assert "requests.delete" not in source
    assert "force=true" not in source.lower()
