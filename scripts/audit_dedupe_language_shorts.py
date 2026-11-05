#!/usr/bin/env python3
"""Audit duplicate Shorts by normalized title and curriculum pair across all ten channels."""
import argparse, datetime as dt, json, os, re, time, unicodedata
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "config/survival_language_channels.json"
CATALOG = ROOT / "config/survival_adjective_pairs.json"
OUT = ROOT / "artifacts/youtube/language-duplicate-audit"


def env(code, name):
    suffix = f"LANGUAGE_{code.upper()}"
    value = os.environ.get(f"YOUTUBE_OAUTH_{name}_{suffix}") or os.environ.get(f"YOUTUBE_OAUTH_{name}")
    if not value:
        raise RuntimeError(f"Missing YOUTUBE_OAUTH_{name}_{suffix}")
    return value


def svc(code):
    credentials = Credentials(
        token=None, refresh_token=env(code, "REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=env(code, "CLIENT_ID"), client_secret=env(code, "CLIENT_SECRET"),
        scopes=None,
    )
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def norm(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    value = re.sub(r"#shorts?\b", "", value)
    return re.sub(r"[^\w]+", "", value, flags=re.UNICODE)


def videos(api, channel_id, limit=None):
    rows = api.channels().list(part="contentDetails", id=channel_id).execute().get("items", [])
    if len(rows) != 1:
        raise RuntimeError(f"Cannot resolve uploads playlist {channel_id}")
    playlist = rows[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, token = [], None
    while limit is None or len(ids) < limit:
        page_size = 50 if limit is None else min(50, limit - len(ids))
        page = api.playlistItems().list(
            part="contentDetails", playlistId=playlist, maxResults=page_size, pageToken=token
        ).execute()
        ids.extend(item["contentDetails"]["videoId"] for item in page.get("items", []))
        token = page.get("nextPageToken")
        if not token:
            break
    result = []
    for offset in range(0, len(ids), 50):
        result.extend(api.videos().list(
            part="snippet,statistics,status", id=",".join(ids[offset:offset + 50])
        ).execute().get("items", []))
    return result


def semantic_pair_key(video, code, pairs):
    snippet = video.get("snippet", {})
    metadata = norm(" ".join([
        snippet.get("title", ""), snippet.get("description", ""),
        " ".join(snippet.get("tags", [])),
    ]))
    for pair in pairs:
        words = [norm(word) for word in pair.get(code, []) if norm(word)]
        pair_id = norm(pair.get("id", ""))
        if pair_id and pair_id in metadata:
            return f"pair:{pair['id']}"
        if len(words) >= 2 and all(word in metadata for word in words):
            return f"pair:{pair['id']}"
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=0,
                        help="Maximum uploads per channel; 0 scans the complete uploads playlist")
    args = parser.parse_args()
    limit = args.limit or None
    registry = json.loads(REG.read_text(encoding="utf-8"))
    pairs = [pair for pair in json.loads(CATALOG.read_text(encoding="utf-8"))["pairs"]
             if pair.get("category", "adjective") != "noun"]
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "mode": "apply" if args.apply else "report_only",
        "scan_scope": "full_uploads_playlist" if limit is None else f"latest_{limit}",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "channels": [], "actions": [],
    }
    for row in registry["languages"]:
        code, channel_id = row["language_code"], row["channel_id"]
        api = svc(code)
        mine = api.channels().list(part="id", mine=True).execute().get("items", [])
        if len(mine) != 1 or mine[0].get("id") != channel_id:
            report["channels"].append({"language": code, "status": "BLOCKED_CHANNEL_IDENTITY_MISMATCH"})
            continue
        all_videos = videos(api, channel_id, limit)
        groups = {}
        for video in all_videos:
            if video.get("status", {}).get("privacyStatus") == "private":
                continue
            snippet = video.get("snippet", {})
            title_text = snippet.get("title", "")
            title_key = norm(title_text)
            description = snippet.get("description", "")
            # Only vocabulary-pair title patterns (e.g. "high vs low" or
            # "book • phone") are eligible for title-based cleanup. Generic
            # quiz/engagement titles can be reused for different questions.
            pair_title = bool(re.search(r"\bvs\b|[•]", title_text, flags=re.IGNORECASE))
            first_description_line = re.split(r"[\r\n]", description, maxsplit=1)[0]
            first_sentence = re.split(r"(?<=[.!?])\s+", first_description_line, maxsplit=1)[0]
            description_key = norm(first_sentence)
            pair_key = semantic_pair_key(video, code, pairs)
            if pair_title and title_key and description_key:
                groups.setdefault(
                    "pair_content:" + title_key + "|" + description_key, set()
                ).add(video["id"])
            if pair_key:
                groups.setdefault(pair_key, set()).add(video["id"])

        # Merge title-duplicate and semantic-pair matches into connected
        # components. A video is handled once even if it matches both keys.
        by_id = {video["id"]: video for video in all_videos}
        parent = {video_id: video_id for video_id in by_id}

        def find(video_id):
            while parent[video_id] != video_id:
                parent[video_id] = parent[parent[video_id]]
                video_id = parent[video_id]
            return video_id

        def union(left, right):
            root_left, root_right = find(left), find(right)
            if root_left != root_right:
                parent[root_right] = root_left

        reasons_by_component = {}
        for key, members in groups.items():
            if len(members) < 2:
                continue
            members = sorted(members)
            for video_id in members[1:]:
                union(members[0], video_id)
        components = {}
        for key, members in groups.items():
            if len(members) < 2:
                continue
            for video_id in members:
                root = find(video_id)
                components.setdefault(root, {"ids": set(), "keys": set()})
                components[root]["ids"].add(video_id)
                components[root]["keys"].add(key)

        losers = 0
        for component in components.values():
            cluster = [by_id[video_id] for video_id in component["ids"]]
            if len(cluster) < 2:
                continue
            if any("viewCount" not in video.get("statistics", {}) for video in cluster):
                report["actions"].append({
                    "language": code, "match_keys": sorted(component["keys"]),
                    "status": "REVIEW_VIEW_COUNT_UNAVAILABLE",
                    "video_ids": sorted(component["ids"]),
                })
                continue
            cluster.sort(key=lambda video: (
                int(video["statistics"]["viewCount"]),
                video.get("snippet", {}).get("publishedAt", ""),
            ), reverse=True)
            keep = cluster[0]
            for video in cluster[1:]:
                action = {
                    "language": code,
                    "match_keys": sorted(component["keys"]),
                    "title": video.get("snippet", {}).get("title"),
                    "keep_video_id": keep["id"],
                    "keep_views": int(keep["statistics"]["viewCount"]),
                    "duplicate_video_id": video["id"],
                    "duplicate_views": int(video["statistics"]["viewCount"]),
                    "status": "WOULD_SET_PRIVATE",
                }
                if args.apply:
                    old_status = video.get("status", {})
                    status = {field: old_status[field] for field in (
                        "license", "embeddable", "publicStatsViewable", "selfDeclaredMadeForKids"
                    ) if field in old_status}
                    status["privacyStatus"] = "private"
                    api.videos().update(part="status", body={"id": video["id"], "status": status}).execute()
                    # YouTube's videos.list index can lag the successful update.
                    # Retry read-only verification; never repeat the write request.
                    verified = False
                    last_check = None
                    for attempt in range(8):
                        check = api.videos().list(part="snippet,status", id=video["id"]).execute().get("items", [])
                        last_check = check
                        if (len(check) == 1
                                and check[0].get("snippet", {}).get("channelId") == channel_id
                                and check[0].get("status", {}).get("privacyStatus") == "private"):
                            verified = True
                            break
                        if attempt < 7:
                            time.sleep(2)
                    if not verified:
                        raise RuntimeError(f"Privacy verification failed after bounded read retries: {video['id']}; last={last_check}")
                    action["status"] = "VERIFIED_PRIVATE"
                report["actions"].append(action)
                losers += 1
        report["channels"].append({
            "language": code, "videos_scanned": len(all_videos),
            "duplicate_matches": losers, "status": "SCANNED",
        })
    path = OUT / f"duplicate_audit_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "mode": report["mode"], "scan_scope": report["scan_scope"],
        "channels": report["channels"], "actions": report["actions"],
        "report_path": str(path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
