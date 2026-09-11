#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rename_categories_short_en.py
여러 사이트의 기존 카테고리 이름을 짧은 영어 명사형으로 일괄 변경합니다.
(카테고리 병합/삭제 없음 — 이름만 변경, 게시물 수 그대로 유지)
"""
import os, requests

WP_USER = "huh0303@gmail.com"
_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))

# 사이트: (secret_env, {기존이름: 새이름})
SITE_RENAMES = {
    "https://koreamedicaltour.com": ("KOREAMEDICALTOURCOM", {
        "성형·피부과": "Cosmetic Surgery", "정부지원혜택": "Government Support", "비용·병원비": "Hospital Costs",
    }),
    "https://ki-korea.com": ("KIKOREACOM", {
        "국내주식·ETF": "Stocks", "부동산·청약": "Real Estate", "절세·연금": "Pension", "기타": "Etc",
    }),
    "https://koreainsurance365.com": ("KOREAINSURANCE365COM", {
        "외국인 건강보험": "Health Insurance", "외국인 자동차보험": "Auto Insurance", "외국인 치과보험": "Dental Insurance",
    }),
    "https://kfinance365.com": ("KFINANCE365COM", {
        "외국인 은행·송금": "Banking", "외국인 투자·주식": "Investing", "외국인 세금·환급": "Tax Refund",
    }),
    "https://koreataxnlaw.com": ("KOREATAXNLAWCOM", {
        "외국인 세금·신고": "Tax Filing", "외국인 법인·창업": "Business Setup", "외국인 비자·체류": "Visa",
    }),
    "https://koreacrypto365.com": ("KOREACRYPTO365COM", {
        "업비트·거래소 가입": "Exchanges", "외국인 코인 투자법": "Investing", "한국 가상화폐 규제": "Regulations",
    }),
    "https://krealestate365.com": ("KREALESTATE365COM", {
        "아파트 매매·전세·월세": "Apartments", "상가·사업장 임대": "Commercial", "외국인 대출·세금": "Loans", "기타": "Etc",
    }),
    "https://koreawedding365.com": ("KOREAWEDDING365COM", {
        "결혼·법적·비자": "Marriage", "자녀국적·교육혜택": "Education", "매칭·결혼비용": "Matching",
    }),
    "https://ksa-korea.org": ("KSAKOREAORG", {
        "입학정보": "Admissions", "장학금": "Scholarships", "비자": "Visa",
    }),
    "https://oliveyoungkorea.com": ("OLIVEYOUNGKOREACOM", {
        "인기상품 TOP30": "Top Products",
    }),
    "https://kworld365.com": ("KWORLD365COM", {
        "K-Pop & Artists": "K-Pop", "K-Culture & Learn Korean": "Learn Korean", "Korean Life & Travel": "Travel",
    }),
    "https://k-trip365.com": ("KTRIP365COM", {
        "Hotels & Stays": "Hotels", "AirBnB & 민박": "AirBnB", "Travel Guides": "Guides",
    }),
    "https://korea365.org": ("KOREA365ORG", {
        "Korean Culture": "Culture", "Travel & Food": "Travel", "Living in Korea": "Living",
    }),
}


def get_categories(site_url, auth):
    r = requests.get(f"{site_url}/wp-json/wp/v2/categories", auth=auth,
                      params={"per_page": 100}, timeout=20)
    r.raise_for_status()
    return {c["name"]: c for c in r.json()}


def rename(site_url, auth, cat_id, new_name):
    r = requests.post(f"{site_url}/wp-json/wp/v2/categories/{cat_id}",
                       auth=auth, json={"name": new_name}, timeout=20)
    return r.status_code in (200, 201), r.status_code


def main():
    for site_url, (secret_name, rename_map) in SITE_RENAMES.items():
        pw = os.environ.get(secret_name)
        log(f"\n🌐 {site_url}")
        if not pw:
            log(f"   ⚠️ 환경변수 {secret_name} 없음 → 건너뜀")
            continue
        auth = requests.auth.HTTPBasicAuth(WP_USER, pw)
        try:
            cats = get_categories(site_url, auth)
        except Exception as e:
            log(f"   ⚠️ 카테고리 조회 실패: {e}")
            continue

        for old_name, new_name in rename_map.items():
            if old_name == new_name:
                continue
            if old_name in cats:
                ok, status = rename(site_url, auth, cats[old_name]["id"], new_name)
                log(f"   {'✅' if ok else '⚠️'} '{old_name}' -> '{new_name}' (status={status}, count={cats[old_name]['count']})")
            elif new_name in cats:
                log(f"   ℹ️ '{old_name}' 없음, 이미 '{new_name}'로 되어있는 것으로 보임 (건너뜀)")
            else:
                log(f"   ⚠️ '{old_name}' 카테고리를 찾지 못함 (건너뜀)")

    with open("rename_categories_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(_LOG))


if __name__ == "__main__":
    main()
