from automation_hub.blogger_topic_router import (
    NoRelatedWordPressSource,
    TopicCandidate,
    rank_topics,
    select_wp_source,
    source_similarity,
)
import automation_hub.blogger_topic_router as router


def _profile(key="korea365", theme="Korea life A-Z", persona="portal editor", categories=None):
    return {
        "site_key": key,
        "wordpress": {
            "url": "https://example.com",
            "theme": theme,
            "persona": persona,
            "categories": categories or [],
        },
        "blogspot": {"persona": persona},
    }


def _row(title, outlet, url, surface="newspaper"):
    return {"title": title, "outlet": outlet, "url": url, "surface": surface}


def test_general_blog_picks_most_repeated_viral_noun_phrase():
    rows = [
        _row("Orion AI chip launch draws global attention", "CNN", "https://cnn.test/1"),
        _row("Orion AI chip launch changes the market", "The New York Times", "https://nyt.test/2"),
        _row("Orion AI chip launch trends in Korea", "Hankyoreh", "https://hani.test/3", "google"),
        _row("Housing loan rules announced", "Outlet A", "https://a.test/4"),
        _row("Housing loan rules explained", "Outlet B", "https://b.test/5"),
    ]
    ranked = rank_topics(rows, profile=_profile(), trend_terms=["Orion AI chip launch"])
    assert ranked
    assert {"ai", "chip"} <= {word.casefold() for word in ranked[0].keyword.split()}
    assert ranked[0].mention_count == 3
    assert ranked[0].viral_score > 0


def test_headline_stop_words_do_not_create_artificial_verb_phrases():
    rows = [
        _row("September plans to change Korea travel insurance", "CNN", "https://cnn.test/1"),
        _row("Korea travel insurance options for visitors", "The New York Times", "https://nyt.test/2"),
    ]
    ranked = rank_topics(rows, profile=_profile("ktrip365", "Travel", "Korea travel planner"))
    assert ranked
    assert ranked[0].keyword.casefold() == "travel insurance"
    assert all("plans to" not in item.keyword.casefold() for item in ranked)


def test_priority_media_registry_includes_requested_us_outlets():
    feed_names = {name for name, _, _ in router.MEDIA_FEEDS}
    assert {"The Washington Post", "Los Angeles Times"} <= feed_names


def test_specialist_profile_filters_more_viral_off_topic_candidate():
    rows = [
        _row("Election debate schedule announced", "CNN", "https://cnn.test/1"),
        _row("Election debate schedule dominates coverage", "NYT", "https://nyt.test/2"),
        _row("Election debate schedule goes viral", "Outlet C", "https://c.test/3"),
        _row("Election debate schedule analysis", "Outlet D", "https://d.test/4"),
        _row("Hanbit semiconductor investment expands", "Chosun Ilbo", "https://chosun.test/5"),
        _row("Hanbit semiconductor investment plan", "Outlet E", "https://e.test/6"),
    ]
    profile = _profile("ktech365", "Technology", "Korean semiconductor and AI editor", ["Semiconductors"])
    ranked = rank_topics(rows, profile=profile, trend_terms=["Election debate schedule"])
    assert ranked
    assert ranked[0].keyword.startswith("Hanbit semiconductor")
    assert all("Election" not in item.keyword for item in ranked)


def test_multi_topic_specialist_is_not_mistaken_for_a_general_blog():
    profile = _profile(
        "koreawedding",
        "International dating, Korean couples, wedding culture, costs, Korean basics, TOPIK, cultural meetups",
        "Korea international-couple and wedding editor",
        ["International Couples", "Wedding Costs", "TOPIK"],
    )
    rows = [
        _row("Election debate schedule announced", "CNN", "https://cnn.test/1"),
        _row("Election debate schedule dominates coverage", "NYT", "https://nyt.test/2"),
        _row("Seoul wedding venue fees rise", "Chosun Ilbo", "https://chosun.test/3"),
        _row("Seoul wedding venue fees compared", "Hankyoreh", "https://hani.test/4"),
    ]
    ranked = rank_topics(rows, profile=profile)
    assert ranked
    assert all("Election" not in item.keyword for item in ranked)
    assert "wedding" in ranked[0].keyword.casefold()


def test_source_router_selects_closest_public_post():
    topic = TopicCandidate(
        keyword="Hanbit semiconductor investment", score=90, mention_count=3,
        outlet_count=3, surface_count=2, viral_score=15,
        evidence_urls=("https://news.test/1",), evidence_text="semiconductor AI chip investment",
    )
    posts = [
        {"status": "publish", "link": "https://example.com/travel", "title": {"rendered": "Spring rail travel guide"}, "excerpt": {"rendered": "Book trains."}},
        {"status": "publish", "link": "https://example.com/chips", "title": {"rendered": "Hanbit semiconductor investment outlook"}, "excerpt": {"rendered": "AI chip capacity and market plans."}},
    ]
    selected = select_wp_source(topic, posts, profile=_profile("ktech365", "Technology"))
    assert selected is not None
    assert selected[0]["link"].endswith("/chips")
    assert selected[1] >= 0.32


def test_source_router_refuses_forced_connection():
    topic = TopicCandidate(
        keyword="Hanbit semiconductor investment", score=90, mention_count=3,
        outlet_count=3, surface_count=2, viral_score=15,
        evidence_urls=("https://news.test/1",), evidence_text="semiconductor technology",
    )
    unrelated = {
        "status": "publish", "link": "https://example.com/wedding",
        "title": {"rendered": "Seoul wedding venue checklist"},
        "excerpt": {"rendered": "Marriage ceremony costs and planning."},
    }
    assert source_similarity(topic, unrelated, profile=_profile("ktech365", "Technology")) == 0
    assert select_wp_source(topic, [unrelated], profile=_profile("ktech365", "Technology")) is None


def test_automatic_route_falls_back_to_independent_article(monkeypatch):
    topic = TopicCandidate(
        keyword="Hanbit semiconductor investment", score=90, mention_count=3,
        outlet_count=3, surface_count=2, viral_score=15,
        evidence_urls=("https://a.test/1", "https://b.test/2"),
        evidence_text="Hanbit semiconductor investment",
        evidence_items=(("A", "Hanbit semiconductor investment", "https://a.test/1"),
                        ("B", "Hanbit semiconductor investment", "https://b.test/2")),
    )
    monkeypatch.setattr(router, "fetch_today_headlines", lambda **kwargs: [])
    monkeypatch.setattr(router, "fetch_profile_headlines", lambda *args, **kwargs: [])
    monkeypatch.setattr(router, "fetch_trending_terms", lambda **kwargs: [])
    monkeypatch.setattr(router, "rank_topics", lambda *args, **kwargs: [topic])
    monkeypatch.setattr(router, "fetch_public_wp_posts", lambda *args, **kwargs: [])
    routed = router.resolve_automatic_source(_profile("ktech365", "Technology"))
    assert routed.result_code == "INDEPENDENT_TREND_ARTICLE"
    assert routed.post is None
    assert routed.source_score is None


def test_queue_keeps_two_gpt_attempts_and_has_no_gemini_route():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "scripts" / "queue_blogger_rewrite.py").read_text(encoding="utf-8")
    assert "for attempt in range(1, 3)" in source
    assert "resolve_automatic_source" in source
    assert "gemini_generate" not in source
