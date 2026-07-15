import os, sys, json, requests

out = {}

for site_url in ["https://jobkorea365.com", "https://sis-korea.com"]:
    entry = {}

    try:
        r = requests.get(f"{site_url}/robots.txt", timeout=20)
        entry["robots_status"] = r.status_code
        entry["robots_content"] = r.text[:1000]
    except Exception as e:
        entry["robots_error"] = str(e)

    try:
        r2 = requests.get(f"{site_url}/ads.txt", timeout=20)
        entry["ads_txt_status"] = r2.status_code
        entry["ads_txt_content"] = r2.text[:200]
    except Exception as e:
        entry["ads_txt_error"] = str(e)

    try:
        r3 = requests.get(site_url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        entry["homepage_normal_ua_status"] = r3.status_code
    except Exception as e:
        entry["homepage_normal_ua_error"] = str(e)

    try:
        r4 = requests.get(site_url, timeout=20, headers={
            "User-Agent": "Mediapartners-Google"
        })
        entry["homepage_adsense_ua_status"] = r4.status_code
        entry["homepage_adsense_ua_len"] = len(r4.text)
    except Exception as e:
        entry["homepage_adsense_ua_error"] = str(e)

    try:
        r5 = requests.get(site_url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        })
        entry["homepage_googlebot_ua_status"] = r5.status_code
    except Exception as e:
        entry["homepage_googlebot_ua_error"] = str(e)

    out[site_url] = entry

with open("crawler_access_check.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
