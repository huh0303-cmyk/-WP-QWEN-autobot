#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""27개 사이트 카테고리 건강도 + 포커스키워드 누락 감사 (읽기 전용, 변경 없음)"""
import os, json, requests

WP_USER = "huh0303@gmail.com"

SITES = [
    ("https://k-health365.com", "KHEALTH365COM"),
    ("https://koreamedicaltour.com", "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com", "KOREAINVEST365COM"),
    ("https://ki-korea.com", "KIKOREACOM"),
    ("https://koreainsurance365.com", "KOREAINSURANCE365COM"),
    ("https://kfinance365.com", "KFINANCE365COM"),
    ("https://koreataxnlaw.com", "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com", "KOREACRYPTO365COM"),
    ("https://krealestate365.com", "KREALESTATE365COM"),
    ("https://ktech365.com", "KTECH365COM"),
    ("https://kskin365.com", "KSKIN365COM"),
    ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com", "KWORLD365COM"),
    ("https://k-trip365.com", "KTRIP365COM"),
    ("https://k-visa365.com", "KVISA365COM"),
    ("https://koreawedding365.com", "KOREAWEDDING365COM"),
    ("https://kstudy365.com", "KSTUDY365COM"),
    ("https://studyinkorea365.com", "STUDYINKOREA365COM"),
    ("https://kieca-korea.org", "KIECAKOREAORG"),
    ("https://ksa-korea.org", "KSAKOREAORG"),
    ("https://sis-korea.com", "SISKOREACOM"),
    ("https://jobkorea365.com", "JOBKOREA365COM"),
    ("https://jobinkorea365.com", "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com", "JOBKOREAGLOBALCOM"),
    ("https://korea365.org", "KOREA365ORG"),
    ("https://koreanews365.com", "KOREANEWS365COM"),
    ("https://theseouljournal.com", "THESEOULJOURNALCOM"),
]


def get_categories(url, pw):
    cats = []
    page = 1
    while True:
        try:
            r = requests.get(f"{url}/wp-json/wp/v2/categories", auth=(WP_USER, pw),
                              params={"per_page": 100, "page": page}, timeout=15)
        except Exception:
            break
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        cats.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return cats


def get_posts_meta(url, pw):
    posts = []
    page = 1
    while True:
        try:
            r = requests.get(f"{url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                              params={"per_page": 100, "page": page, "status": "publish",
                                      "_fields": "id,categories,meta"}, timeout=20)
        except Exception:
            break
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def main():
    report = {}
    for url, env_key in SITES:
        pw = os.getenv(env_key, "")
        entry = {"error": None, "categories": [], "empty_categories": [],
                  "etc_count": 0, "etc_pct": 0, "total_posts": 0,
                  "missing_keyword": 0, "missing_keyword_pct": 0}
        if not pw:
            entry["error"] = "no_password"
            report[url] = entry
            print(f"⚠️ {url} — 비밀번호 없음")
            continue

        cats = get_categories(url, pw)
        cat_list = []
        etc_count = 0
        empty = []
        for c in cats:
            name = c.get("name", "")
            count = c.get("count", 0)
            if name.strip().lower() in ("uncategorized", "미분류"):
                continue
            cat_list.append({"name": name, "count": count})
            if count == 0:
                empty.append(name)
            if name.strip().lower() in ("etc", "기타", "etc.", "other", "others"):
                etc_count = count
        entry["categories"] = cat_list
        entry["empty_categories"] = empty

        posts = get_posts_meta(url, pw)
        total = len(posts)
        missing_kw = 0
        for p in posts:
            meta = p.get("meta", {}) or {}
            kw = meta.get("rank_math_focus_keyword", "")
            if not kw or not str(kw).strip():
                missing_kw += 1
        entry["total_posts"] = total
        entry["etc_count"] = etc_count
        entry["etc_pct"] = round(etc_count / total * 100, 1) if total else 0
        entry["missing_keyword"] = missing_kw
        entry["missing_keyword_pct"] = round(missing_kw / total * 100, 1) if total else 0

        report[url] = entry
        print(f"✅ {url} | 글:{total} | 카테고리:{len(cat_list)}개 | 빈카테고리:{len(empty)}개 "
              f"{empty if empty else ''} | Etc비중:{entry['etc_pct']}% | 키워드누락:{entry['missing_keyword_pct']}%")

    with open("category_audit_result.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
