"""Remove explicit reviewed featured-image assignments; keep media and articles."""
import json
import os
from pathlib import Path
import requests
from site_registry import SITES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/featured-image-removals"


def eligible(post, expected):
    return post.get("status") == "publish" and post.get("featured_media") == expected


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = json.loads((ROOT / "config/reviewed_featured_image_removals.json").read_text(encoding="utf-8"))
    allowed = {u: key for u, key, _ in SITES}
    receipts = []
    for item in plan["posts"]:
        site, post_id = item["site"], int(item["post_id"])
        receipt = dict(item)
        try:
            if site not in allowed or not os.getenv(allowed[site]):
                raise ValueError("Missing approved site credential")
            auth = ("huh0303@gmail.com", os.environ[allowed[site]])
            endpoint = f"{site}/wp-json/wp/v2/posts/{post_id}"
            before = requests.get(endpoint, auth=auth, params={"context": "edit"}, timeout=30)
            before.raise_for_status()
            post = before.json()
            if post.get("featured_media") == 0:
                receipt["status"] = "already_removed"
            elif not eligible(post, item["expected_media_id"]):
                receipt["status"] = "changed_since_review"
            elif os.getenv("APPLY", "false").lower() != "true":
                receipt["status"] = "reviewed_ready"
            else:
                # Preserve the exact pre-change assignment and article for review.
                (OUT / (site.split("//")[1] + f"-{post_id}-before.json")).write_text(
                    json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
                # One write only. Reconcile a timeout with GET, never repeat POST.
                try:
                    response = requests.post(endpoint, auth=auth, json={"featured_media": 0}, timeout=30)
                    response.raise_for_status()
                except requests.RequestException:
                    pass
                after = requests.get(endpoint, auth=auth, params={"context": "edit"}, timeout=30)
                after.raise_for_status()
                verified = after.json()
                if verified.get("featured_media") != 0:
                    raise ValueError("Featured image removal not verified")
                if verified.get("content", {}).get("raw") != post.get("content", {}).get("raw"):
                    receipt["content_changed_concurrently"] = True
                receipt.update(status="removed_verified", url=verified.get("link"))
        except (requests.RequestException, ValueError, KeyError) as exc:
            receipt.update(status="failed_or_uncertain", error=type(exc).__name__)
        receipts.append(receipt)
        (OUT / "results.json").write_text(json.dumps(receipts, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(receipt, ensure_ascii=False))
    if any(r["status"] in {"failed_or_uncertain", "changed_since_review"} for r in receipts):
        raise SystemExit("Some reviewed assignments were not changed; inspect receipts")


if __name__ == "__main__":
    main()
