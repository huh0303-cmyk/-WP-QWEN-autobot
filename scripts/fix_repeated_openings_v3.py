#!/usr/bin/env python3
"""Rewrite ONLY the first sentence of posts whose opening repeats another post on the same site
(exact same first sentence, or same first 5 words in >=3 posts). Keeps one post per group untouched.
Skips newsroom source-attribution openings. New sentence must keep the language, add no new numbers, and not
share its first 3 words with any other opening on the site. Env: APPLY_CHANGES, ONLY_SITES. Backups -> artifacts/opening_backups/."""
from __future__ import annotations
import collections, json, os, re, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup, NavigableString
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_openings_v3 as A  # noqa: E402
from audit_titles_images_v2 import ROOT  # noqa: E402

APPLY = os.environ.get("APPLY_CHANGES", "false").lower() == "true"
ONLY = {x.strip() for x in os.environ.get("ONLY_SITES", "").split(",") if x.strip()}
WP_USER = "huh0303@gmail.com"
ATTRIB = re.compile(r"보도에 따르면|according to|reported by|에 따르면", re.I)
OUT = Path("artifacts/opening_backups"); OUT.mkdir(parents=True, exist_ok=True)
NUM = re.compile(r"\d[\d,.]*")


def lang(s): return "ko" if re.search(r"[가-힣]", s) else ("ja" if re.search(r"[ぁ-んァ-ン]", s) else "en")


def groups(data):
    ex, pf = collections.defaultdict(list), collections.defaultdict(list)
    for site, rows in data.items():
        for r in rows:
            n = A.norm(r["opening"])
            if len(n) < 12: continue
            ex[(site, n)].append(r); pf[(site, " ".join(n.split()[:5]))].append(r)
    targets = {}
    for g in list(ex.values()) + [v for v in pf.values() if len(v) >= 3]:
        if len(g) < (2 if g in ex.values() else 3): continue
        for r in g[1:]:
            if ATTRIB.search(r["opening"]): continue
            targets[(r.get("site_key"), r["id"])] = r
    return targets


def rewrite(title, sent, avoid):
    import economy_text
    for _ in range(2):
        prompt = (f"Rewrite ONLY the opening sentence of a blog post so it starts differently from other posts.\n"
                  f"Post title: {title}\nOriginal opening sentence: {sent}\n"
                  f"Rules: same language as the original; keep exactly the same meaning and facts; do NOT add any new facts or numbers; "
                  f"similar length; do not begin with any of these phrases: {'; '.join(sorted(avoid)[:12])}; avoid cliches like 'In today's', 'In the dynamic world of', '안녕하세요'. "
                  f"Return ONLY the new sentence, no quotes.")
        try:
            new = economy_text.generate_text(prompt, temperature=0.8).strip().strip('"“”「」').split("\n")[0].strip()
        except Exception as e:  # noqa: BLE001
            print("LLM fail", type(e).__name__, flush=True); continue
        if not new or lang(new) != lang(sent) or not (0.5 <= len(new) / max(1, len(sent)) <= 1.7): continue
        if set(NUM.findall(new)) - set(NUM.findall(sent)): continue
        if " ".join(A.norm(new).split()[:3]) in {" ".join(a.split()[:3]) for a in avoid}: continue
        return new
    return None


def swap(body, old, new):
    soup = BeautifulSoup(body, "html.parser")
    for node in soup.find_all(string=True):
        if isinstance(node, NavigableString) and old[:30] in str(node) and node.parent.name not in ("script", "style", "figcaption"):
            if old in str(node):
                node.replace_with(str(node).replace(old, new, 1)); return str(soup)
            return None
    return None


def main():
    sites = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
    sites = sites if isinstance(sites, list) else sites["sites"]
    wpc = {s["site_id"]: s for s in sites if s["platform"] == "wordpress"}
    data = {}
    for sid, s in wpc.items():
        if (not ONLY or sid in ONLY) and s.get("enabled", True):
            data[sid] = A.wp(s["url"])
    try:
        data.update({k: v for k, v in A.blogger().items() if not ONLY or k in ONLY})
    except Exception as e:  # noqa: BLE001
        print("BLOGGER FAIL", e)
    for site, rows in data.items():
        for r in rows: r["site_key"] = site
    targets = groups(data)
    print("posts", sum(len(v) for v in data.values()), "to rewrite", len(targets), "apply", APPLY, flush=True)
    openings = collections.defaultdict(set)
    for site, rows in data.items():
        for r in rows: openings[site].add(A.norm(r["opening"]))
    token, log = None, []
    for (site, pid), r in targets.items():
        rec = {"site": site, "id": pid, "old": r["opening"][:140]}
        new = rewrite(r["title"], r["opening"], openings[site])
        if not new:
            rec["status"] = "no_valid_rewrite"; log.append(rec); print(rec["status"], site, pid, flush=True); continue
        rec["new"] = new[:140]
        openings[site].add(A.norm(new))
        if not APPLY:
            rec["status"] = "dry_run"; log.append(rec); print("dry", site, pid, "|", r["opening"][:50], "=>", new[:60], flush=True); continue
        try:
            if site.startswith("blogger_"):
                if token is None or time.time() - token[1] > 2400:
                    t = requests.post("https://oauth2.googleapis.com/token", data={
                        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
                        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
                    token = (t, time.time())
                h = {"Authorization": f"Bearer {token[0]}"}
                u = f"https://www.googleapis.com/blogger/v3/blogs/{r['blog_id']}/posts/{pid}"
                cur = requests.get(u, headers=h, timeout=30); cur.raise_for_status(); body = cur.json()["content"]
                nb = swap(body, r["opening"], new)
                if nb is None: rec["status"] = "sentence_not_locatable"
                else:
                    (OUT / f"{site}-{pid}.html").write_text(body, encoding="utf-8")
                    rr = requests.patch(u, headers=h, json={"content": nb}, timeout=40); rec["status"] = "updated" if rr.ok else f"failed HTTP {rr.status_code}"
            else:
                s = wpc[site]; auth = (WP_USER, os.environ[s["secret_name"]]); tgt = f"{s['url']}/wp-json/wp/v2/posts/{pid}"
                cur = requests.get(tgt, auth=auth, params={"context": "edit"}, timeout=30); cur.raise_for_status()
                body = cur.json()["content"]["raw"]
                nb = swap(body, r["opening"], new)
                if nb is None: rec["status"] = "sentence_not_locatable"
                else:
                    (OUT / f"{site}-{pid}.html").write_text(body, encoding="utf-8")
                    rr = requests.post(tgt, auth=auth, json={"content": nb}, timeout=40); rec["status"] = "updated" if rr.ok else f"failed HTTP {rr.status_code}"
        except Exception as e:  # noqa: BLE001
            rec["status"] = f"error {type(e).__name__}: {str(e)[:90]}"
        log.append(rec); print(rec["status"], site, pid, flush=True); time.sleep(0.8)
    Path("artifacts/opening_fix_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    c = collections.Counter(x["status"] for x in log); print(json.dumps(c))


if __name__ == "__main__":
    main()
