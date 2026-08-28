"""2026-08-28 사용자 지시: 플리 채널 영상 제작 전면 정지.

youtube_playlist_maker_legacy.main()은 PLAYLIST_VIDEO_GENERATION_ENABLED가
정확히 "true"가 아니면 그 무엇도 하지 않고 즉시 리턴해야 한다 — 트리거 방식
(수동 workflow_dispatch, 예약 실행, API 호출 등)과 무관하게.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import youtube_playlist_maker_legacy as legacy


def test_main_is_a_no_op_when_flag_is_unset():
    env = {k: v for k, v in os.environ.items() if k != "PLAYLIST_VIDEO_GENERATION_ENABLED"}
    with patch.dict(os.environ, env, clear=True), \
         patch.object(legacy, "GOOGLE_OAUTH_CLIENT_ID", "should-never-be-checked"):
        result = legacy.main()
    assert result is None  # early return, never reaches the missing-credentials check


def test_main_is_a_no_op_when_flag_is_explicitly_false():
    with patch.dict(os.environ, {"PLAYLIST_VIDEO_GENERATION_ENABLED": "false"}):
        result = legacy.main()
    assert result is None


def test_main_proceeds_past_the_freeze_only_when_flag_is_true():
    # Once past the freeze it hits the real credential check next — confirm
    # we got that far (SystemExit from missing creds) rather than the
    # freeze's silent `return None`.
    with patch.dict(os.environ, {"PLAYLIST_VIDEO_GENERATION_ENABLED": "true"}), \
         patch.object(legacy, "GOOGLE_OAUTH_CLIENT_ID", ""), \
         patch.object(legacy, "GOOGLE_OAUTH_CLIENT_SECRET", ""), \
         patch.object(legacy, "GOOGLE_OAUTH_REFRESH_TOKEN", ""):
        try:
            legacy.main()
            assert False, "expected SystemExit from missing credentials past the freeze"
        except SystemExit:
            pass


def test_workflow_does_not_set_the_flag_to_true():
    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" /
                "generate-youtube-playlist.yml").read_text(encoding="utf-8")
    assert "PLAYLIST_VIDEO_GENERATION_ENABLED" not in workflow
