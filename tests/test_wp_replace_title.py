from pathlib import Path


def test_emergency_title_repair_preserves_everything_except_title():
    source = (Path(__file__).resolve().parents[1] / "scripts/wp_replace_title.py").read_text(encoding="utf-8")
    assert 'json={"title": new_title}' in source
    assert '"content"' not in source
    assert '"status"' not in source.split("requests.post", 1)[1].split("timeout=30", 1)[0]
    assert '"slug"' not in source.split("requests.post", 1)[1].split("timeout=30", 1)[0]
