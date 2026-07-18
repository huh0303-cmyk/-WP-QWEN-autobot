import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, SITE_PERSONA, build_cta_html


def check_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    result = {"site": site_url, "lang": site.get("lang")}

    p = SITE_PERSONA.get(site_url, {})
    result["has_cta_field"] = bool(p.get("cta"))
    result["has_persona"] = bool(p.get("persona_ko") or p.get("persona_en"))
    result["min_chars"] = p.get("min_chars")

    cta_html = build_cta_html(site_url, site.get("lang", "ko"))
    result["cta_html_generated"] = bool(cta_html)

    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                          params={"per_page": 5, "orderby": "date", "order": "desc",
                                  "status": "publish", "_fields": "id,title,content,date"}, timeout=30)
        posts = r.json() if r.status_code == 200 else []
    except Exception as e:
        result["posts_error"] = str(e)
        posts = []

    cta_present_count = 0
    sample_titles = []
    for post in posts:
        content = post.get("content", {}).get("rendered", "")
        if 'class="cta-box"' in content:
            cta_present_count += 1
        sample_titles.append({"title": post["title"]["rendered"][:50], "date": post.get("date")})

    result["recent_posts_checked"] = len(posts)
    result["recent_posts_with_cta"] = cta_present_count
    result["sample_titles"] = sample_titles

    return result


if __name__ == "__main__":
    results = [check_site(s) for s in SITES_CONFIG]
    with open("persona_cta_audit.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    for r in results:
        err = r.get("error", "") or r.get("posts_error", "")
        ok = (r.get("has_cta_field") and r.get("has_persona") and r.get("cta_html_generated")
              and r.get("recent_posts_with_cta", 0) == r.get("recent_posts_checked", 0)
              and r.get("recent_posts_checked", 0) > 0)
        flag = "✅" if ok and not err else "⚠️"
        print(f"{flag} {r['site']:32s} lang:{r.get('lang')} CTA필드:{r.get('has_cta_field')} "
              f"최근글CTA:{r.get('recent_posts_with_cta')}/{r.get('recent_posts_checked')} {err[:30]}")
