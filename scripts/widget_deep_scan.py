import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER


def check_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/widgets", auth=(WP_USER, pw), timeout=25)
    except Exception as e:
        return {"site": site_url, "error": str(e)}
    if r.status_code != 200:
        return {"site": site_url, "error": f"widgets_status_{r.status_code}"}

    widgets = r.json()
    suspects = []
    for w in widgets:
        rendered = w.get("rendered", "") or ""
        dead_links = len(re.findall(r'href=["\']#["\']', rendered))
        if dead_links > 0 or "websitedemos.net" in rendered:
            preview = re.sub(r'<[^>]+>', ' ', rendered)
            preview = re.sub(r'\s+', ' ', preview).strip()[:150]
            suspects.append({
                "id": w.get("id"), "sidebar": w.get("sidebar"),
                "dead_link_count": dead_links,
                "has_demo_domain": "websitedemos.net" in rendered,
                "text_preview": preview
            })

    return {"site": site_url, "total_widgets": len(widgets), "suspects": suspects}


if __name__ == "__main__":
    results = [check_site(s) for s in SITES_CONFIG]
    with open("widget_deep_scan.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    for r in results:
        err = r.get("error", "")
        sus = r.get("suspects", [])
        flag = "⚠️" if sus or err else "✅"
        print(f"{flag} {r['site']:32s} 의심위젯:{len(sus)} {err[:30]}")
