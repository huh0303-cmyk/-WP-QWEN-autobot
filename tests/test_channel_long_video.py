import datetime as dt, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import channel_long_video as C


def good(lang="en", n=10, per=60):
    word = "word " if lang == "en" else "あ"
    nar = (word * per) if lang == "en" else (word * per * 2)
    return {"title": "A calm look at fish oil", "scenes": [{"narration": nar, "visual": "fish oil capsules"} for _ in range(n)]}


def test_catalogs_consistent():
    cat = json.loads((ROOT / "config/korea_travel_catalog.json").read_text(encoding="utf-8"))
    for t in cat["topics"]:
        for hid in t.get("items", []):
            assert hid in cat["hotels"]
    topics = json.loads((ROOT / "config/senior_health_topics.json").read_text(encoding="utf-8"))["topics"]
    assert len({t["key"] for t in topics}) == len(topics) >= 40
    assert all(t["en"] and t["ja"] for t in topics)


def test_topic_rotation_daily_and_distinct_per_channel():
    d0 = dt.date(2026, 10, 6)
    keys = [C.load_topic("health_usa", d0 + dt.timedelta(days=i))["key"] for i in range(50)]
    assert len(set(keys)) == 50
    assert C.load_topic("health_usa", d0)["key"] != C.load_topic("health_japan", d0)["key"]


def test_health_gate_blocks_claims_and_dosage():
    d = good(per=60)
    assert C.validate_script(d, "health_usa") == []
    d["scenes"][0]["narration"] += " This miracle supplement cures arthritis."
    assert any("banned" in p for p in C.validate_script(d, "health_usa"))
    d = good(per=60)
    d["scenes"][1]["narration"] += " Take 500 mg daily."
    assert "dosage number" in C.validate_script(d, "health_usa")
    j = good("ja", per=60)
    j["scenes"][0]["narration"] += "必ず効きます。"
    assert any("banned" in p for p in C.validate_script(j, "health_japan"))


def test_shopping_gate_blocks_prices():
    d = good(per=60)
    d["scenes"][0]["narration"] += " Rooms start at $120 a night."
    assert "price/rating claim" in C.validate_script(d, "shopping")


def test_length_window():
    assert any("length" in p for p in C.validate_script(good(per=20), "health_usa"))


def test_srt_covers_scenes_and_wraps():
    texts = ["First sentence here. Second sentence follows right after it, a bit longer than the first.", "あいうえお、かきくけこ。さしすせそたちつてと、なにぬねの。"]
    srt = C.make_srt(texts[:1], [8.0], "en")
    assert "00:00:00,150" in srt and srt.count("-->") >= 2
    assert all(len(line) <= 40 for line in srt.splitlines() if "-->" not in line and not line.isdigit() and line)
    ja = C.make_srt(texts[1:], [8.0], "ja")
    assert all(len(line) <= 20 for line in ja.splitlines() if "-->" not in line and not line.isdigit() and line)


def test_links_use_affiliate_only_when_configured(monkeypatch):
    topic = next(t for t in json.loads((ROOT / "config/korea_travel_catalog.json").read_text(encoding="utf-8"))["topics"] if t["key"] == "seoul_midrange")
    monkeypatch.delenv("BOOKING_AID", raising=False)
    assert all("aid=" not in u for _, u in C.shopping_links(topic))
    monkeypatch.setenv("BOOKING_AID", "123")
    assert any("aid=123" in u for _, u in C.shopping_links(topic))
