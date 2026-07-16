import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autopost_mega as am

site = next(s for s in am.SITES_CONFIG if s["url"] == "https://k-health365.com")
keyword = am.load_keyword(site["keywords_file"], site["url"], "노안 예방 루틴")

result = {"site": site["url"], "keyword": keyword}
try:
    reporter = am.pick_reporter(site)
    prompt = am.make_site_prompt(keyword, site, reporter)
    raw = am.generate_content_gemini(prompt)
    result["raw_response_length"] = len(raw)

    body_raw, title, meta, faq = am.extract_meta_and_faq(raw)
    body, tags = am.extract_tags(body_raw, keyword, site["theme"], site["lang"])
    result["body_length"] = len(re.sub(r'<[^>]+>', '', body))
    result["tags"] = tags
    result["meta_desc"] = meta
    result["faq_count"] = len(faq)

    final_title = am.build_diverse_title(keyword, site["lang"], site_url=site["url"])
    result["final_title"] = final_title

    score = am.estimate_seo_score(final_title, body, meta, tags, faq, ["x", "x", "x"], keyword)
    result["seo_score"] = score
    result["body_preview"] = re.sub(r'<[^>]+>', ' ', body)[:600]
    result["success"] = True
except Exception as e:
    result["success"] = False
    result["error"] = str(e)

with open("prompt_test_final.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2)[:3000])
