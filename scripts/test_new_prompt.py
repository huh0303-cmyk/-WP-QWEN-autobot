import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autopost_mega as am

site = next(s for s in am.SITES_CONFIG if s["url"] == "https://k-health365.com")
keyword = am.load_keyword(site["keywords_file"], site["url"], "노안 예방 루틴")

result = {"site": site["url"], "keyword": keyword}
try:
    ok = am.process_one(site, keyword)
    result["success"] = ok
except Exception as e:
    result["success"] = False
    result["error"] = str(e)

with open("prompt_test_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
