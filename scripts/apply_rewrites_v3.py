"""Apply subagent-researched rewrites in data/rewrites/*.html after deterministic validation.
Keeps each post's existing first figure, backs up old body. VALIDATE_ONLY=true -> no network."""
from __future__ import annotations
import html, json, os, re, sys, time
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parent))
import quality_scan_v3 as Q  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RW = ROOT / "data/rewrites"
VALIDATE_ONLY = os.environ.get("VALIDATE_ONLY", "true").lower() == "true"
ONLY = {x.strip() for x in os.environ.get("ONLY_KEYS", "").split(",") if x.strip()}
BAK = Path("artifacts/rewrite_backups"); BAK.mkdir(parents=True, exist_ok=True)
FORBID = re.compile(r"<h1|<img|<script|<iframe|```|\*\*[^*]+\*\*|^#{1,3} ", re.M)
OLDYEAR = re.compile(r"\b(2019|2020|2021|2022|2023|2024|2025)\b")


def validate(body: str):
    errs = []
    s = BeautifulSoup(body, "html.parser")
    text = re.sub(r"\s+", " ", s.get_text(" ")).strip()
    words = len(text.split()); kor = len(re.findall(r"[가-힣]", text))
    size = kor if kor > 200 else words
    if (kor > 200 and size < 900) or (kor <= 200 and size < 780): errs.append(f"short {size}")
    h2 = [h.get_text(" ", strip=True) for h in s.find_all("h2")]
    if len(h2) < 4: errs.append(f"h2={len(h2)}")
    links = [a["href"] for a in s.find_all("a", href=True) if a["href"].startswith("http")]
    if len(set(links)) < 2: errs.append("sources<2")
    if not h2 or not re.search(r"source|출처|참고", h2[-1], re.I): errs.append("no Sources last h2")
    if FORBID.search(body): errs.append("forbidden markup")
    for rx in (Q.CLICHE_EN, Q.CLICHE_KO):
        m = rx.search(text)
        if m: errs.append(f"cliche:{m.group(0)[:20]}")
    if Q.PERSONA.search(text): errs.append("persona")
    if re.search(r"\b(I|my|we) (have|visited|tried|tested|personally)\b", text): errs.append("first-person")
    if not re.search(r"Korea|Seoul|한국|서울", text): errs.append("no-korea")
    return errs, size, h2


def first_figure(body):
    s = BeautifulSoup(body or "", "html.parser"); img = s.find("img")
    return str(img.find_parent("figure") or img) if img else ""


def main():
    import requests
    files = sorted(RW.glob("*.html"))
    ok, bad = [], {}
    for f in files:
        key = f.stem
        if ONLY and key not in ONLY: continue
        body = f.read_text(encoding="utf-8")
        errs, size, _ = validate(body)
        (bad.__setitem__(key, errs) if errs else ok.append(key))
    print(f"valid {len(ok)} invalid {len(bad)}")
    for k, v in bad.items(): print("INVALID", k, v)
    if VALIDATE_ONLY:
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/rewrite_validation.json").write_text(json.dumps({"ok": ok, "bad": bad}, ensure_ascii=False, indent=1))
        return
    cfg = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8")); cfg = cfg if isinstance(cfg, list) else cfg["sites"]
    wpc = {s["site_id"]: s for s in cfg if s["platform"] == "wordpress"}
    prof = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
    bid = {f"blogger_{r['site_key']}": r["blogspot"]["destination_id"] for r in prof["profiles"] if r.get("blogspot", {}).get("destination_id")}
    tok = requests.post("https://oauth2.googleapis.com/token", data={"client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
          "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    log = []
    for key in ok:
        site, pid = key.rsplit("-", 1)
        rec = {"key": key}
        try:
            new = (RW / f"{key}.html").read_text(encoding="utf-8")
            if site.startswith("blogger_"):
                u = f"https://www.googleapis.com/blogger/v3/blogs/{bid[site]}/posts/{pid}"
                old = requests.get(u, headers=H, timeout=30).json()["content"]
            else:
                s = wpc[site]; auth = ("huh0303@gmail.com", os.environ[s["secret_name"]])
                u = f"{s['url']}/wp-json/wp/v2/posts/{pid}"
                old = requests.get(u, auth=auth, params={"context": "edit"}, timeout=30).json()["content"]["raw"]
            (BAK / f"{key}.html").write_text(old, encoding="utf-8")
            final = (first_figure(old) + "\n" + new).strip()
            rr = requests.patch(u, headers=H, json={"content": final}, timeout=60) if site.startswith("blogger_") else requests.post(u, auth=auth, json={"content": final}, timeout=60)
            rec["status"] = "rewritten" if rr.ok else f"failed {rr.status_code}"
        except Exception as e:  # noqa: BLE001
            rec["status"] = f"error {type(e).__name__}: {str(e)[:100]}"
        print(rec["status"], key, flush=True); log.append(rec); time.sleep(2)
    Path("artifacts/apply_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1))
    c = {}
    for x in log: c[x["status"]] = c.get(x["status"], 0) + 1
    print(json.dumps(c))


if __name__ == "__main__":
    main()
