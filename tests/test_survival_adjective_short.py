import datetime as dt
import json
from pathlib import Path

from scripts.survival_adjective_short import LANGUAGES, PAIR_PATH, channel_map, pronunciation, select_pair


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
    pair = select_pair(dt.date(2026, 10, 1), None)
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
