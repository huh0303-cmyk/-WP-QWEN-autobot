# Tistory 5-site local registrar

The cloud workflow creates validated drafts and appends them to the Google
Sheet tab `자동화_발행대기`. The local registrar is the only component that
touches Tistory's browser editor. It can save **private** posts only.

## One-time setup

```powershell
pip install playwright google-api-python-client google-auth
python -m playwright install chromium
python scripts/setup_google_sheets_local.py
python scripts/tistory_local_runner.py login
```

Finish Kakao/Tistory login in the opened persistent browser and press Enter.

## Run pending jobs

```powershell
python scripts/tistory_local_runner.py run --max-jobs 5 --gap-seconds 600
```

`SHEET_ID` must identify the control spreadsheet. Pending commands are copied
to `.local/tistory-queue.sqlite3` before browser work. A PC shutdown, editor
failure, or temporary Sheets outage therefore leaves the job available for a
safe retry. Completed `job_id` values are never selected again.

```powershell
python scripts/tistory_local_runner.py status
```

Success means the private post was reopened and verified. The administrator
edit URL is written back to the same Sheet row and emailed when Gmail
credentials are configured. Public publication remains a manual owner action.
