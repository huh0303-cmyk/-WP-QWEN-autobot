"""Identity guard for interactive channel OAuth renewal."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reauthorize_youtube_channel import MASTER, PROFILES, _require_exact_channel
import json


def test_exact_channel_is_required():
    expected = "UCexpected"
    _require_exact_channel([{"id": expected}], expected)
    for items in ([], [{"id": "UCwrong"}],
                  [{"id": expected}, {"id": "UCother"}]):
        with pytest.raises(RuntimeError, match="nothing stored"):
            _require_exact_channel(items, expected)


def test_every_locked_channel_has_a_distinct_oauth_profile():
    groups = json.loads(MASTER.read_text(encoding="utf-8"))["groups"]
    keys = {row["key"] for rows in groups.values() for row in rows}
    assert len(keys) == 23
    assert keys == set(PROFILES)
    assert len(set(PROFILES.values())) == 23
