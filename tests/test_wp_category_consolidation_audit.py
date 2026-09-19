import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import wp_category_consolidation_audit as m  # noqa: E402


def test_denylist_blocks_protected_sites():
    assert "koreanews365.com" in m.DENYLIST
    assert "theseouljournal.com" in m.DENYLIST


def test_classify_home():
    assert m.classify_url("https://jobkorea365.com/", "jobkorea365.com", set()) == "HOME"


def test_classify_pagination():
    assert m.classify_url("https://jobkorea365.com/page/4/", "jobkorea365.com", set()) == "PAGINATION"


def test_classify_category_tag_author():
    assert m.classify_url("https://x.com/category/jobs/", "x.com", set()) == "CATEGORY"
    assert m.classify_url("https://x.com/tag/visa/", "x.com", set()) == "TAG"
    assert m.classify_url("https://x.com/author/admin/", "x.com", set()) == "AUTHOR"


def test_classify_archive():
    assert m.classify_url("https://x.com/2026/08/", "x.com", set()) == "ARCHIVE"
    assert m.classify_url("https://x.com/2026/", "x.com", set()) == "ARCHIVE"


def test_classify_page_from_known_slug():
    slugs = {"contact", "privacy-policy"}
    assert m.classify_url("https://x.com/contact/", "x.com", slugs) == "PAGE"


def test_classify_post_default():
    assert m.classify_url(
        "https://jobkorea365.com/how-korea-work-permit-process-actually-works/",
        "jobkorea365.com", set(),
    ) == "POST"


def test_gsc_snapshot_has_exactly_32_jobkorea365_rows():
    rows = m.load_gsc_rows("jobkorea365.com")
    assert len(rows) == 32


def test_recommend_category_reuses_existing_job_category():
    categories = [
        {"id": 5, "name": "Jobs", "slug": "jobs", "count": 20},
        {"id": 1, "name": "Uncategorized", "slug": "uncategorized", "count": 2},
    ]
    rec = m.recommend_category(categories, "Korea Jobs")
    assert rec["action"] == "KEEP_EXISTING"
    assert rec["slug"] == "jobs"


def test_recommend_category_would_create_when_nothing_fits():
    categories = [{"id": 1, "name": "Uncategorized", "slug": "uncategorized", "count": 2}]
    rec = m.recommend_category(categories, "Korea Jobs")
    assert rec["action"] == "WOULD_CREATE_NEW"
    assert rec["id"] is None
