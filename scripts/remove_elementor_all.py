#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""27개 사이트 Elementor 완전 제거: 플러그인 + 템플릿(elementor_library) + DB 찌꺼기(postmeta/options)
GP Premium을 깨끗하게 쓸 수 있도록 REST API 기반으로 정리한다.
"""
import os
import requests

WP_USER = "huh0303@gmail.com"

SITES = [
    {"url": "https://k-health365.com",        "wp_pass_env": "KHEALTH365COM"},
    {"url": "https://koreamedicaltour.com",   "wp_pass_env": "KOREAMEDICALTOURCOM"},
    {"url": "https://koreainvest365.com",     "wp_pass_env": "KOREAINVEST365COM"},
    {"url": "https://ki-korea.com",           "wp_pass_env": "KIKOREACOM"},
    {"url": "https://koreainsurance365.com",  "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://kfinance365.com",        "wp_pass_env": "KFINANCE365COM"},
    {"url": "https://koreataxnlaw.com",       "wp_pass_env": "KOREATAXNLAWCOM"},
    {"url": "https://koreacrypto365.com",     "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://krealestate365.com",     "wp_pass_env": "KREALESTATE365COM"},
    {"url": "https://ktech365.com",           "wp_pass_env": "KTECH365COM"},
    {"url": "https://kskin365.com",           "wp_pass_env": "KSKIN365COM"},
    {"url": "https://oliveyoungkorea.com",    "wp_pass_env": "OLIVEYOUNGKOREACOM"},
    {"url": "https://kworld365.com",          "wp_pass_env": "KWORLD365COM"},
    {"url": "https://k-trip365.com",          "wp_pass_env": "KTRIP365COM"},
    {"url": "https://k-visa365.com",          "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreawedding365.com",    "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://kstudy365.com",          "wp_pass_env": "KSTUDY365COM"},
    {"url": "https://studyinkorea365.com",    "wp_pass_env": "STUDYINKOREA365COM"},
    {"url": "https://kieca-korea.org",        "wp_pass_env": "KIECAKOREAORG"},
    {"url": "https://ksa-korea.org",          "wp_pass_env": "KSAKOREAORG"},
    {"url": "https://sis-korea.com",          "wp_pass_env": "SISKOREACOM"},
    {"url": "https://jobkorea365.com",        "wp_pass_env": "JOBKOREA365COM"},
    {"url": "https://jobinkorea365.com",      "wp_pass_env": "JOBINKOREA365COM"},
    {"url": "https://jobkoreaglobal.com",     "wp_pass_env": "JOBKOREAGLOBALCOM"},
    {"url": "https://korea365.org",           "wp_pass_env": "KOREA365ORG"},
    {"url": "https://koreanews365.com",       "wp_pass_env": "KOREANEWS365COM"},
    {"url": "https://theseouljournal.com",    "wp_pass_env": "THESEOULJOURNALCOM"},
]

ELEMENTOR_SLUGS = [
    "elementor/elementor",
    "elementor-pro/elementor-pro",
    "essential-addons-for-elementor-lite/essential_addons_elementor.php",
    "happy-elementor-addons/happy-elementor-addons.php",
    "premium-addons-for-elementor/premium-addons-for-elementor.php",
]

# 원클릭 DB 청소용 PHP 스니펫 (WPCode 경유). 1회 실행 후 자동으로 콘텐츠를 비활성 처리한다.
DB_CLEANUP_PHP = r"""<?php
add_action('init', function () {
    if (get_option('_elementor_purge_done_v1')) return;
    global $wpdb;
    $wpdb->query("DELETE FROM {$wpdb->postmeta} WHERE meta_key LIKE '\\_elementor%'");
    $wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '\\_elementor%'");
    $wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE 'elementor%'");
    $wpdb->query("DELETE FROM {$wpdb->posts} WHERE post_type = 'elementor_library'");
    update_option('_elementor_purge_done_v1', 1);
});
"""


def auth(pw):
    return requests.auth.HTTPBasicAuth(WP_USER, pw)


def get_plugins(url, pw):
    try:
        r = requests.get(f"{url}/wp-json/wp/v2/plugins", auth=auth(pw), timeout=20)
        if r.status_code == 200 and isinstance(r.json(), list):
            return r.json()
    except Exception:
        pass
    return []


def remove_plugin(url, pw, plugin_id, log):
    # 1) 비활성화
    r1 = requests.post(f"{url}/wp-json/wp/v2/plugins/{plugin_id}",
                        auth=auth(pw), json={"status": "inactive"}, timeout=20)
    if r1.status_code not in (200, 201):
        log(f"    ⚠️ 비활성화 실패 {plugin_id} (HTTP {r1.status_code})")
        return False
    # 2) 삭제
    r2 = requests.delete(f"{url}/wp-json/wp/v2/plugins/{plugin_id}", auth=auth(pw), timeout=20)
    if r2.status_code in (200, 201):
        log(f"    ✅ 삭제 완료: {plugin_id}")
        return True
    log(f"    ⚠️ 삭제 실패 {plugin_id} (HTTP {r2.status_code}) — 비활성화는 됨")
    return False


def remove_elementor_library_posts(url, pw, log):
    removed = 0
    for post_type in ["elementor_library", "wp_template", "wp_template_part"]:
        try:
            r = requests.get(f"{url}/wp-json/wp/v2/{post_type}",
                              auth=auth(pw), params={"per_page": 100, "status": "any"}, timeout=15)
            if r.status_code == 200 and isinstance(r.json(), list):
                for item in r.json():
                    pid = item.get("id")
                    if pid:
                        dr = requests.delete(f"{url}/wp-json/wp/v2/{post_type}/{pid}",
                                              auth=auth(pw), params={"force": True}, timeout=10)
                        if dr.status_code in (200, 201):
                            removed += 1
        except Exception:
            pass
    if removed:
        log(f"    🗑️ elementor_library/template 잔여 {removed}개 삭제")
    return removed


def inject_db_cleanup_snippet(url, pw, log):
    """WPCode PHP 스니펫으로 postmeta/options/elementor_library DB 잔재 일괄 삭제"""
    base = f"{url}/wp-json/wp/v2"
    snippet_data = {
        "title": "Elementor DB Purge (one-time)",
        "content": DB_CLEANUP_PHP,
        "code_type": "php",
        "location": "everywhere",
        "status": "publish",
    }
    try:
        r = requests.get(f"{base}/wpcode-snippets", auth=auth(pw), params={"per_page": 50}, timeout=15)
        if r.status_code == 200 and isinstance(r.json(), list):
            for s in r.json():
                t = s.get("title", {})
                ts = t.get("rendered", "") if isinstance(t, dict) else str(t)
                if "Elementor DB Purge" in ts:
                    ur = requests.post(f"{base}/wpcode-snippets/{s['id']}",
                                        auth=auth(pw), json=snippet_data, timeout=15)
                    if ur.status_code in (200, 201):
                        log("    ✅ DB 청소 스니펫 갱신 (다음 페이지뷰에서 실행됨)")
                        # 트리거: 홈페이지 한번 호출해서 init 훅 실행되게 함
                        try:
                            requests.get(url, timeout=10)
                        except Exception:
                            pass
                        return True
        cr = requests.post(f"{base}/wpcode-snippets", auth=auth(pw), json=snippet_data, timeout=15)
        if cr.status_code in (200, 201):
            log("    ✅ DB 청소 스니펫 생성 (다음 페이지뷰에서 실행됨)")
            try:
                requests.get(url, timeout=10)
            except Exception:
                pass
            return True
        log(f"    ⚠️ WPCode 스니펫 API 사용 불가 (HTTP {cr.status_code}) — postmeta/options 수동 정리 필요")
    except Exception as e:
        log(f"    ⚠️ DB 청소 스니펫 오류: {e}")
    return False


def main():
    lines = []

    def log(m):
        print(m)
        lines.append(m)

    for site in SITES:
        url = site["url"]
        wp_pass = os.getenv(site["wp_pass_env"], "")
        log(f"\n🌐 {url}")
        if not wp_pass:
            log("  ⚠️ 비밀번호 없음 — 스킵")
            continue

        plugins = get_plugins(url, wp_pass)
        found = [p.get("plugin", "") for p in plugins if "elementor" in p.get("plugin", "").lower()]

        if not found:
            log("  ✅ Elementor 플러그인 없음")
        else:
            log(f"  🔎 발견: {found}")
            for pid in found:
                remove_plugin(url, wp_pass, pid, log)

        remove_elementor_library_posts(url, wp_pass, log)
        inject_db_cleanup_snippet(url, wp_pass, log)

    with open("remove_elementor_all_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
