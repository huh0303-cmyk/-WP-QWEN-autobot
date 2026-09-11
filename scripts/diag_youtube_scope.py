"""Lightweight scope check: does the stored globalmusic YouTube OAuth token
have enough scope for channels().list(mine=true)? No video/API quota-heavy
work here, just the exact call that failed in the real pipeline."""
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

creds = Credentials(
    token=None,
    refresh_token=os.environ["YOUTUBE_OAUTH_REFRESH_TOKEN"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ["YOUTUBE_OAUTH_CLIENT_ID"],
    client_secret=os.environ["YOUTUBE_OAUTH_CLIENT_SECRET"],
    scopes=["https://www.googleapis.com/auth/youtube"],
)
youtube = build("youtube", "v3", credentials=creds)
try:
    resp = youtube.channels().list(part="id,snippet", mine=True, maxResults=1).execute()
    items = resp.get("items", [])
    if items:
        print(f"OK channel_id={items[0]['id']} title={items[0]['snippet']['title']}")
    else:
        print("OK call succeeded but no channel items returned")
except HttpError as e:
    print(f"FAIL {e.resp.status} {e}")
