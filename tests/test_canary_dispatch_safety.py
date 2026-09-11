from automation_hub.canary_dispatch import choose_canaries


def test_wordpress_public_approval_forced_false():
    items = [{
        "room_id": "wp_test", "platform": "wordpress", "workflow": "daily-network-publish.yml",
        "publish_policy": "draft", "inputs": {"publication_approved": True, "target_site_url": "https://example.com"},
    }]
    chosen = choose_canaries(items, {"wordpress"})
    assert chosen[0]["inputs"]["publication_approved"] is False


def test_youtube_schedule_and_public_flags_are_blocked():
    items = [{
        "room_id": "yt_test", "platform": "youtube", "workflow": "generate-youtube-playlist.yml",
        "publish_policy": "private",
        "inputs": {"channel": "kpop", "publish_delay_hours": "6", "public": True, "publishAt": "2030-01-01T00:00:00Z"},
    }]
    chosen = choose_canaries(items, {"youtube"})
    assert len(chosen) == 1
    inputs = chosen[0]["inputs"]
    assert inputs["public"] is False
    assert inputs["publish_delay_hours"] == ""
    assert inputs["publishAt"] == ""


def test_policy_mismatch_is_not_selected():
    items = [{
        "room_id": "yt_bad", "platform": "youtube", "workflow": "generate-youtube-playlist.yml",
        "publish_policy": "draft", "inputs": {"channel": "kpop"},
    }]
    assert choose_canaries(items, {"youtube"}) == []
