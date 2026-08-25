import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials(
    token=None,
    refresh_token=os.environ["YOUTUBE_OAUTH_REFRESH_TOKEN_MBB_BROAD"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ["YOUTUBE_OAUTH_CLIENT_ID"],
    client_secret=os.environ["YOUTUBE_OAUTH_CLIENT_SECRET"],
)

youtube = build("youtube", "v3", credentials=creds)

video_id = "aXowfYGmMFg"
resp = youtube.videos().update(
    part="status",
    body={"id": video_id, "status": {"privacyStatus": "public"}},
).execute()

print("SUCCESS:", resp.get("id"), resp.get("status"))
