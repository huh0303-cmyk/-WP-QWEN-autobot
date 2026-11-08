"""Authenticated, fail-closed daily gate for the owner's K-Visa365 publisher."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys

import requests

SITE = "https://k-visa365.com"
KST = timezone(timedelta(hours=9))


def read_json(session, route, **params):
    response = session.get(SITE + "/wp-json/wp/v2/" + route,
                           params=params, timeout=25, allow_redirects=False)
    if response.status_code != 200:
        challenge = "Checking your browser" in response.text
        reason = "HOSTINGER_BROWSER_CHALLENGE" if challenge else "WORDPRESS_HTTP_ERROR"
        raise RuntimeError(f"{reason}: HTTP {response.status_code} ({route})")
    try:
        return response.json(), response.headers
    except ValueError:
        raise RuntimeError("REST endpoint did not return JSON") from None


def inventory(session, now):
    start = now.astimezone(KST).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    found = []
    for status in ("publish", "future"):
        for page in range(1, 101):
            rows, headers = read_json(session, "posts", status=status, context="edit",
                                     per_page=100, page=page, orderby="date", order="desc",
                                     _fields="id,link,date_gmt,title,status")
            if not isinstance(rows, list):
                raise RuntimeError("Invalid post inventory")
            older = False
            for row in rows:
                date = datetime.fromisoformat(row["date_gmt"].removesuffix("Z") + "+00:00")
                if start <= date < end:
                    found.append(row)
                if date < start:
                    older = True
            if older or not rows or page >= int(headers.get("X-WP-TotalPages", "1")):
                break
        else:
            raise RuntimeError("Post inventory exceeds safe pagination limit")
    return found


def check(session, now, verify=False):
    user, _ = read_json(session, "users/me", context="edit")
    if not user.get("capabilities", {}).get("publish_posts"):
        raise RuntimeError("Authenticated WordPress user lacks publish_posts capability")
    posts = inventory(session, now)
    result = {"site": SITE, "day_kst": now.astimezone(KST).date().isoformat(),
              "should_publish": not bool(posts), "posts": posts}
    if verify:
        published = [p for p in posts if p["status"] == "publish"]
        if not published:
            raise RuntimeError("NO_PUBLICATION_RECEIPT: no public post for the current KST day")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from automation_hub.public_verifier import verify_publication
        receipts = []
        for post in published:
            receipt = verify_publication(post["link"], post["title"]["rendered"], site_url=SITE)
            receipts.append(receipt.to_dict())
            if not receipt.ok:
                raise RuntimeError(f"PUBLIC_PAGE_CHECK_FAILED: {receipt.error_code}")
        result["receipts"] = receipts
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    target = Path("artifacts/kvisa-daily-receipt.json" if args.verify
                  else "artifacts/kvisa-daily-preflight.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        password = os.environ.get("KVISA365COM", "").strip()
        if not password:
            raise RuntimeError("MISSING_KVISA365COM")
        with requests.Session() as session:
            session.auth = ("huh0303@gmail.com", password)
            session.headers["User-Agent"] = "Korea365-Control/1.1"
            result = check(session, datetime.now(KST), args.verify)
    except (RuntimeError, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        # Never serialize request objects, Authorization headers or response bodies.
        reason = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        target.write_text(json.dumps({"site": SITE, "status": "BLOCKED", "reason": reason}), encoding="utf-8")
        print(f"::error::{reason}")
        return 1
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if os.getenv("GITHUB_OUTPUT") and not args.verify:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"should_publish={str(result['should_publish']).lower()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
