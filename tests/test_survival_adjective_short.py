import datetime as dt
import json
from pathlib import Path

from scripts.survival_adjective_short import LANGUAGES, PAIR_PATH, channel_map, select_pair


def test_all_ten_languages_have_exact_unique_channels_and_native_locale_voices():
    channels = channel_map()
    assert set(channels) == set(LANGUAGES)
    assert len({row["channel_id"] for row in channels.values()}) == 10
    for code, profile in LANGUAGES.items():
        assert profile.voice.startswith(profile.locale + "-")
        assert channels[code]["upload_enabled"] is True


def test_catalog_has_a_full_month_of_localized_pairs():
    catalog = json.loads(Path(PAIR_PATH).read_text(encoding="utf-8"))
    assert catalog["repeat_each_word_minimum"] >= 5
    assert len(catalog["pairs"]) >= 30
    for pair in catalog["pairs"]:
        assert set(LANGUAGES).issubset(pair)
        assert all(len(pair[code]) == 2 and all(pair[code]) for code in LANGUAGES)


def test_first_day_is_the_requested_long_short_example():
    pair = select_pair(dt.date(2026, 10, 1), None)
    assert pair["id"] == "long-short"
    assert pair["ko"] == ["길다", "짧다"]
    assert pair["en"] == ["long", "short"]
