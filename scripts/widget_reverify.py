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
        return {"site": site_url, "error": f"status_{r.status_code}"}
    widgets = r.json()
    suspects = []
    for w in widgets:
        rendered = w.get("rendered", "") or ""
        dead_links = len(re.findall(r'href=["\']#["\']', rendered))
        if dead_links > 0 or "websitedemos.net" in rendered or "product highlight" in rendered.lower():
            suspects.append({"id": w.get("id"), "sidebar": w.get("sidebar")})
    return {"site": site_url, "suspects": suspects}


if __name__ == "__main__":
    results = [check_site(s) for s in SITES_CONFIG]
    with open("widget_reverify.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    ok = 0
    for r in results:
        err = r.get("error", "")
        sus = r.get("suspects", [])
        if not sus and not err:
            ok += 1
        flag = "⚠️" if sus or err else "✅"
        print(f"{flag} {r['site']:32s} 의심:{sus} {err[:30]}")
    print(f"\n{ok}/{len(results)} 완전 정상")
