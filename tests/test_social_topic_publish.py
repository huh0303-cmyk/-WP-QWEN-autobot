import json

from scripts import publish_social_topic_post as publish


def test_save_receipts_keeps_public_url_and_post_id(monkeypatch, tmp_path):
    receipt_path = tmp_path / "social_publication_receipts.json"
    monkeypatch.setattr(publish, "RECEIPTS", receipt_path)

    publish.save_receipts(
        "topic-1",
        [{"platform": "Instagram", "role": "korean_topik", "post_id": "1789", "url": "https://example.test/p/1"}],
    )

    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    row = payload["publications"][0]
    assert row["content_id"] == "topic-1"
    assert row["post_id"] == "1789"
    assert row["url"] == "https://example.test/p/1"
    assert row["published_at"]
