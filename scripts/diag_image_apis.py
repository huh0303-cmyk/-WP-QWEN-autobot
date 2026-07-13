import os, sys, json, requests

PIXABAY_KEY = os.getenv("PIXABAY_KEY")
PEXELS_KEY = os.getenv("PEXELS_KEY")

result = {
    "pixabay_key_present": bool(PIXABAY_KEY),
    "pixabay_key_len": len(PIXABAY_KEY) if PIXABAY_KEY else 0,
    "pexels_key_present": bool(PEXELS_KEY),
    "pexels_key_len": len(PEXELS_KEY) if PEXELS_KEY else 0,
}

if PIXABAY_KEY:
    try:
        r = requests.get(
            f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=Korea&image_type=photo&per_page=20&safesearch=true&min_width=600",
            timeout=15)
        result["pixabay_status"] = r.status_code
        body = r.json()
        result["pixabay_total_hits"] = body.get("totalHits")
        result["pixabay_hits_count"] = len(body.get("hits", []))
        if r.status_code != 200:
            result["pixabay_error_body"] = r.text[:300]
    except Exception as e:
        result["pixabay_exception"] = str(e)

if PEXELS_KEY:
    try:
        r = requests.get("https://api.pexels.com/v1/search?query=Korea&per_page=20",
                          headers={"Authorization": PEXELS_KEY}, timeout=15)
        result["pexels_status"] = r.status_code
        if r.status_code == 200:
            body = r.json()
            result["pexels_photos_count"] = len(body.get("photos", []))
        else:
            result["pexels_error_body"] = r.text[:300]
    except Exception as e:
        result["pexels_exception"] = str(e)

with open("img_diag_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
