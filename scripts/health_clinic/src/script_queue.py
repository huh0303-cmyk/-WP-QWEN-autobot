"""
미리 써둔 대본들을 날짜 순서로 구글 드라이브에 올리고,
파이프라인이 "다음 순서" 대본을 하나씩 꺼내 쓸 수 있게 관리하는 모듈.

구조 (Drive):
  HealthClinic_Queue/
    manifest.csv          ← 발행 순서/상태 관리 (ready → used)
    KR/  2026-07-26_D01_당뇨_초기신호.txt ...
    EN/  ...
    JP/  ...

로컬 scripts_batch/ 폴더 구조를 그대로 미러링해서 올립니다.
"""
import csv
import io
import os

from config import DRIVE_FOLDER_ID
from src.drive_utils import get_drive_service, get_or_create_folder, upload_file

LOCAL_BATCH_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts_batch")
MANIFEST_NAME = "manifest.csv"


def _find_file_id(service, name: str, parent_id: str) -> str | None:
    query = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def get_queue_root(service) -> str:
    return get_or_create_folder(service, "HealthClinic_Queue", DRIVE_FOLDER_ID)


def upload_batch():
    """scripts_batch/ 안의 manifest.csv + 언어별 대본 파일을 Drive HealthClinic_Queue/ 에 업로드."""
    service = get_drive_service()
    queue_root = get_queue_root(service)

    # manifest.csv 업로드 (이미 있으면 갱신)
    manifest_local = os.path.join(LOCAL_BATCH_DIR, MANIFEST_NAME)
    existing_id = _find_file_id(service, MANIFEST_NAME, queue_root)
    if existing_id:
        from googleapiclient.http import MediaFileUpload
        service.files().update(fileId=existing_id, media_body=MediaFileUpload(manifest_local)).execute()
        print(f"[Queue] manifest.csv 갱신 완료")
    else:
        upload_file(manifest_local, queue_root, MANIFEST_NAME)

    # 언어별 대본 파일 업로드 (PENDING_WRITE 는 건너뜀)
    with open(manifest_local, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        if row["status"] != "ready":
            continue
        lang = row["lang"]
        filename = row["filename"]
        local_path = os.path.join(LOCAL_BATCH_DIR, lang, filename)
        if not os.path.exists(local_path):
            print(f"[Queue] 경고: {local_path} 파일이 로컬에 없어 건너뜁니다.")
            continue

        lang_folder = get_or_create_folder(service, lang, queue_root)
        if _find_file_id(service, filename, lang_folder):
            print(f"[Queue] 이미 업로드됨, 건너뜀: {filename}")
            continue
        upload_file(local_path, lang_folder, filename)

    print("[Queue] 배치 업로드 완료.")


def _download_manifest(service, queue_root: str) -> tuple[str, list[dict]]:
    manifest_id = _find_file_id(service, MANIFEST_NAME, queue_root)
    if not manifest_id:
        raise FileNotFoundError("Drive에 manifest.csv가 없습니다. 먼저 upload_batch()를 실행하세요.")

    request = service.files().get_media(fileId=manifest_id)
    buf = io.BytesIO()
    from googleapiclient.http import MediaIoBaseDownload
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    text = buf.getvalue().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    return manifest_id, rows


def _update_manifest(service, manifest_id: str, rows: list[dict]):
    from googleapiclient.http import MediaFileUpload

    tmp_path = "/tmp/manifest_updated.csv"
    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    service.files().update(fileId=manifest_id, media_body=MediaFileUpload(tmp_path)).execute()


def fetch_next_ready_script(lang: str) -> dict:
    """
    Drive의 manifest.csv 를 확인해 지정 언어(lang)의 가장 빠른 순번(day) 중
    status == 'ready' 인 대본을 하나 가져오고, 상태를 'used'로 갱신합니다.

    반환: {"title": ..., "hook": ..., "script": ..., "scene_keywords": ..., "topic_slug": ..., "day": ...}
    """
    service = get_drive_service()
    queue_root = get_queue_root(service)
    manifest_id, rows = _download_manifest(service, queue_root)

    lang_upper = lang.upper()
    candidates = [r for r in rows if r["lang"] == lang_upper and r["status"] == "ready"]
    if not candidates:
        raise RuntimeError(f"[Queue] '{lang_upper}' 채널용으로 'ready' 상태인 대본이 없습니다. 대본을 더 추가해주세요.")

    next_row = sorted(candidates, key=lambda r: int(r["day"]))[0]
    lang_folder = get_or_create_folder(service, lang_upper, queue_root)
    file_id = _find_file_id(service, next_row["filename"], lang_folder)
    if not file_id:
        raise FileNotFoundError(f"Drive에서 {next_row['filename']} 파일을 찾을 수 없습니다.")

    from src.drive_utils import download_file_text
    raw_text = download_file_text(file_id)

    import re

    def _extract(tag):
        m = re.search(rf"\[{tag}\](.*?)(?=\n\[[A-Z_]+\]|\Z)", raw_text, re.S)
        return m.group(1).strip() if m else ""

    parsed = {
        "title": _extract("TITLE"),
        "hook": _extract("HOOK"),
        "script": _extract("SCRIPT"),
        "scene_keywords": _extract("SCENE_KEYWORDS"),
        "raw": raw_text,
        "topic_slug": os.path.splitext(next_row["filename"])[0],
        "day": next_row["day"],
        "drive_file_id": file_id,
    }

    # 상태를 'used'로 갱신
    for r in rows:
        if r is next_row:
            r["status"] = "used"
    _update_manifest(service, manifest_id, rows)
    print(f"[Queue] Day {next_row['day']} ({lang_upper}) 대본을 꺼내 'used'로 표시했습니다: {next_row['topic_kr']}")

    return parsed


if __name__ == "__main__":
    upload_batch()
