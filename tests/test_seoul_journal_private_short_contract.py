from pathlib import Path


PIPELINE = Path("scripts/seoul_journal_shorts_pipeline.py")
PUBLIC_WORKFLOW = Path(".github/workflows/seoul-journal-randomized-shorts.yml")
PRIVATE_WORKFLOW = Path(".github/workflows/seoul-journal-political-shorts.yml")
BENCHMARKS = Path("config/seoul_journal_thumbnail_benchmarks.json")
VIDEO_SOURCES = Path("config/seoul_journal_reusable_video_sources.json")


def source():
    return PIPELINE.read_text(encoding="utf-8")


def test_final_poll_starts_after_narration_and_holds_six_seconds():
    text = source()
    assert "60초 상한을 두지 말고" in text
    assert "poll_seconds = 6.0" in text
    assert "frames.append((poll_frame,poll_seconds))" in text
    assert 'for frame,hold_seconds in frames:' in text
    assert '"댓글로 A·B·C를 눌러 참여하세요"' in text
    assert "next_start=active_cues[idx+1]" in text
    assert "else duration" in text
    assert "apad=pad_dur=" in text
    assert '"poll_starts_after_narration_seconds":round(duration,3)' in text
    assert 'proof_at=max(0.0,final_duration-1.5)' in text
    assert '"poll-proof.jpg"' in text
    assert 'if mean_difference>18' in text


def test_support_account_is_secret_driven_on_every_video_frame():
    text = source()
    workflow = PRIVATE_WORKFLOW.read_text(encoding="utf-8")
    assert 'os.getenv("SEOUL_JOURNAL_SUPPORT_LINE","").strip()' in text
    assert "secrets.SEOUL_JOURNAL_SUPPORT_LINE" in workflow
    assert "for name in GEMINI_API_KEY FISH_AUDIO_API_KEY SEOUL_JOURNAL_SUPPORT_LINE" in workflow
    assert "자율구독 전체 계좌 표시가 없어 생성·비공개 업로드를 중단합니다." in text
    assert "352-2371" not in text
    assert '"support_line_present":bool' in text
    assert "if support_line and not thumbnail" in text
    assert "https://control.korea365.org/seoul-journal-support/?account=" in text


def test_final_poll_is_story_specific_with_three_choices():
    text = source()
    assert '"poll_question":"15~28자 중립 질문"' in text
    assert '"poll_options":[' in text
    assert 'zip("ABC",choices)' in text
    assert 'poll_question=meta["poll_question"]' in text
    assert 'poll_options=meta["poll_options"]' in text
    assert 'choices=list(poll_options or [])' in text


def test_private_upload_sets_thumbnail_and_reads_back_identity():
    text = source()
    assert "yt.thumbnails().set" in text
    assert 'actual_privacy!="private"' in text
    assert "actual_channel!=expected" in text
    assert '"thumbnail_status":thumbnail_status' in text
    assert 'thumbnail_status!="api_set"' in text
    assert 'duration!="P0D"' in text


def test_visuals_require_reusable_principal_figure_photos():
    text = source()
    assert "PRIORITY_FIGURES" in text
    assert "LicenseShortName" in text
    assert "RIGHTS_CLEARED_POLITICIAN_PHOTOS" in text
    assert "photo-sources.json" in text


def test_legacy_public_workflow_has_no_separate_schedule():
    workflow = PUBLIC_WORKFLOW.read_text(encoding="utf-8")
    assert "schedule:" not in workflow
    assert "confirm_public_release_after_owner_review" in workflow
    assert "inputs.confirm_public_release_after_owner_review == true" in workflow


def test_private_schedule_is_three_review_uploads_per_day():
    workflow = PRIVATE_WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count('cron:') == 3
    assert "publish_after_validation" in workflow
    assert "github.event_name == 'schedule'" in workflow


def test_thumbnail_contract_uses_three_inspected_500k_examples():
    import json
    data = json.loads(BENCHMARKS.read_text(encoding="utf-8"))
    assert data["minimum_views"] >= 500_000
    assert len(data["examples"]) >= 3
    assert len({row["channel"] for row in data["examples"]}) >= 3
    assert all(row["observed_views"] >= 500_000 for row in data["examples"])
    assert all(row["visual_observation"] for row in data["examples"])
    assert len(data["common_traits"]) >= 5
    assert len(data["examples"]) >= 6
    assert sum(row["channel"] == "KNN NEWS" for row in data["examples"]) >= 3


def test_reusable_video_sources_fail_closed_on_item_level_license():
    import json
    data = json.loads(VIDEO_SOURCES.read_text(encoding="utf-8"))
    names = {row["name"] for row in data["sources"]}
    assert "공공누리 영상 원문" in names
    assert "KTV 국민방송" in names
    assert "e영상역사관 / KTV 나누리" in names
    assert any("exact video page/file displays KOGL Type 1" in row["rule"] for row in data["sources"])
    assert any("Archive access or download availability is not a reuse license" in row["rule"] for row in data["sources"])
    assert "clip_start_seconds" in data["required_receipt_fields"]
    assert "transcript_excerpt" in data["required_receipt_fields"]


def test_pipeline_fails_closed_without_fresh_benchmark_receipt():
    text = source()
    assert "load_thumbnail_benchmark_contract" in text
    assert "age>30" in text
    assert "thumbnail-benchmark-receipt.json" in text
    assert "thumbnail=True" in text


def test_no_face_covering_black_boxes_and_full_narration_subtitles():
    text = source()
    assert "def build_caption_cues" in text
    assert 'cues=build_caption_cues(OUT/"tts-timeline.json")' in text
    assert "source=unique[photo_mapping[idx]]" in text
    assert "fill=(0,0,0,170)" not in text
    assert "fill=(0,0,0,205)" not in text
    assert "No black panel or bar may cover the face" in text


def test_ffmpeg_motion_is_applied_but_final_poll_stays_readable():
    text = source()
    assert "zoompan=z='min(zoom+0.00012,1.04)'" in text
    assert "if i < len(frames)-1" in text
    assert "Keep the final poll steady for legibility" in text
    assert "poll=True" in text
    assert "poll_question=poll_question,poll_options=poll_options" in text
    assert "render-receipt.json" in text
    assert '"motion_effect":"ffmpeg zoompan Ken Burns on narration scenes"' in text


def test_description_is_compact_and_scheduled_release_is_validated_first():
    text = source()
    assert "def compact_photo_credits" in text
    assert 'split("[원문 기사]",1)[0]' in text
    assert 'description=support_intro+summary[:700]+"\\n\\n원문: "+source_url' in text
    assert "seoul-journal-support/?account=" in text
    assert "credits.append(f\"자료사진" not in text
    assert 'AUTO_PUBLIC_AFTER_VALIDATION' in text
    assert 'privacyStatus":"public"' in text
    assert 'thumbnail_status!="api_set"' in text


def test_non_photo_commons_assets_are_rejected():
    text = source()
    assert '"signature","logo","flag","map","diagram","coat of arms"' in text
    assert 'mime in ("image/svg+xml","image/gif")' in text


def test_seoul_journal_channel_id_is_canonical_not_secret_controlled():
    text = source()
    workflow = PRIVATE_WORKFLOW.read_text(encoding="utf-8")
    channel_id = "UChRUdHZlXSjftAqBtdDNEWA"
    assert f'CANONICAL_SEOUL_JOURNAL_CHANNEL_ID="{channel_id}"' in text
    assert f"EXPECTED_CHANNEL_ID: {channel_id}" in workflow
    assert f"SEOUL_JOURNAL_YOUTUBE_CHANNEL_ID: {channel_id}" in workflow
    assert "secrets.SEOUL_JOURNAL_YOUTUBE_CHANNEL_ID" not in workflow


def test_schedules_stop_before_generation_until_thumbnail_api_is_verified():
    workflow = PRIVATE_WORKFLOW.read_text(encoding="utf-8")
    assert "vars.SEOUL_JOURNAL_THUMBNAIL_API_READY" in workflow
    assert 'github.event_name }}" = "schedule"' in workflow
    assert 'THUMBNAIL_API_READY" != "true"' in workflow
    assert "Scheduled public release is blocked" in workflow


def test_tts_timestamps_drive_fast_synchronized_subtitles():
    text = source()
    assert "/v1/tts/stream/with-timestamp" in text
    assert 'boundary="WordBoundary"' in text
    assert '"type"]=="WordBoundary"' in text
    assert "ko-KR-HyunsuMultilingualNeural" in text
    assert "ko-KR-HyunsuNeural" not in text
    assert "ko-KR-BongJinNeural" not in text
    assert "max_seconds=2.8" in text
    assert "atempo=1.2" not in text
    assert 'subtitle_timing_source":"TTS word/phrase timestamps"' in text
    assert "Subtitle display duration out of sync" in text


def test_photos_are_semantically_planned_not_round_robin():
    text = source()
    assert "def plan_visual_sequence" in text
    assert "단순 0,1,2 순환은 금지합니다" in text
    assert "photo_mapping=plan_visual_sequence" in text
    assert "source=unique[photo_mapping[idx]]" in text
    assert "source=unique[idx % len(unique)]" not in text
    assert "confidence<0.65" in text
    assert "visual-plan.json" in text


def test_manual_verify_only_can_render_without_upload():
    text = source()
    workflow = PRIVATE_WORKFLOW.read_text(encoding="utf-8")
    assert "verify_only:" in workflow
    assert "VERIFY_ONLY: ${{ inputs.verify_only }}" in workflow
    assert 'os.getenv("VERIFY_ONLY","")' in text
    assert '"upload_skipped":True' in text

