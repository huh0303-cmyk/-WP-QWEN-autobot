from pathlib import Path


PIPELINE = Path("scripts/seoul_journal_shorts_pipeline.py")
PUBLIC_WORKFLOW = Path(".github/workflows/seoul-journal-randomized-shorts.yml")
PRIVATE_WORKFLOW = Path(".github/workflows/seoul-journal-political-shorts.yml")
BENCHMARKS = Path("config/seoul_journal_thumbnail_benchmarks.json")


def source():
    return PIPELINE.read_text(encoding="utf-8")


def test_final_poll_is_inside_the_narration_duration():
    text = source()
    assert "60초 상한을 두지 말고" in text
    assert "segment = (duration - poll_seconds) / len(unique)" in text
    assert "frames.append((poll_frame,poll_seconds))" in text
    assert 'for frame,hold_seconds in frames:' in text
    assert '"댓글로 A·B·C를 눌러 참여하세요"' in text


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


def test_public_release_requires_explicit_owner_approval():
    workflow = PUBLIC_WORKFLOW.read_text(encoding="utf-8")
    assert "schedule:" not in workflow
    assert "confirm_public_release_after_owner_review" in workflow
    assert "inputs.confirm_public_release_after_owner_review == true" in workflow


def test_private_schedule_is_three_review_uploads_per_day():
    workflow = PRIVATE_WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count('cron:') == 3
    assert "Confirm upload will be PRIVATE only" in workflow


def test_thumbnail_contract_uses_three_inspected_500k_examples():
    import json
    data = json.loads(BENCHMARKS.read_text(encoding="utf-8"))
    assert data["minimum_views"] >= 500_000
    assert len(data["examples"]) >= 3
    assert len({row["channel"] for row in data["examples"]}) >= 3
    assert all(row["observed_views"] >= 500_000 for row in data["examples"])
    assert all(row["visual_observation"] for row in data["examples"])
    assert len(data["common_traits"]) >= 5


def test_pipeline_fails_closed_without_fresh_benchmark_receipt():
    text = source()
    assert "load_thumbnail_benchmark_contract" in text
    assert "age>30" in text
    assert "thumbnail-benchmark-receipt.json" in text
    assert "thumbnail=True" in text

