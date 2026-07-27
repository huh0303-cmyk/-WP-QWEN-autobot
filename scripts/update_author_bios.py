# -*- coding: utf-8 -*-
"""
update_author_bios.py
autopost_mega.py의 AUTHOR_BY_SITE_DEF에 이미 반영된 새 bio(면허/자격/소속 사칭 문구
제거본)를, 각 사이트에 이미 생성되어 있는 WP 작성자 계정의 실제 description 필드에
반영한다. 코드만 고치면 "새로 계정을 만들 때"만 적용되고 기존 27개 계정에는 반영이
안 되므로, 이 스크립트로 기존 계정을 직접 PATCH한다.
"""
import os, sys, json, time, random, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, pick_reporter


def find_user_id(site_url, pw, reporter):
    for params in ({"search": reporter["email"], "per_page": 5},
                   {"slug": reporter["slug"], "per_page": 1}):
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/users", auth=(WP_USER, pw),
                              params=params, timeout=15)
            if r.status_code == 200 and r.json():
                return r.json()[0]["id"], r.json()[0].get("description", "")
        except Exception:
            pass
    return None, None


def fix_site(site, dry_run=False):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    log = {"site": site_url, "updated": [], "skipped": [], "failed": [], "dry_run": dry_run}
    if not pw:
        log["error"] = "no_password"
        return log

    reporter = pick_reporter(site)

    uid, current_desc = find_user_id(site_url, pw, reporter)
    if uid is None:
        log["skipped"].append({"reason": "user_not_found", "slug": reporter["slug"]})
        return log

    new_bio = reporter.get("bio", "")
    if (current_desc or "").strip() == new_bio.strip():
        log["skipped"].append({"reason": "already_up_to_date", "id": uid})
        return log

    entry = {"id": uid, "old_desc": (current_desc or "")[:120], "new_desc": new_bio[:120]}
    if dry_run:
        log["updated"].append(entry)
        return log

    try:
        r = requests.patch(f"{site_url}/wp-json/wp/v2/users/{uid}", auth=(WP_USER, pw),
                            json={"description": new_bio}, timeout=20)
        entry["status"] = r.status_code
        if r.status_code == 200:
            log["updated"].append(entry)
        else:
            entry["error"] = r.text[:200]
            log["failed"].append(entry)
    except Exception as e:
        entry["error"] = str(e)
        log["failed"].append(entry)

    time.sleep(random.uniform(0.5, 1.0))
    return log


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    targets = [s for s in SITES_CONFIG if (not args.site or s["url"] == args.site)]
    results = []
    out_file = "update_author_bios_dryrun.json" if args.dry_run else "update_author_bios_result.json"
    for site in targets:
        res = fix_site(site, dry_run=args.dry_run)
        results.append(res)
        tag = "[DRY-RUN] " if args.dry_run else ""
        print(f"{tag}{res['site']}: 수정{len(res.get('updated',[]))} / 스킵{len(res.get('skipped',[]))} "
              f"/ 실패{len(res.get('failed',[]))} / 오류{res.get('error','')}")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
