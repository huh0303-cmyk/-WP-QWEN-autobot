from automation_hub.golden_keyword_mentions import parse_mention_rows, rank_mentioned_keywords


CATEGORIES = ["Travel", "Health"]


TODAY = "2026-09-03"


def _row(keyword, noun, surface, outlet, url, published_on=TODAY):
    return f"{keyword}\tTravel\t{noun}\t{surface}\t{outlet}\t{published_on}\t{url}"


def test_cross_surface_nouns_rank_ahead_of_raw_single_surface_volume():
    text = "\n".join(
        [
            _row("Busan rail pass guide", "Busan rail pass", "newspaper", "A", "https://a.test/1"),
            _row("Busan rail pass guide", "Busan Rail Pass", "naver", "B", "https://b.test/2"),
            _row("Busan rail pass guide", "Busan rail-pass", "google", "C", "https://c.test/3"),
            _row("Jeju festival dates", "Jeju festival", "newspaper", "D", "https://d.test/1"),
            _row("Jeju festival dates", "Jeju festival", "media", "E", "https://e.test/2"),
            _row("Single source hype", "Single source hype", "media", "F", "https://f.test/1"),
            _row("Single source hype", "Single source hype", "media", "G", "https://g.test/2"),
            _row("Single source hype", "Single source hype", "media", "H", "https://h.test/3"),
            _row("Single source hype", "Single source hype", "media", "I", "https://i.test/4"),
        ]
    )
    ranked = rank_mentioned_keywords(parse_mention_rows(text, CATEGORIES, observed_on=TODAY))
    assert [item[0] for item in ranked] == ["Busan rail pass guide", "Jeju festival dates"]
    assert ranked[0][2] == {"surface_count": 3, "outlet_count": 3, "mention_count": 3}


def test_duplicate_url_is_counted_once_and_bad_rows_are_rejected():
    valid = _row("Busan pass price", "Busan pass", "google", "A", "https://a.test/1")
    text = "\n".join(
        [
            valid,
            valid,
            _row("Busan pass price", "Busan pass", "naver", "B", "https://b.test/2"),
            "bad\tTravel\tnoun\tunknown\toutlet\thttps://bad.test/1",
            "bad\tTravel\tnoun\tmedia\toutlet\tnot-a-url",
            _row("Old item", "Old item", "media", "Old", "https://old.test/1", "2026-09-02"),
        ]
    )
    ranked = rank_mentioned_keywords(parse_mention_rows(text, CATEGORIES, observed_on=TODAY))
    assert len(ranked) == 1
    assert ranked[0][2]["mention_count"] == 2


def test_total_mentions_are_the_primary_sort_order():
    text = "\n".join(
        [
            _row("Frequent noun guide", "Frequent noun", "newspaper", "A", "https://a.test/f1"),
            _row("Frequent noun guide", "Frequent noun", "naver", "B", "https://b.test/f2"),
            _row("Frequent noun guide", "Frequent noun", "naver", "C", "https://c.test/f3"),
            _row("Frequent noun guide", "Frequent noun", "media", "D", "https://d.test/f4"),
            _row("Broad noun guide", "Broad noun", "newspaper", "A", "https://a.test/b1"),
            _row("Broad noun guide", "Broad noun", "naver", "B", "https://b.test/b2"),
            _row("Broad noun guide", "Broad noun", "google", "C", "https://c.test/b3"),
        ]
    )
    ranked = rank_mentioned_keywords(parse_mention_rows(text, CATEGORIES, observed_on=TODAY))
    assert [item[0] for item in ranked] == ["Frequent noun guide", "Broad noun guide"]
