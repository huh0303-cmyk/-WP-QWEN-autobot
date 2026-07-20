#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resolve_404_and_index.py

목적:
1) 404 모니터 정리
   - 봇 스캔성 잡음(wp-admin, .php, adsbygoogle 등)은 즉시 로그 삭제
   - 진짜 존재했던 글 슬러그로 보이는 404는: 그 슬러그로 연결된 내부링크를
     본문에서 찾아 홈으로 안전하게 고쳐쓰고(REST API), 원인이 제거된 뒤
     404 로그도 삭제
2) 전체 발행글 색인 재제출
   - 사이트별 전체 발행 글 URL을 모아 IndexNow(빙/네이버/제네릭)에 재제출

실행 방식:
- 로그인은 실제 계정(WP_REAL_PASSWORD, 세션 쿠키) 사용 - 404모니터 화면은
  REST API가 없고 wp-admin 화면 자체를 읽어야 하기 때문
- 글 본문 수정/조회는 기존처럼 WP REST API(Application Password) 사용
"""
import os, re, json, sys, time
import requests
from bs4 import BeautifulSoup

WP_USER = "huh0303@gmail.com"
WP_REAL_PASSWORD = os.getenv("WP_REAL_PASSWORD", "")

# (사이트, GitHub Secret이름) - Application Password 용
SITES = [
    ("https://koreacrypto365.com",     "KOREACRYPTO365COM"),
]

INDEXNOW_KEY = "907ae08aa52b45239490ed2407df835d"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

JUNK_PATTERNS = [
    r"wp-admin", r"wp-login", r"wp-json", r"xmlrpc\.php", r"\.env", r"\.git",
    r"wp-content/(plugins|mu-plugins)", r"\.php($|[/?])", r"pagead", r"adsbygoogle",
    r"favicon\.ico", r"\.well-known", r"^feed/?$", r"/feed/?$", r"robots\.txt",
    r"\.(xml|txt|ico|map)$", r"^\?", r"wlwmanifest", r"apple-touch-icon",
    r"internal-link-", r"^tag/.*feed", r"\.(png|jpe?g|gif|css|js)$",
]
JUNK_RE = re.compile("|".join(JUNK_PATTERNS), re.IGNORECASE)


def login(site):
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.post(
        f"{site}/wp-login.php",
        data={"log": WP_USER, "pwd": WP_REAL_PASSWORD, "wp-submit": "Log In",
              "redirect_to": f"{site}/wp-admin/", "testcookie": "1"},
        timeout=30, allow_redirects=True,
    )
    ok = any(c.startswith("wordpress_logged_in_") for c in s.cookies.keys())
    return s, ok


def fetch_404_rows(session, site, max_pages=15):
    """페이지네이션 돌면서 404 로그 전체 수집"""
    all_rows = []
    for paged in range(1, max_pages + 1):
        url = f"{site}/wp-admin/admin.php?page=rank-math-404-monitor"
        if paged > 1:
            url += f"&paged={paged}"
        try:
            r = session.get(url, timeout=30)
        except Exception:
            break
        if r.status_code != 200:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", class_=re.compile("wp-list-table"))
        if not table:
            break
        tbody = table.find("tbody")
        if not tbody:
            break
        page_rows = []
        for tr in tbody.find_all("tr"):
            if "no-items" in (tr.get("class") or []):
                continue
            links = {}
            for a in tr.find_all("a", href=True):
                label = a.get_text(strip=True).lower()
                if label:
                    links[label] = a["href"]
            slug = None
            for k in links:
                if k not in ("view", "redirect", "delete"):
                    slug = k
                    break
            if slug is not None:
                page_rows.append({"slug": slug, "actions": links})
        if not page_rows:
            break
        all_rows.extend(page_rows)
        if len(page_rows) < 20:  # 마지막 페이지로 추정
            break
        time.sleep(0.5)
    return all_rows


def delete_404_row(session, delete_href):
    try:
        r = session.get(delete_href, timeout=20)
        return r.status_code == 200
    except Exception:
        return False


def fix_broken_internal_links(site, wp_app_pw, slug, home_url, log):
    """slug를 참조하는 내부링크를 가진 글을 찾아 홈으로 안전하게 교체"""
    auth = (WP_USER, wp_app_pw)
    fixed_posts = 0
    try:
        r = requests.get(
            f"{site}/wp-json/wp/v2/posts",
            auth=auth, params={"search": slug, "per_page": 20, "status": "publish",
                                "_fields": "id,link,content"},
            timeout=20,
        )
        if r.status_code != 200:
            return 0
        candidates = r.json()
        if not isinstance(candidates, list):
            return 0
        pattern = re.compile(r'href="([^"]*' + re.escape(slug) + r'[^"]*)"')
        for p in candidates:
            content = p.get("content", {}).get("rendered", "") or ""
            if not pattern.search(content):
                continue
            new_content = pattern.sub(f'href="{home_url}"', content)
            if new_content != content:
                rr = requests.post(
                    f"{site}/wp-json/wp/v2/posts/{p['id']}", auth=auth,
                    json={"content": new_content}, timeout=20,
                )
                if rr.status_code in (200, 201):
                    fixed_posts += 1
    except Exception as e:
        log(f"    ⚠️ 내부링크 수정 오류({slug[:30]}): {str(e)[:100]}")
    return fixed_posts


def submit_indexnow(site, urls, log):
    if not urls:
        return
    host = site.replace("https://", "").replace("http://", "").rstrip("/")
    payload = {
        "host": host, "key": INDEXNOW_KEY,
        "keyLocation": f"{site}/{INDEXNOW_KEY}.txt",
        "urlList": urls[:10000],
    }
    for ep in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow",
               "https://searchadvisor.naver.com/indexnow"]:
        try:
            r = requests.post(ep, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
            log(f"    IndexNow {ep.split('/')[2]}: HTTP {r.status_code}")
        except Exception as e:
            log(f"    IndexNow {ep.split('/')[2]}: 오류 {str(e)[:80]}")


def fetch_all_published_urls(site, wp_app_pw):
    auth = (WP_USER, wp_app_pw)
    urls = []
    for post_type in ("posts", "pages"):
        page_num = 1
        while True:
            try:
                r = requests.get(
                    f"{site}/wp-json/wp/v2/{post_type}", auth=auth,
                    params={"per_page": 100, "page": page_num, "status": "publish", "_fields": "link"},
                    timeout=25,
                )
            except Exception:
                break
            if r.status_code != 200:
                break
            batch = r.json()
            if not isinstance(batch, list) or not batch:
                break
            urls.extend([p["link"] for p in batch if p.get("link")])
            if len(batch) < 100:
                break
            page_num += 1
    return urls


def main():
    all_results = {}
    lines = []

    def log(m):
        print(m)
        lines.append(m)
        sys.stdout.flush()

    if not WP_REAL_PASSWORD:
        log("NO WP_REAL_PASSWORD"); sys.exit(1)

    for site, secret_name in SITES:
        wp_app_pw = os.getenv(secret_name, "")
        entry = {"site": site, "junk_deleted": 0, "real_fixed": 0, "real_flagged": [],
                  "indexnow_urls": 0, "login_ok": False}
        log(f"\n=== {site} ===")

        s, ok = login(site)
        entry["login_ok"] = ok
        if not ok:
            log("  ❌ 로그인 실패")
            all_results[site] = entry
            continue

        rows = fetch_404_rows(s, site)
        log(f"  404 로그 {len(rows)}건 수집")

        for row in rows:
            slug = row["slug"]
            delete_href = row["actions"].get("delete")
            if JUNK_RE.search(slug):
                if delete_href and delete_404_row(s, delete_href):
                    entry["junk_deleted"] += 1
                time.sleep(0.2)
                continue

            # 실제 콘텐츠로 보이는 404: 내부링크 수정 시도
            if wp_app_pw:
                fixed = fix_broken_internal_links(site, wp_app_pw, slug, site + "/", log)
                if fixed > 0:
                    entry["real_fixed"] += fixed
                    if delete_href:
                        delete_404_row(s, delete_href)
                        time.sleep(0.2)
                else:
                    entry["real_flagged"].append(slug)
            else:
                entry["real_flagged"].append(slug)

        log(f"  ✅ 정크삭제:{entry['junk_deleted']} / 내부링크수정:{entry['real_fixed']} / "
            f"미해결(수동검토필요):{len(entry['real_flagged'])}")

        # 색인 재제출
        if wp_app_pw:
            urls = fetch_all_published_urls(site, wp_app_pw)
            entry["indexnow_urls"] = len(urls)
            log(f"  발행글 {len(urls)}건 IndexNow 재제출")
            for i in range(0, len(urls), 200):
                submit_indexnow(site, urls[i:i + 200], log)
                time.sleep(1)
        else:
            log("  ⚠️ WP Application Password 없음 - 색인 재제출 스킵")

        all_results[site] = entry

    with open("resolve_404_and_index_result.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    with open("resolve_404_and_index_report.md", "w", encoding="utf-8") as f:
        f.write("# 404 해결 + 색인 재제출 리포트\n\n```\n" + "\n".join(lines) + "\n```\n")

    log("\n전체 완료")


if __name__ == "__main__":
    main()
