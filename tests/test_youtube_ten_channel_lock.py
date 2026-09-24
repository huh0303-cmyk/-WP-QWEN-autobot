import json
from pathlib import Path


def test_youtube_ten_channel_lock_is_complete_and_nonpublishing():
    data = json.loads(Path("config/youtube-ten-channel-lock.json").read_text(encoding="utf-8"))
    rows = data["groups"]["playlist"] + data["groups"]["knowledge"]
    assert len(data["groups"]["playlist"]) == 5
    assert len(data["groups"]["knowledge"]) == 5
    assert [row["order"] for row in rows] == list(range(1, 11))
    assert len({row["channel_id"] for row in rows}) == 10
    assert data["identity_rule"] == "channel_id_is_authoritative"
    assert data["reauthorization_rule"].startswith("do_not_ask_again")
    assert data["publication_rule"] == "no_automatic_upload_or_publication"
