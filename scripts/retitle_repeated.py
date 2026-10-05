#!/usr/bin/env python3
"""Rewrite repeated / templated titles on WP + Blogger posts with unique LLM-written titles.
Default dry-run. Env: APPLY_CHANGES=true to write. Only titles are changed (slug/body untouched)."""
from __future__ import annotations
import collections, html, json, os, re, sys, time
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import audit_titles_all as A          # noqa: E402
import economy_text                    # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
from automation_hub.repetition_guard import title_self_issues  # noqa: E402
APPLY = os.environ.get("APPLY_CHANGES", "false").lower() == "true"
WP_USER = "huh0303@gmail.com"
KEEP_PER_PATTERN = 1
OPEN_MIN, END_MIN = 4, 6
HANGUL = re.compile(r"[가-힣]")


def clean(t): return html.unescape(re.sub(r"<[^>]+>", "", t or "")).strip()
def words(t): return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", clean(t).lower())).split()
def opening(t): w = words(t); return " ".join(w[:3]) if len(w) >= 3 else ""
def ending(t): w = words(t); return " ".join(w[-3:]) if len(w) >= 4 else ""


STOPW = set("a an the and or of to in on for with from by at as is are your you how what vs about korea korean".split())


def _jac(a, b):
    x = {w for w in words(a) if w not in STOPW and len(w) > 2}
    y = {w for w in words(b) if w not in STOPW and len(w) > 2}
    return len(x & y) / len(x | y) if len(x) >= 4 and len(y) >= 4 else 0.0


def det_fix(t):
    """Deterministic repair: drop a trailing keyword parenthetical / stock tail."""
    n = re.sub(r"\s*\([^()]{6,}\)", "", t)
    n = re.sub(r"(?i)[:\-]?\s*(a closer look at what really matters|frequently overlooked facts)\s*$", "", n)
    n = re.sub(r"\s{2,}", " ", n).strip(" :-")
    return n if n != t and len(n) >= 12 else ""


def flag(data):
    """Return {(site, id): reason} for posts to rewrite (keep the oldest per pattern)."""
    rows = [(s, r) for s, rs in data.items() for r in rs]
    rows.sort(key=lambda x: x[1].get("date", ""))
    seen_open, seen_end, seen_exact = collections.Counter(), collections.Counter(), set()
    seen_site = collections.defaultdict(list)
    op_total = collections.Counter(opening(r["title"]) for _, r in rows if opening(r["title"]))
    en_total = collections.Counter(ending(r["title"]) for _, r in rows if ending(r["title"]))
    out = {}
    for s, r in rows:
        t, o, e = r["title"], opening(r["title"]), ending(r["title"])
        ex = " ".join(words(t))  # network-wide exact duplicate
        reason = None
        if ex in seen_exact:
            reason = "duplicate"
        elif o and op_total[o] >= OPEN_MIN and seen_open[o] >= KEEP_PER_PATTERN:
            reason = f"opening:{o}"
        elif e and en_total[e] >= END_MIN and seen_end[e] >= KEEP_PER_PATTERN:
            reason = f"ending:{e}"
        elif title_self_issues(t):
            reason = "self:" + title_self_issues(t)[0][:60]
        elif any(_jac(t, o) >= 0.8 for o in seen_site[s]):
            reason = "near_duplicate"
        seen_site[s].append(t)
        seen_exact.add(ex); seen_open[o] += 1; seen_end[e] += 1
        if reason:
            out[(s, str(r["id"]))] = reason
    return out


def banned_list(data):
    ops = collections.Counter(opening(r["title"]) for rs in data.values() for r in rs)
    ens = collections.Counter(ending(r["title"]) for rs in data.values() for r in rs)
    return [k for k, v in ops.most_common(40) if v >= OPEN_MIN and k] + [k for k, v in ens.most_common(40) if v >= END_MIN and k]


def make_titles(batch, banned, avoid):
    items = "\n".join(f'{i}. [{ "KO" if HANGUL.search(b["title"]) else "EN" }] {b["title"]}' for i, b in enumerate(batch))
    prompt = f"""Rewrite each blog post title below so it reads like a human editor wrote it and is clearly different from the others.
Rules:
- Keep the same topic, main keyword and language ([KO]=Korean, [EN]=English).
- Natural phrasing, no clickbait clichés, no templates. Vary the structure (question, statement, how-to, number, comparison).
- Do NOT start or end with these overused phrases: {', '.join(banned[:40])}
- Never use years other than 2026; omit the year if unsure.
- English: Title Case, max 62 characters. Korean: max 38 characters. No quotes, no trailing period.
- Titles must differ from each other and from these existing titles: {' | '.join(avoid[:12])}
Return ONLY a JSON array of objects: [{{"i":0,"title":"..."}}, ...] covering every item.

Titles:
{items}"""
    txt = economy_text.generate_text(prompt, temperature=0.9)
    m = re.search(r"\[.*\]", txt, re.S)
    arr = json.loads(m.group(0))
    return {int(x["i"]): clean(x["title"]).strip('"“”\' ') for x in arr}


def valid(new, old, banned, used):
    if not new or new == old or len(new) < 8 or len(new) > 75:
        return False
    if bool(HANGUL.search(new)) != bool(HANGUL.search(old)):
        return False
    if opening(new) in banned or ending(new) in banned or opening(new) == opening(old):
        return False
    if re.search(r"\b(20(?!26)\d\d)\b", new):
        return False
    if " ".join(words(new)) in used:
        return False
    return True


def apply_wp(site_cfg, pid, title):
    pw = os.environ.get(site_cfg["secret_name"], "")
    if not pw:
        return False, "no secret"
    r = requests.post(f"{site_cfg['url']}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw), json={"title": title}, timeout=30)
    return r.status_code in (200, 201), f"HTTP {r.status_code}"


def main():
    cfg = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
    cfg = cfg if isinstance(cfg, list) else cfg["sites"]
    wp = {s["site_id"]: s for s in cfg if s["platform"] == "wordpress" and s.get("enabled", True)}
    data = {}
    for sid, s in wp.items():
        try:
            data[sid] = A.wp_titles(s["url"])
        except Exception as e:
            print("WP FAIL", sid, e)
    data.update(A.blogger_titles())
    flagged = flag(data)
    banned = banned_list(data)
    print(f"posts={sum(len(v) for v in data.values())} flagged={len(flagged)} apply={APPLY}")
    by_id = {(s, str(r["id"])): r for s, rs in data.items() for r in rs}
    used = {" ".join(words(r["title"])) for rs in data.values() for r in rs}
    per_site = collections.defaultdict(list)
    for k in flagged:
        per_site[k[0]].append(k)
    token = None
    log, ok_n, fail_n = [], 0, 0
    deadline = time.time() + float(os.environ.get("RETITLE_BUDGET_MIN", "35")) * 60
    for site, keys in per_site.items():
        avoid = [r["title"] for r in data[site][:30]]
        for i in range(0, len(keys), 8):
            if time.time() > deadline:
                print("budget reached; stopping", flush=True)
                break
            chunk = keys[i:i + 8]
            batch = [by_id[k] for k in chunk]
            result = {}
            for attempt in range(3):
                try:
                    result = make_titles(batch, banned, avoid)
                    break
                except Exception as e:
                    print("  gen retry", site, attempt, str(e)[:120], flush=True); time.sleep(3)
            for idx, k in enumerate(chunk):
                old = by_id[k]["title"]
                new = det_fix(old)
                if not (new and not title_self_issues(new) and " ".join(words(new)) not in used):
                    new = result.get(idx, "")
                    ok = valid(new, old, banned, used) and not title_self_issues(new)
                else:
                    ok = True
                if not ok:
                    log.append({"site": site, "id": k[1], "old": old, "new": new, "status": "skipped_invalid", "reason": flagged[k]})
                    fail_n += 1
                    continue
                used.add(" ".join(words(new)))
                status = "dry_run"
                if APPLY:
                    if site.startswith("blogger_"):
                        if token is None:
                            token = requests.post("https://oauth2.googleapis.com/token", data={
                                "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
                                "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
                        r = requests.patch(f"https://www.googleapis.com/blogger/v3/blogs/{by_id[k]['blog_id']}/posts/{k[1]}",
                                           headers={"Authorization": f"Bearer {token}"}, json={"title": new}, timeout=30)
                        good, msg = r.ok, f"HTTP {r.status_code}"
                    else:
                        good, msg = apply_wp(wp[site], k[1], new)
                    status = "updated" if good else f"failed {msg}"
                    ok_n += int(good); fail_n += int(not good)
                    time.sleep(0.8)
                log.append({"site": site, "id": k[1], "old": old, "new": new, "status": status, "reason": flagged[k]})
        print(f"{site}: {len(keys)} flagged", flush=True)
    Path("retitle_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"flagged": len(flagged), "updated": ok_n, "failed_or_skipped": fail_n}))
    for x in log[:60]:
        print(f"{x['status']:<10} {x['site']} | {x['old'][:55]} -> {x['new'][:55]}")


if __name__ == "__main__":
    main()
