"""Identity guard for interactive channel OAuth renewal."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reauthorize_youtube_channel import _require_exact_channel


def test_exact_channel_is_required():
    expected = "UCexpected"
    _require_exact_channel([{"id": expected}], expected)
    for items in ([], [{"id": "UCwrong"}],
                  [{"id": expected}, {"id": "UCother"}]):
        with pytest.raises(RuntimeError, match="nothing stored"):
            _require_exact_channel(items, expected)
