from scripts.site_health_guardian import (
    robots_blocks_all, has_noindex, duplicate_title_groups, count_locs, severity)


def test_robots_blocks_all_only_for_wildcard_agent():
    assert robots_blocks_all("User-agent: *\nDisallow: /")
    assert not robots_blocks_all("User-agent: *\nDisallow: /wp-admin/\nAllow: /")
    assert not robots_blocks_all("User-agent: BadBot\nDisallow: /\nUser-agent: *\nAllow: /")


def test_has_noindex_meta_and_header():
    assert has_noindex('<meta name="robots" content="noindex, follow">')
    assert has_noindex("<html></html>", "noindex")
    assert not has_noindex('<meta name="robots" content="index, follow">')


def test_duplicate_titles_normalised():
    groups = duplicate_title_groups(["A  b", "a b", "c"])
    assert groups == {"a b": 2}


def test_count_locs_and_severity():
    assert count_locs("<loc>x</loc><loc>y</loc>") == 2
    assert severity({"issues": []}) == "ok"
    assert severity({"issues": ["warn:x"]}) == "warn"
    assert severity({"issues": ["warn:x", "critical:y"]}) == "critical"
