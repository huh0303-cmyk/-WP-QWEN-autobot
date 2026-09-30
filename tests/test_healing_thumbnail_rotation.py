import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location("healing_motion_test", ROOT / "scripts" / "healing_motion.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_selection_avoids_three_recent_sources(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    module = load_module()
    pool = module.SOURCE_POOLS["rain"]
    history = [{"mode": "rain", "source_id": source_id} for source_id in pool[:3]]
    assert module.select_source("rain", 0, history) == pool[3]


def test_thumbnail_frame_is_not_reused_for_same_source(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    module = load_module()
    history = [{"source_id": 7351460, "thumbnail_second": 2}]
    assert module.select_thumbnail_second(7351460, 12, 0, history) != 2


def test_thumbnail_history_is_bounded_and_atomic(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    module = load_module()
    path = tmp_path / "history.json"
    for index in range(module.HISTORY_LIMIT + 3):
        module.record_thumbnail(path, {"source_id": index, "thumbnail_second": 2})
    rows = module._read_history(path)
    assert len(rows) == module.HISTORY_LIMIT
    assert rows[0]["source_id"] == 3
