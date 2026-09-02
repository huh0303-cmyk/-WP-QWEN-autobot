import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NEW_IDS = {
    "4456888951628869767",
    "3205814823967421343",
    "2531035487222435079",
    "2234527810530371008",
    "3683978748331752523",
    "8077962392257357260",
}
IMAGE_CHAIN = ["bytedance/sdxl-lightning-4step", "black-forest-labs/flux-schnell"]


def test_all_33_blogspot_cards_are_consistent_and_unique():
    portfolio = json.loads((ROOT / "config/blogger_portfolio.json").read_text(encoding="utf-8"))["channels"]
    rooms = json.loads((ROOT / "config/automation_rooms.json").read_text(encoding="utf-8"))["rooms"]
    bloggers = [room for room in rooms if room["platform"] == "blogger"]
    assert len(portfolio) == len(bloggers) == 33
    assert len({row["blogspot"].rstrip("/").lower() for row in portfolio}) == 33
    assert len({row["destination_id"] for row in portfolio}) == 33
    assert NEW_IDS <= {row["destination_id"] for row in portfolio}


def test_six_new_cards_use_requested_models_and_remain_drafts():
    rooms = json.loads((ROOT / "config/automation_rooms.json").read_text(encoding="utf-8"))["rooms"]
    added = [room for room in rooms if room.get("destination_id") in NEW_IDS]
    assert len(added) == 6
    assert all(room["text_model"] == "gpt-5-mini" for room in added)
    assert all(room["image_models"] == IMAGE_CHAIN for room in added)
    assert all(room["publish_policy"] == "draft" for room in added)


def test_kworld_kpop_is_distinct_from_existing_kworld_seoul():
    portfolio = json.loads((ROOT / "config/blogger_portfolio.json").read_text(encoding="utf-8"))["channels"]
    urls = {row["blogspot"] for row in portfolio}
    assert "https://kworld365.blogspot.com" in urls
    assert "https://kworld365seoul.blogspot.com" in urls
