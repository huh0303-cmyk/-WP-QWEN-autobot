from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from scripts.apply_naver_trend_overrides import apply_overrides


def _plan():
    return {
        "date": "2026-10-01",
        "jobs": [
            {
                "job_id": "naver_n1:2026-10-01:1",
                "site_id": "naver_n1",
                "scheduled_local_time": "09:19",
                "base_query": "old",
                "catalog_keyword_id": "old-id",
                "status": "RESEARCH_REQUIRED",
                "research": {"naver_datalab": "https://datalab.naver.com"},
            }
        ],
    }


def _brief(status="READY_FOR_OFFICIAL_SOURCE_RECHECK"):
    return {
        "date": "2026-10-01",
        "status": "COMPLETE",
        "generated_at": "2026-10-01T07:11:38+09:00",
        "candidates": [
            {
                "rank": 16,
                "query": "2026 청년내일저축계좌 최종 선정 이후 해야 할 일",
                "cluster": "국가지원금·자산형성",
                "site_ids": ["naver_n1"],
                "signal": "fresh official release",
                "official_sources": ["https://example.gov"],
                "status": status,
            }
        ],
        "recommended_plan_overrides": {"naver_n1": [16]},
    }


def test_applies_candidate_without_changing_job_identity_or_time():
    plan, changed = apply_overrides(
        _plan(),
        _brief(),
        datetime(2026, 10, 1, 8, 7, tzinfo=ZoneInfo("Asia/Seoul")),
    )
    job = plan["jobs"][0]
    assert changed == 1
    assert job["job_id"] == "naver_n1:2026-10-01:1"
    assert job["scheduled_local_time"] == "09:19"
    assert job["base_query"].startswith("2026 청년내일저축계좌")
    assert job["trend_candidate_rank"] == 16
    assert job["research"]["official_sources"] == ["https://example.gov"]
    assert job["research"]["naver_datalab"] == "https://datalab.naver.com"
    assert "catalog_keyword_id" not in job
    assert plan["trend_override_count"] == 1


@pytest.mark.parametrize("status", ["HOLD_UNTIL_SOURCE", "LOW_RELEVANCE_DO_NOT_PROMOTE_TODAY"])
def test_rejects_blocked_candidate(status):
    with pytest.raises(ValueError, match="blocked"):
        apply_overrides(_plan(), _brief(status))


def test_second_application_is_idempotent_for_jobs():
    applied_at = datetime(2026, 10, 1, 8, 7, tzinfo=ZoneInfo("Asia/Seoul"))
    first, first_changed = apply_overrides(_plan(), _brief(), applied_at)
    second, second_changed = apply_overrides(deepcopy(first), _brief(), applied_at)
    assert first_changed == 1
    assert second_changed == 0
    assert second == first
