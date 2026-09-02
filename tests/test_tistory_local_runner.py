import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import tistory_local_runner as runner
import enqueue_tistory_drafts


def test_local_queue_is_idempotent_and_survives_restart(tmp_path):
    path = tmp_path / "queue.sqlite3"
    db = runner.open_queue(path)
    payload = json.dumps({"job_id": "t-1", "site_id": "tistory_health_info"})
    db.execute("INSERT OR IGNORE INTO jobs(job_id,sheet_row,site_id,payload) VALUES(?,?,?,?)", ("t-1", 2, "tistory_health_info", payload)); db.commit(); db.close()
    reopened = runner.open_queue(path)
    reopened.execute("INSERT OR IGNORE INTO jobs(job_id,sheet_row,site_id,payload) VALUES(?,?,?,?)", ("t-1", 2, "tistory_health_info", payload)); reopened.commit()
    assert reopened.execute("SELECT count(*) FROM jobs WHERE job_id='t-1'").fetchone()[0] == 1


def test_draft_from_sheet_is_always_private_and_uses_category_label():
    row = {
        "site_id": "tistory_health_info", "title": "검진 전 확인할 항목",
        "content_html": '<p><img src="x.webp" alt="검진표를 확인하는 사람"></p>' + ("<p>검진 전에 확인할 내용을 설명합니다.</p>" * 10),
        "labels": "건강검진", "search_description": "건강검진 전에 복용약과 금식 시간, 예약기관 안내를 확인하는 순서를 실제 준비 과정에 맞춰 알기 쉽게 정리하고 당일 준비물과 주의사항까지 함께 안내합니다.",
    }
    draft = runner.draft_from_row(row, "https://k-healthcare.tistory.com/")
    assert draft.visibility == "private"
    assert draft.category == "건강검진"
    assert draft.validate() == []


def test_completed_job_is_not_selected_again(tmp_path):
    db = runner.open_queue(tmp_path / "q.sqlite3")
    db.execute("INSERT INTO jobs(job_id,sheet_row,site_id,payload,state) VALUES(?,?,?,?,?)", ("done", 2, "tistory_health_info", "{}", "complete"))
    db.commit()
    assert db.execute("SELECT * FROM jobs WHERE state IN ('pending','retry')").fetchall() == []


def test_only_private_ready_artifacts_enter_sheet_queue():
    payload = {"drafts": [
        {"job_id": "ok", "site_id": "tistory_health_info", "status": "DRAFT_READY", "public_allowed": False, "title": "제목", "body_html": "<p>본문</p>", "category": "건강검진", "meta_description": "설명"},
        {"job_id": "bad", "site_id": "tistory_health_info", "status": "CONSENSUS_FAILED", "public_allowed": False},
    ]}
    rows = enqueue_tistory_drafts.rows_from_artifact(payload)
    assert len(rows) == 1
    header = enqueue_tistory_drafts.PUBLISH_QUEUE_HEADER
    queued = dict(zip(header, rows[0]))
    assert queued["visibility"] == "private"
    assert queued["publish_now"] == "FALSE"
