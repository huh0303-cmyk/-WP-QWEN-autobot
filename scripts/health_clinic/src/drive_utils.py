"""
Google Drive 인증 + 업로드/다운로드 유틸리티.
Drive API와 YouTube API는 같은 OAuth 인증정보(credentials.json / token.json)를 공유합니다.

최초 1회는 반드시 로컬에서 아래처럼 실행해서 브라우저 로그인으로 token.json을 생성하세요:
    python src/drive_utils.py
huh0303@gmail.com 계정으로 로그인/승인하시면 됩니다.
"""
import io
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")


def get_credentials() -> Credentials:
    """공용 Google OAuth 자격증명을 반환. 없으면 브라우저 인증 흐름을 실행."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


def get_drive_service():
    return build("drive", "v3", credentials=get_credentials())


def get_or_create_folder(service, name: str, parent_id: str | None = None) -> str:
    """이름으로 폴더를 찾고 없으면 새로 생성 후 folder id 반환."""
    query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        metadata["parents"] = [parent_id]
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_file(local_path: str, folder_id: str, filename: str | None = None) -> str:
    """로컬 파일을 지정 폴더에 업로드하고 Drive 파일 id를 반환."""
    service = get_drive_service()
    filename = filename or os.path.basename(local_path)
    metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(local_path, resumable=True)
    file = service.files().create(body=metadata, media_body=media, fields="id, webViewLink").execute()
    print(f"[Drive] 업로드 완료: {filename} → {file.get('webViewLink')}")
    return file["id"]


def download_file_text(file_id: str) -> str:
    """Drive의 텍스트(대본) 파일을 문자열로 읽어옴."""
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue().decode("utf-8")


def download_file_to_path(file_id: str, dest_path: str) -> str:
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return dest_path


if __name__ == "__main__":
    # 최초 인증용 (token.json 생성)
    get_credentials()
    print("✅ 인증 완료. token.json이 생성되었습니다.")
