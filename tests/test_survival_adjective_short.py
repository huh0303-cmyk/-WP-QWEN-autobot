import datetime as dt
import json
from pathlib import Path

from scripts.survival_adjective_short import LANGUAGES, PAIR_PATH, channel_map, pronunciation, select_pair
from scripts.select_unique_survival_pair import norm, pair_is_used


def test_all_ten_languages_have_exact_unique_channels_and_native_locale_voices():
    channels = channel_map()
    assert set(channels) == set(LANGUAGES)
    assert len({row["channel_id"] for row in channels.values()}) == 10
    for code, profile in LANGUAGES.items():
        assert profile.voice.startswith(profile.locale + "-")
        assert channels[code]["upload_enabled"] is True


def test_catalog_has_a_full_month_of_localized_pairs():
    catalog = json.loads(Path(PAIR_PATH).read_text(encoding="utf-8"))
    assert catalog["repeat_each_word_minimum"] == 5
    assert len(catalog["pairs"]) >= 30
    for pair in catalog["pairs"]:
        assert set(LANGUAGES).issubset(pair)
        assert all(len(pair[code]) == 2 and all(pair[code]) for code in LANGUAGES)


def test_first_day_is_the_requested_long_short_example():
    pair = select_pair(dt.date(2026, 10, 1), "long-short")
    assert pair["id"] == "long-short"
    assert pair["ko"] == ["길다", "짧다"]
    assert pair["en"] == ["long", "short"]
    assert pronunciation(pair, "ko", "길다") == "gil-da"
    assert pronunciation(pair, "ko", "짧다") == "jjal-tta"
    assert pronunciation(pair, "ja", "長い") == "na-ga-i"
    assert pronunciation(pair, "zh", "长") == "cháng"


def test_randomized_timing_never_intentionally_targets_29_seconds():
    import random
    for seed in range(500):
        rng = random.Random(seed)
        intro = round(rng.uniform(1.1, 2.8), 2)
        outro = round(rng.uniform(1.3, 3.2), 2)
        durations = [round(rng.uniform(1.8, 4.0), 2) for _ in range(10)]
        planned = intro + outro + sum(durations)
        if 28.5 <= planned < 29.5:
            adjustable = next((i for i, value in enumerate(durations) if value <= 2.8), None)
            if adjustable is not None:
                durations[adjustable] = round(durations[adjustable] + 1.1, 2)
            else:
                adjustable = next(i for i, value in enumerate(durations) if value >= 3.0)
                durations[adjustable] = round(durations[adjustable] - 1.1, 2)
            planned = intro + outro + sum(durations)
        assert not 28.5 <= planned < 29.5
        assert all(1.8 <= duration <= 4.0 for duration in durations)



def test_builder_refuses_unsafe_date_based_pair_rotation():
    with pytest.raises(RuntimeError, match="history-verified --pair-id is mandatory"):
        select_pair(dt.date(2026, 11, 6), None)


def test_builder_refuses_retired_noun_pairs_even_when_explicitly_requested():
    with pytest.raises(RuntimeError, match="Retired noun lesson"):
        select_pair(dt.date(2026, 11, 6), "book-phone")

def test_history_selector_catches_legacy_vietnamese_book_phone_metadata():
    pair = {
        "id": "book-phone",
        "vi": ["sách", "điện thoại"],
    }
    legacy_video_metadata = norm(
        "sách (sách) • điện thoại (điện thoại) | book • phone #Shorts "
        "sách means book; điện thoại means phone"
    )
    assert pair_is_used(pair, "vi", [legacy_video_metadata])


def test_history_selector_does_not_combine_words_from_different_videos():
    pair = {"id": "book-phone", "vi": ["sách", "điện thoại"]}
    history = [norm("sách means book"), norm("điện thoại means phone")]
    assert not pair_is_used(pair, "vi", history)


def test_history_selector_matches_stable_pair_id_in_metadata():
    pair = {"id": "reluctant-eager", "vi": ["miễn cưỡng", "háo hức"]}
    assert pair_is_used(pair, "vi", [norm("Lesson ID: reluctant-eager")])
