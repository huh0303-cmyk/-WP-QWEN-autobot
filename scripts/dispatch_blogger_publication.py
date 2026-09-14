"""Preserve the exact child run receipt before the authoring workflow exits."""
import json
import os
from pathlib import Path

import requests


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    response = requests.post(
        f"https://api.github.com/repos/{repo}/actions/workflows/platform-publish-v2.yml/dispatches",
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2026-03-10"},
        json={"ref": "main", "return_run_details": True,
              "inputs": {"platform": "blogger", "job_id": os.environ["QUEUED_JOB_ID"], "max_jobs": "1"}},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data.get("workflow_run_id"), int):
        raise RuntimeError("Publication dispatch returned no exact run ID; do not dispatch again blindly")
    data.update(parent_run_id=os.environ["GITHUB_RUN_ID"], job_id=os.environ["QUEUED_JOB_ID"], site_id=os.environ["BLOGGER_SITE_ID"])
    output = Path("artifacts/control-handoff.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"Publication run: {data['workflow_run_id']}")


if __name__ == "__main__":
    main()
