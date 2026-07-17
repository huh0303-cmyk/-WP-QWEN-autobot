import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autopost_mega as am

site = next(s for s in am.SITES_CONFIG if s["url"] == "https://ki-korea.com")
keyword = am.load_keyword(site["keywords_file"], site["url"], "Korea stock market 2026")

result = {"site": site["url"], "keyword": keyword, "lang": site["lang"]}
try:
    reporter = am.pick_reporter(site)
    prompt = am.make_site_prompt(keyword, site, reporter)
    result["prompt_preview"] = prompt[:500]

    raw = am.generate_content_gemini(prompt)
    body_raw, title, meta, faq = am.extract_meta_and_faq(raw)
    body, tags = am.extract_tags(body_raw, keyword, site["theme"], site["lang"])
    result["body_length"] = len(re.sub(r'<[^>]+>', '', body))

    cta_html = am.build_cta_html(site["url"], site["lang"])
    result["cta_html"] = cta_html
    result["success"] = True
except Exception as e:
    result["success"] = False
    result["error"] = str(e)

with open("persona_update_test.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2)[:2500])
