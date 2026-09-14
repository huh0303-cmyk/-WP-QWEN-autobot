import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def test_every_registered_site_has_square_logo():
    wp = json.loads((ROOT / "config" / "automation_hub_sites.json").read_text(encoding="utf-8"))
    ts = json.loads((ROOT / "config" / "tistory_portfolio.json").read_text(encoding="utf-8"))
    expected = [ROOT / "assets" / "site_logos" / "wordpress" / f"{s['site_id']}.png" for s in wp["sites"] if s.get("platform") == "wordpress"]
    expected += [ROOT / "assets" / "site_logos" / "tistory" / f"{s['site_id']}.png" for s in ts["sites"]]
    assert len(expected) == 32
    for path in expected:
        assert path.exists(), path
        with Image.open(path) as image:
            assert image.size == (512, 512)
            assert image.mode == "RGB"
