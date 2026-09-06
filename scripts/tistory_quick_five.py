#!/usr/bin/env python3
"""CEO's one-click "5개 지금 발행" button (Option 2).

Click once: finds today's golden keyword for each of the 5 Tistory sites,
writes all 5 as private drafts in the real Tistory editor (uses the local
login session), then stops - the CEO sets each post's own reserved/
staggered publish time by hand in Tistory and clicks publish there.

Requires: a GitHub token in GH_TOKEN or CONTROL_CENTER_GITHUB_TOKEN (same
one the control room uses), and a Tistory login already done once via
`python scripts/tistory_local_runner.py login`.

Usage: python scripts/tistory_quick_five.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

import requests

REPO = os.environ.get("GITHUB_REPOSITORY", "huh0303-cmyk/-WP-QWEN-autobot")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "")


def dispatch_generation() -> None:
    if not TOKEN:
        raise SystemExit(
            "GH_TOKEN (또는 CONTROL_CENTER_GITHUB_TOKEN) 환경변수가 필요합니다.\n"
            "Windows: setx GH_TOKEN \"ghp_...\" 로 한 번 등록해두면 다음부터 자동으로 읽습니다."
        )
    print("1/3 오늘의 황금키워드로 5개 사이트 글 생성 요청 중...")
    response = requests.post(
        f"https://api.github.com/repos/{REPO}/actions/workflows/tistory-daily-plan.yml/dispatches",
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {TOKEN}"},
        json={"ref": "main", "inputs": {"site_ids": "", "run_key": f"quick5-{int(time.time())}"}},
        timeout=30,
    )
    if response.status_code != 204:
        raise SystemExit(f"생성 요청 실패: HTTP {response.status_code} {response.text[:200]}")


def wait_for_generation(timeout_seconds: int = 900) -> None:
    print("2/3 생성이 끝날 때까지 기다리는 중 (최대 15분)...")
    deadline = time.time() + timeout_seconds
    dispatched_at = time.time()
    run_id = None
    while time.time() < deadline:
        time.sleep(10)
        runs = requests.get(
            f"https://api.github.com/repos/{REPO}/actions/workflows/tistory-daily-plan.yml/runs",
            headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {TOKEN}"},
            params={"event": "workflow_dispatch", "per_page": 5}, timeout=15,
        ).json().get("workflow_runs", [])
        if run_id is None:
            candidates = [r for r in runs if r["created_at"] >= time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(dispatched_at - 15))]
            if candidates:
                run_id = candidates[0]["id"]
                print(f"   실행 확인됨: {candidates[0]['html_url']}")
            continue
        current = next((r for r in runs if r["id"] == run_id), None)
        if current and current["status"] == "completed":
            print(f"   생성 완료 ({current['conclusion']})")
            return
    print("   시간 초과 - 그래도 지금까지 큐에 쌓인 것만 마저 처리합니다.")


def run_local_registrar() -> None:
    print("3/3 실제 Tistory 편집기에 비공개 초안으로 써넣는 중 (브라우저 창이 뜹니다)...")
    subprocess.run(
        [sys.executable, "scripts/tistory_local_runner.py", "run",
         "--max-jobs", "5", "--gap-seconds", "20", "--force-private"],
        check=True,
    )
    print("\n완료! Tistory 관리자 페이지에서 각 글을 열어 예약 발행 시간을 직접 설정하고 발행 버튼을 눌러주세요.")


def main() -> int:
    dispatch_generation()
    wait_for_generation()
    run_local_registrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
