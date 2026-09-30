#!/usr/bin/env python3
"""Site Health Guardian — WordPress 27 + Blogger 33 정기 건강도 점검 및 안전 자동복구.

무료 티어만 사용한다(유료 API 호출 없음). 매 실행마다:
  1. 공개 점검: 홈 200, robots.txt 전체차단 여부, 메타/헤더 noindex, 사이트맵 URL 수,
     ads.txt, 마지막 발행일(정체), 중복 제목.
  2. 인증 점검(WP 앱 비밀번호): Rank Math·Site Kit 플러그인 상태, Site Kit 연결 상태,
     예약(future)인데 시간이 지난 글.
  3. GSC(서비스 계정): 사이트맵 제출/오류 상태, 최근 28일 클릭·노출.
  4. 안전한 자동 수정(GUARDIAN_FIX=1일 때만):
       - 시간이 지난 'future' 글 → publish
       - Rank Math 비활성 → 활성화
       - 사이트맵 미제출/오류 → GSC 재제출
       - IndexNow 핑(키 파일이 실제로 공개돼 있을 때만)
     삭제·비공개 전환·플러그인 초기화·Site Kit 재설정 같은 되돌리기 어려운 작업은
     절대 자동으로 하지 않고 report의 manual_actions로만 남긴다.
결과: artifacts/site-health/report.json, report.md
"""
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_registry import ACTIVE_SITES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "site-health"
ADSENSE_PUB = "pub-3456727916386941"
INDEXNOW_KEY = "907ae08aa52b45239490ed2407df835d"
WP_USER = "huh0303@gmail.com"
FIX = os.environ.get("GUARDIAN_FIX", "1") == "1"
STALE_DAYS = 4
UA = {"User-Agent": "SiteHealthGuardian/1.0 (+github actions)"}
NEWS = {"https://koreanews365.com", "https://theseouljournal.com"}


# ---------- pure helpers (unit-tested) ----------
def robots_blocks_all(text):
    """User-agent: * 그룹에 'Disallow: /' 가 있으면 True."""
    applies = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            applies = value == "*"
        elif key == "disallow" and applies and value == "/":
            return True
    return False


def has_noindex(html, x_robots=""):
    if "noindex" in (x_robots or "").lower():
        return True
    for tag in re.findall(r"<meta[^>]+name=[\"']robots[\"'][^>]*>", html, flags=re.I):
        if "noindex" in tag.lower():
            return True
    return False


def duplicate_title_groups(titles):
    norm = Counter(re.sub(r"\s+", " ", t).strip().lower() for t in titles if t)
    return {k: v for k, v in norm.items() if v > 1}


def days_since(iso):
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400


def count_locs(xml):
    return len(re.findall(r"<loc>", xml))


# ---------- GSC ----------
class GSC:
    def __init__(self):
        self.token = None
        self.props = set()
        raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "")
        if not raw:
            return
        try:
            import jwt
            key = json.loads(raw)
            now = int(time.time())
            assertion = jwt.encode({
                "iss": key["client_email"],
                "scope": "https://www.googleapis.com/auth/webmasters",
                "aud": "https://oauth2.googleapis.com/token",
                "iat": now, "exp": now + 3600}, key["private_key"], algorithm="RS256")
            r = requests.post("https://oauth2.googleapis.com/token", data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion}, timeout=20)
            r.raise_for_status()
            self.token = r.json()["access_token"]
            s = self._req("GET", "/sites")
            if s.status_code == 200:
                self.props = {e["siteUrl"] for e in s.json().get("siteEntry", [])}
        except Exception as exc:  # noqa: BLE001 - guardian must never crash on GSC
            print(f"GSC init failed: {type(exc).__name__}")
            self.token = None

    def _req(self, method, path, **kw):
        return requests.request(
            method, "https://www.googleapis.com/webmasters/v3" + path,
            headers={"Authorization": f"Bearer {self.token}"}, timeout=25, **kw)

    def prop_for(self, site_url):
        domain = site_url.replace("https://", "").rstrip("/")
        for cand in (site_url + "/", site_url, f"sc-domain:{domain}"):
            if cand in self.props:
                return cand
        return None

    def sitemaps(self, prop):
        r = self._req("GET", f"/sites/{quote(prop, safe='')}/sitemaps")
        return r.json().get("sitemap", []) if r.status_code == 200 else None

    def submit(self, prop, sitemap_url):
        r = self._req("PUT", f"/sites/{quote(prop, safe='')}/sitemaps/{quote(sitemap_url, safe='')}")
        return r.status_code in (200, 204)

    def traffic_28d(self, prop):
        end = datetime.now(timezone.utc).date() - timedelta(days=2)
        start = end - timedelta(days=27)
        r = self._req("POST", f"/sites/{quote(prop, safe='')}/searchAnalytics/query",
                      json={"startDate": str(start), "endDate": str(end)})
        if r.status_code != 200:
            return None
        rows = r.json().get("rows", [])
        if not rows:
            return {"clicks": 0, "impressions": 0}
        return {"clicks": int(rows[0]["clicks"]), "impressions": int(rows[0]["impressions"])}


# ---------- WordPress ----------
def wp_get(url, auth=None, **kw):
    return requests.get(url, auth=auth, timeout=30, headers=UA, **kw)


def check_wp(site, gsc):
    url, env_key, lifecycle = site
    row = {"site": url, "platform": "newsroom" if url in NEWS else "wordpress",
           "issues": [], "manual_actions": [], "fixes": []}
    auth = (WP_USER, os.environ[env_key]) if os.environ.get(env_key) else None
    if not auth:
        row["issues"].append("credential_missing")

    def issue(level, msg):
        row["issues"].append(f"{level}:{msg}")

    try:
        home = wp_get(url + "/")
        row["home_status"] = home.status_code
        if home.status_code != 200:
            issue("critical", f"home_http_{home.status_code}")
        if has_noindex(home.text, home.headers.get("X-Robots-Tag", "")):
            issue("critical", "home_noindex")
            row["manual_actions"].append("설정>읽기>검색엔진 노출 체크 해제 및 SEO 플러그인 noindex 확인")
        row["adsense_tag"] = "adsbygoogle" in home.text or ADSENSE_PUB in home.text
        row["sitekit_marker"] = "google-site-kit" in home.text.lower()
    except requests.RequestException as exc:
        issue("critical", f"home_unreachable_{type(exc).__name__}")
        return row

    try:
        rb = wp_get(url + "/robots.txt")
        row["robots_status"] = rb.status_code
        if rb.status_code == 200 and robots_blocks_all(rb.text):
            issue("critical", "robots_disallow_all")
        if rb.status_code == 200 and "sitemap" not in rb.text.lower():
            issue("warn", "robots_no_sitemap_line")
    except requests.RequestException:
        issue("warn", "robots_unreachable")

    sitemap_url = None
    for path in ("/sitemap_index.xml", "/wp-sitemap.xml", "/sitemap.xml"):
        try:
            sm = wp_get(url + path)
        except requests.RequestException:
            continue
        if sm.status_code == 200 and "<loc>" in sm.text:
            sitemap_url = url + path
            row["sitemap_url"] = sitemap_url
            row["sitemap_index_entries"] = count_locs(sm.text)
            break
    if not sitemap_url:
        issue("critical", "sitemap_missing")

    try:
        ads = wp_get(url + "/ads.txt")
        row["ads_txt_ok"] = ads.status_code == 200 and ADSENSE_PUB in ads.text
        if not row["ads_txt_ok"]:
            issue("warn", "ads_txt_missing_or_wrong")
    except requests.RequestException:
        issue("warn", "ads_txt_unreachable")

    # 최근 글: 정체 여부 + 중복 제목
    try:
        pr = wp_get(url + "/wp-json/wp/v2/posts", params={
            "per_page": 100, "_fields": "id,date_gmt,link,title", "orderby": "date", "order": "desc"})
        if pr.status_code == 200:
            posts = pr.json()
            row["public_total"] = int(pr.headers.get("X-WP-Total", len(posts)))
            if posts:
                row["latest_published"] = posts[0]["date_gmt"] + "Z"
                age = days_since(row["latest_published"])
                row["days_since_last_post"] = round(age, 1) if age is not None else None
                if age is not None and age > STALE_DAYS:
                    issue("warn", f"stale_{int(age)}d")
                dups = duplicate_title_groups([p["title"]["rendered"] for p in posts])
                row["duplicate_title_groups"] = len(dups)
                if dups:
                    issue("warn", f"duplicate_titles_{len(dups)}groups")
                    row["manual_actions"].append("중복 제목 그룹 검토 후 대표 1개만 공개(비공개 전환은 승인 후)")
            else:
                issue("critical", "no_public_posts")
            row["_recent_urls"] = [p["link"] for p in posts[:20]]
            if row.get("public_total", 0) < 10 and url not in NEWS:
                issue("warn", f"thin_public_content_{row['public_total']}")
    except (requests.RequestException, ValueError):
        issue("warn", "posts_api_failed")

    if auth:
        # 플러그인 상태
        try:
            pl = wp_get(url + "/wp-json/wp/v2/plugins", auth=auth)
            if pl.status_code == 200:
                plugins = pl.json()
                rm = next((p for p in plugins if p.get("plugin", "").startswith("seo-by-rank-math")), None)
                sk = next((p for p in plugins if p.get("plugin", "").startswith("google-site-kit")), None)
                row["rankmath"] = rm.get("status") if rm else "not_installed"
                row["sitekit"] = sk.get("status") if sk else "not_installed"
                if rm and rm.get("status") != "active":
                    issue("warn", "rankmath_inactive")
                    if FIX:
                        ok = requests.put(
                            f"{url}/wp-json/wp/v2/plugins/{rm['plugin']}", auth=auth, timeout=30,
                            json={"status": "active"}).status_code == 200
                        row["fixes"].append({"rankmath_activate": ok})
                if not rm:
                    issue("warn", "rankmath_not_installed")
            else:
                issue("warn", f"plugins_api_{pl.status_code}")
        except requests.RequestException:
            issue("warn", "plugins_api_failed")

        # Site Kit 연결
        if row.get("sitekit") == "active":
            try:
                c = wp_get(url + "/wp-json/google-site-kit/v1/core/site/data/connection", auth=auth)
                if c.status_code == 200:
                    conn = c.json()
                    row["sitekit_connected"] = bool(conn.get("connected"))
                    row["sitekit_setup_completed"] = bool(conn.get("setupCompleted"))
                    if not (conn.get("connected") and conn.get("setupCompleted")):
                        issue("critical", "sitekit_disconnected")
                        row["manual_actions"].append(
                            "wp-admin > Site Kit > 설정에서 Google 계정으로 재연결(자동 불가: 구글 로그인 필요)")
                else:
                    issue("critical", f"sitekit_connection_api_{c.status_code}")
                    row["manual_actions"].append(
                        "Site Kit 연결 오류 — 플러그인 설정 재실행 필요(애드센스 연결 일시 해제되므로 수동 승인 후)")
            except requests.RequestException:
                issue("warn", "sitekit_check_failed")

        # 시간이 지난 예약글 → 발행
        try:
            fr = wp_get(url + "/wp-json/wp/v2/posts", auth=auth, params={
                "status": "future", "per_page": 100, "_fields": "id,date_gmt"})
            if fr.status_code == 200:
                overdue = [p for p in fr.json()
                           if (days_since(p["date_gmt"] + "Z") or -1) > 0]
                row["future_total"] = len(fr.json())
                row["future_overdue"] = len(overdue)
                if overdue:
                    issue("warn", f"overdue_scheduled_{len(overdue)}")
                    if FIX:
                        done = 0
                        for p in overdue[:30]:
                            ok = requests.post(f"{url}/wp-json/wp/v2/posts/{p['id']}", auth=auth,
                                               timeout=30, json={"status": "publish"}).status_code == 200
                            done += ok
                        row["fixes"].append({"published_overdue_scheduled": done})
        except requests.RequestException:
            pass

    # GSC
    if gsc.token:
        prop = gsc.prop_for(url)
        row["gsc_property"] = prop
        if not prop:
            issue("warn", "gsc_property_not_accessible")
        else:
            maps = gsc.sitemaps(prop)
            if maps is not None:
                submitted = sum(int(c.get("submitted", 0)) for m in maps for c in m.get("contents", []))
                indexed = sum(int(c.get("indexed", 0)) for m in maps for c in m.get("contents", []))
                errors = sum(int(m.get("errors", 0)) for m in maps)
                row["gsc_sitemaps"] = len(maps)
                row["gsc_submitted"] = submitted
                row["gsc_indexed_reported"] = indexed
                row["gsc_sitemap_errors"] = errors
                if sitemap_url and not any(m.get("path", "").rstrip("/") == sitemap_url for m in maps):
                    issue("warn", "sitemap_not_submitted")
                    if FIX:
                        row["fixes"].append({"gsc_submit": gsc.submit(prop, sitemap_url)})
                if errors:
                    issue("warn", f"gsc_sitemap_errors_{errors}")
                    if FIX and sitemap_url:
                        row["fixes"].append({"gsc_resubmit": gsc.submit(prop, sitemap_url)})
            traffic = gsc.traffic_28d(prop)
            if traffic is not None:
                row["gsc_28d"] = traffic
                if traffic["impressions"] == 0 and row.get("public_total", 0) >= 10:
                    issue("warn", "zero_impressions_28d")

    # IndexNow (키 파일이 공개돼 있을 때만)
    if FIX and row.get("_recent_urls"):
        try:
            host = url.replace("https://", "")
            kf = requests.get(f"{url}/{INDEXNOW_KEY}.txt", timeout=15, headers=UA)
            if kf.status_code == 200 and INDEXNOW_KEY in kf.text:
                r = requests.post("https://api.indexnow.org/indexnow", timeout=20, json={
                    "host": host, "key": INDEXNOW_KEY,
                    "keyLocation": f"{url}/{INDEXNOW_KEY}.txt", "urlList": row["_recent_urls"]})
                row["fixes"].append({"indexnow_ping": r.status_code in (200, 202)})
        except requests.RequestException:
            pass
    row.pop("_recent_urls", None)
    return row


# ---------- Blogger ----------
def check_blogger(ch, gsc):
    url = ch["blogspot"].rstrip("/")
    row = {"site": url, "platform": "blogger", "title": ch.get("title"), "issues": [],
           "manual_actions": [], "fixes": []}
    try:
        r = requests.get(url + "/feeds/posts/default?alt=json&max-results=1", timeout=25, headers=UA)
        row["feed_status"] = r.status_code
        if r.status_code != 200:
            row["issues"].append(f"critical:feed_http_{r.status_code}")
        else:
            feed = r.json()["feed"]
            row["public_total"] = int(feed.get("openSearch$totalResults", {}).get("$t", 0))
            entries = feed.get("entry", [])
            if entries:
                row["latest_published"] = entries[0]["published"]["$t"]
                age = days_since(row["latest_published"])
                row["days_since_last_post"] = round(age, 1) if age is not None else None
                if age is not None and age > STALE_DAYS:
                    row["issues"].append(f"warn:stale_{int(age)}d")
            else:
                row["issues"].append("critical:no_public_posts")
        home = requests.get(url + "/", timeout=25, headers=UA)
        if has_noindex(home.text, home.headers.get("X-Robots-Tag", "")):
            row["issues"].append("critical:home_noindex")
        sm = requests.get(url + "/sitemap.xml", timeout=25, headers=UA)
        row["sitemap_status"] = sm.status_code
        if sm.status_code != 200:
            row["issues"].append("warn:sitemap_missing")
        if gsc.token:
            prop = gsc.prop_for(url)
            row["gsc_property"] = prop
            if prop:
                maps = gsc.sitemaps(prop)
                if maps is not None and not maps and FIX and sm.status_code == 200:
                    row["fixes"].append({"gsc_submit": gsc.submit(prop, url + "/sitemap.xml")})
                traffic = gsc.traffic_28d(prop)
                if traffic is not None:
                    row["gsc_28d"] = traffic
    except (requests.RequestException, ValueError, KeyError) as exc:
        row["issues"].append(f"critical:unreachable_{type(exc).__name__}")
    return row


# ---------- report ----------
def severity(row):
    if any(i.startswith("critical") for i in row["issues"]):
        return "critical"
    if row["issues"]:
        return "warn"
    return "ok"


def render_md(rows, started):
    counts = Counter(severity(r) for r in rows)
    lines = [f"# 사이트 건강도 리포트 ({started})", "",
             f"- 점검 {len(rows)}곳 · 정상 {counts['ok']} · 경고 {counts['warn']} · 심각 {counts['critical']}",
             f"- 자동수정 모드: {'ON' if FIX else 'OFF(점검만)'}", ""]
    for level, title in (("critical", "심각"), ("warn", "경고")):
        group = [r for r in rows if severity(r) == level]
        if not group:
            continue
        lines += [f"## {title}", ""]
        for r in group:
            lines.append(f"- **{r['site']}** ({r['platform']}): {', '.join(r['issues'])}")
            for fx in r["fixes"]:
                lines.append(f"  - 자동수정: {fx}")
            for m in r["manual_actions"]:
                lines.append(f"  - 수동 필요: {m}")
        lines.append("")
    manual = [(r["site"], m) for r in rows for m in r["manual_actions"]]
    if manual:
        lines += ["## 사람이 해야 하는 일", ""] + [f"- {s}: {m}" for s, m in manual] + [""]
    traffic = sorted(((r["site"], r["gsc_28d"]) for r in rows if r.get("gsc_28d")),
                     key=lambda x: -x[1]["clicks"])[:10]
    if traffic:
        lines += ["## 최근 28일 검색 클릭 상위", ""] + [
            f"- {s}: 클릭 {t['clicks']} / 노출 {t['impressions']}" for s, t in traffic] + [""]
    return "\n".join(lines)


def main():
    started = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST")
    portfolio = json.loads((ROOT / "config/blogger_portfolio.json").read_text(encoding="utf-8"))["channels"]
    gsc = GSC()
    print(f"GSC properties accessible: {len(gsc.props)}")
    with ThreadPoolExecutor(max_workers=4) as pool:
        wp_rows = list(pool.map(lambda s: check_wp(s, gsc), ACTIVE_SITES))
        bl_rows = list(pool.map(lambda c: check_blogger(c, gsc), portfolio))
    rows = wp_rows + bl_rows
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(
        {"generated": started, "fix_mode": FIX, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    md = render_md(rows, started)
    (OUT / "report.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
