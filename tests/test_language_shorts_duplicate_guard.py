from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "publish_survival_adjective_shorts.py"


def load_duplicate_helpers():
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    names = {"normalized_title", "assert_no_recent_duplicate"}
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in selected} == names
    namespace = {
        "json": json,
        "recent_channel_videos": lambda service, channel_id: service,
        "RuntimeError": RuntimeError,
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


def test_publisher_source_parses_as_valid_python():
    ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("LONG vs SHORT #Shorts", "long vs short"),
        ("Long—vs Short!!!", "long vs short"),
        ("Ｃａｆｅ MOZART", "cafe mozart"),
    ],
)
def test_title_normalization_is_stable(value, expected):
    helpers = load_duplicate_helpers()
    assert helpers["normalized_title"](value) == expected


def test_existing_same_title_blocks_duplicate():
    helpers = load_duplicate_helpers()
    videos = [{
        "id": "existing12345",
        "snippet": {"title": "Long vs Short #Shorts", "publishedAt": "2026-10-25T10:00:00Z"},
        "statistics": {"viewCount": "12"},
        "status": {"privacyStatus": "public"},
    }]
    with pytest.raises(RuntimeError, match="Duplicate upload blocked"):
        helpers["assert_no_recent_duplicate"](videos, {"title": "LONG vs SHORT", "words": []}, "channel123")


def test_matching_word_pair_blocks_duplicate_but_substrings_do_not():
    helpers = load_duplicate_helpers()
    duplicate = [{
        "id": "existing12345",
        "snippet": {"title": "Long vs Short | Listen and Repeat", "publishedAt": "2026-10-25T10:00:00Z"},
        "statistics": {"viewCount": "12"},
        "status": {"privacyStatus": "public"},
    }]
    with pytest.raises(RuntimeError, match="Duplicate upload blocked"):
        helpers["assert_no_recent_duplicate"](duplicate, {"title": "A new title", "words": ["long", "short"]}, "channel123")

    non_duplicate = [{
        "id": "existing54321",
        "snippet": {"title": "Longer and Shortcut", "publishedAt": "2026-10-25T10:00:00Z"},
        "statistics": {"viewCount": "12"},
        "status": {"privacyStatus": "public"},
    }]
    helpers["assert_no_recent_duplicate"](non_duplicate, {"title": "A new title", "words": ["long", "short"]}, "channel123")
