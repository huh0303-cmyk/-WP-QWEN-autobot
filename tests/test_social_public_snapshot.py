from __future__ import annotations

import json

from scripts import social_public_snapshot as snapshot


def test_duration_seconds_parses_video_runtime():
    assert snapshot.duration_seconds("PT32S") == 32
    assert snapshot.duration_seconds("PT1M23S") == 83
    assert snapshot.duration_seconds("PT1H2M3S") == 3723


def test_youtube_latest_item_includes_title_url_publish_time_and_duration(monkeypatch):
    def fake_get_json(url, *, params=None, **kwargs):
        if url.endswith("/youtube/v3/channels"):
            return {
                "items": [{
                    "id": "UC-test",
                    "snippet": {"title": "Test channel", "publishedAt": "2025-01-01T00:00:00Z"},
                    "statistics": {"subscriberCount": "10", "viewCount": "500", "videoCount": "2"},
                    "contentDetails": {"relatedPlaylists": {"uploads": "PL-test"}},
                }]
            }
        if url.endswith("/youtube/v3/playlistItems"):
            return {
                "items": [{
                    "snippet": {
                        "title": "Latest published title",
                        "publishedAt": "2026-11-14T02:00:00Z",
                        "resourceId": {"videoId": "video-123"},
                    },
                    "contentDetails": {"videoId": "video-123", "videoPublishedAt": "2026-11-14T02:00:00Z"},
                }]
            }
        if url.endswith("/youtube/v3/videos"):
            return {
                "items": [{
                    "id": "video-123",
                    "snippet": {
                        "title": "Latest published title",
                        "description": "A test description",
                        "publishedAt": "2026-11-14T02:00:00Z",
                    },
                    "contentDetails": {"duration": "PT1M23S"},
                    "statistics": {"viewCount": "42", "likeCount": "3", "commentCount": "1"},
                }]
            }
        raise AssertionError(url)

    monkeypatch.setattr(snapshot, "get_json", fake_get_json)
    result = snapshot.fetch_youtube([{
        "platform": "YouTube",
        "handle": "test_channel",
        "url": "https://www.youtube.com/channel/UC-test",
    }], "test-api-key")
    row = result["youtube|test_channel"]
    assert row["latest_content_title"] == "Latest published title"
    assert row["latest_content_url"] == "https://www.youtube.com/watch?v=video-123"
    assert row["latest_content_published_at"] == "2026-11-14T02:00:00Z"
    assert row["latest_content_duration_seconds"] == 83
    assert row["latest_content_text_length"] == len("A test description")


def test_receipt_metadata_uses_latest_verified_social_post_and_spec(monkeypatch, tmp_path):
    data = tmp_path / "data"
    specs = data / "social_publication_specs"
    specs.mkdir(parents=True)
    (data / "social_publication_receipts.json").write_text(json.dumps({
        "publications": [{
            "platform": "Instagram",
            "role": "korean_topik",
            "handle": "sis_topik1",
            "content_id": "2026-11-14-topik",
            "url": "https://www.instagram.com/p/example/",
            "published_at": "2026-11-14T10:00:00+09:00",
        }]
    }), encoding="utf-8")
    (specs / "2026-11-14-topik.json").write_text(json.dumps({
        "content_id": "2026-11-14-topik",
        "text_engine": "Gemini 3.5 Flash Lite",
        "image_engine": "Pexels",
        "instagram": {"caption": "오늘의 한국어 표현\n예문과 설명"}
    }), encoding="utf-8")
    (data / "social_content_evidence.json").write_text(json.dumps({"accounts": {}}), encoding="utf-8")
    monkeypatch.setattr(snapshot, "ROOT", tmp_path)
    row = snapshot.receipt_metadata({
        "platform": "Instagram",
        "handle": "sis_topik1",
        "name": "Seoul TOPIK",
    })
    assert row["latest_content_title"] == "오늘의 한국어 표현"
    assert row["latest_content_url"] == "https://www.instagram.com/p/example/"
    assert row["latest_content_published_at"] == "2026-11-14T10:00:00+09:00"
    assert row["latest_content_text_length"] == len("오늘의 한국어 표현\n예문과 설명")
    assert row["latest_text_engine"] == "Gemini 3.5 Flash Lite"
    assert row["latest_image_engine"] == "Pexels"
