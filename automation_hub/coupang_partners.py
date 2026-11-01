"""Shared, soft-quota Coupang Partners footer for WordPress and Blogger."""
from __future__ import annotations
import html, json, re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- LONDON-COUPANG-PARTNERS-START -->"
END = "<!-- LONDON-COUPANG-PARTNERS-END -->"
LEGACY_MARKERS = ((START, END), ("<!-- KHEALTH365-COUPANG-START -->", "<!-- KHEALTH365-COUPANG-END -->"))
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
POLICY_PATH = ROOT / "config/affiliate/london-shared-policy.json"

CATEGORY_TERMS = {
    "k_beauty_olive_young": ("beauty", "skincare", "toner", "serum", "sunscreen", "cream", "cleanser", "에센스", "토너", "선크림", "화장품", "스킨", "앰플"),
    "k_health_supplements": ("health", "supplement", "vitamin", "omega", "probiotic", "lutein", "collagen", "칼슘", "비타민", "오메가", "유산균", "건강", "영양제", "콜라겐"),
    "korea_digital_esim_sim": ("esim", "e-sim", "sim card", "usim", "유심", "이심", "데이터"),
    "korea_lifestyle_hot_items": ("kitchen", "travel", "household", "daily", "lifestyle", "생활", "주방", "여행", "생활용품", "핫아이템"),
}
def _load_json(path):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError): return None

def _resolve_site_key(site_id):
    raw = str(site_id or "").strip()
    if raw.startswith("http"):
        host = urlparse(raw).netloc.lower().split(":")[0]
        registry = _load_json(ROOT / "config/automation_hub_sites.json") or {}
        for site in registry.get("sites", []):
            if urlparse(str(site.get("url", ""))).netloc.lower().split(":")[0] == host:
                sid = str(site.get("site_id", ""))
                return sid[3:] if sid.startswith("wp_") else sid
        return host
    key = raw.lower()
    if key.startswith("blogger_"):
        key = key[len("blogger_"):]
    if key.startswith("wp_"):
        key = key[len("wp_"):]
    return key

def _candidate(raw, source):
    if not isinstance(raw, dict): return None
    url = raw.get("affiliate_url") or raw.get("url")
    title = raw.get("title_ko") or raw.get("product_title") or raw.get("title") or raw.get("display_title_en")
    image = raw.get("official_image_url") or raw.get("image_url")
    status = raw.get("status", "")
    account_owned = raw.get("affiliate_confirmed") is True or (
        raw.get("verified_account_owned") is True and raw.get("capture_source") == "coupang_partners_portal"
    ) or status == "VERIFIED_ACCOUNT_GENERATED"
    if not (isinstance(url, str) and url.startswith("https://link.coupang.com/")): return None
    if not (isinstance(title, str) and title.strip() and isinstance(image, str) and image.startswith("https://")): return None
    if not account_owned: return None
    host = urlparse(image).netloc.lower()
    if "coupangcdn.com" not in host: return None
    price_raw = raw.get("price_krw") or raw.get("price") or raw.get("displayed_price") or ""
    digits = re.sub(r"[^0-9]", "", str(price_raw))
    price = int(digits) if digits else None
    return {"url": url, "title": title.strip(), "image": image, "source": source, "price_krw": price,
            "category": str(raw.get("category", "")).lower(),
            "search_text": " ".join([title, str(raw.get("query","")), str(raw.get("category","")), str(raw.get("relevance","")), str(raw.get("description_en",""))]).lower()}

def load_candidates(site_id=""):
    key = _resolve_site_key(site_id)
    paths = []
    # Each site consumes only its own catalog. These two product pools have
    # explicit site_scope declarations and are never spread across the fleet.
    if key in {"oliveyoung", "kskin365"}:
        paths.append((ROOT / "data/affiliate/oliveyoung-kskin365-verified-product-pool.json", "beauty"))
    if key == "khealth365":
        paths.extend([
            (ROOT / "config/affiliate/k-health365-sitewide-10.json", "health"),
            (ROOT / "config/affiliate/k-health365-products.json", "health"),
        ])
    # Standard per-site catalog locations for future portal captures.
    paths.extend([
        (ROOT / f"data/affiliate/catalogs/{key}.json", key),
        (ROOT / f"data/affiliate/{key}-products.json", key),
        (ROOT / f"config/affiliate/catalogs/{key}.json", key),
    ])
    out, seen = [], set()
    for path, source in paths:
        data = _load_json(path)
        rows = data.get("products", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        for raw in rows:
            item = _candidate(raw, source)
            if item and item["url"] not in seen:
                seen.add(item["url"]); out.append(item)
    # Legacy portal captures are also scoped to the exact site's placement map.
    fleet = _load_json(ROOT / "data/affiliate/fleet-placements.json") or {}
    for post in (fleet.get("sites", {}).get(key + ".com", []) or fleet.get("sites", {}).get(key, [])):
        for raw in post.get("products", []):
            item = _candidate(raw, key)
            if item and item["url"] not in seen:
                seen.add(item["url"]); out.append(item)
    return out

def _score(item, text):
    stop = {"the","and","for","with","from","your","how","what","when","where","why","into","this","that","are","was","is","of","in","on","to","a","an"}
    tokens = set(re.findall(r"[a-z0-9가-힣]{2,}", text.lower())) - stop
    words = set(re.findall(r"[a-z0-9가-힣]{2,}", item["search_text"])) - stop
    return len(tokens & words)

def _category(item):
    raw = item.get("category", "")
    if raw in {"kbeauty", "beauty", "toner", "serum", "mask", "cleanser", "moisturizer", "sunscreen", "device", "luxury"}: return "k_beauty_olive_young"
    if raw in {"health", "k_health", "supplement", "vitamin"}: return "k_health_supplements"
    if raw in {"korean_life", "korea_life", "daily_life", "lifestyle"}: return "korea_lifestyle_hot_items"
    if raw in {"digital", "esim", "usim", "sim"}: return "korea_digital_esim_sim"
    s = item["search_text"]
    for cat, terms in CATEGORY_TERMS.items():
        if any(term in s for term in terms): return cat
    return "korea_lifestyle_hot_items"

def select_products(title, article_text, site_id="", limit=10):
    pool = load_candidates(site_id)
    if not pool: return []
    clean_text = article_text or ""
    for old_start, old_end in LEGACY_MARKERS:
        clean_text = re.sub(re.escape(old_start) + r".*?" + re.escape(old_end), " ", clean_text, flags=re.S)
    subject = f"{title} {clean_text[:5000]}"
    ranked = sorted(pool, key=lambda p: (_score(p, subject), p.get("price_krw") is not None and p["price_krw"] <= 30000, p["source"] == "beauty"), reverse=True)
    chosen, used = [], set()
    # First two are always selected by article relevance, not by a rigid category quota.
    for item in ranked:
        if len(chosen) >= min(2, limit): break
        if item["url"] not in used:
            chosen.append(item); used.add(item["url"])
    # Then softly seek the 2/2/2/2 category mix; missing categories are filled by best remaining products.
    for cat in ("korea_lifestyle_hot_items", "k_beauty_olive_young", "k_health_supplements", "korea_digital_esim_sim"):
        cat_items = [p for p in ranked if _category(p) == cat and p["url"] not in used]
        for item in cat_items[:2]:
            if len(chosen) >= limit: break
            chosen.append(item); used.add(item["url"])
    for item in ranked:
        if len(chosen) >= limit: break
        if item["url"] not in used:
            chosen.append(item); used.add(item["url"])
    return chosen[:limit]

def render_footer(title, article_text, site_id="", lang="en"):
    products = select_products(title, article_text, site_id)
    if not products: return ""
    cards = []
    for p in products:
        url, image, name = (html.escape(p[k], quote=True) for k in ("url","image","title"))
        cards.append(
            '<article class="london-coupang-card"><a href="' + url + '" target="_blank" rel="sponsored nofollow noopener">'
            '<img src="' + image + '" alt="' + name + '" loading="lazy" decoding="async">'
            '<span>' + name + '</span></a><a class="london-coupang-button" href="' + url
            + '" target="_blank" rel="sponsored nofollow noopener">상품 확인</a></article>'
        )
    heading = "함께 살펴볼 상품" if lang == "ko" else "Products to Explore"
    return (START + '<section class="london-coupang-wrap" aria-label="Coupang Partners products">'
        '<style>.london-coupang-wrap{margin:30px 0;padding:18px;border:1px solid #e5e7eb;border-radius:12px}'
        '.london-coupang-wrap h2{font-size:20px;margin:0 0 10px}.london-coupang-disclosure{font-size:12px;color:#666;margin:0 0 14px}'
        '.london-coupang-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}'
        '.london-coupang-card{min-width:0;border:1px solid #e5e7eb;border-radius:10px;padding:10px;text-align:center;display:flex;flex-direction:column}'
        '.london-coupang-card img{width:100%;height:145px;object-fit:contain}.london-coupang-card span{display:block;font-size:13px;line-height:1.45;margin:8px 0;overflow-wrap:anywhere}'
        '.london-coupang-button{margin-top:auto;background:#17365d;color:#fff!important;text-decoration:none;padding:8px;border-radius:7px;font-size:12px}'
        '@media(max-width:760px){.london-coupang-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.london-coupang-card img{height:125px}}</style>'
        '<h2>' + heading + '</h2><p class="london-coupang-disclosure">' + DISCLOSURE + '</p>'
        '<div class="london-coupang-grid">' + ''.join(cards) + '</div></section>' + END)

def apply_footer(content, title, site_id="", lang="en"):
    """Replace shared/K-Health legacy marker blocks or append once; never duplicate."""
    content = content or ""
    footer_source = content
    for old_start, old_end in LEGACY_MARKERS:
        a = footer_source.find(old_start)
        b = footer_source.find(old_end, a + len(old_start)) if a >= 0 else -1
        if a >= 0 and b >= 0:
            footer_source = footer_source[:a] + footer_source[b + len(old_end):]
    footer = render_footer(title, footer_source, site_id, lang)
    if not footer:
        return content
    for old_start, old_end in LEGACY_MARKERS:
        a = content.find(old_start)
        b = content.find(old_end, a + len(old_start)) if a >= 0 else -1
        if a >= 0 and b >= 0:
            before, after = content[:a], content[b + len(old_end):]
            if before.rstrip().endswith("<p>"):
                before = before.rstrip()[:-3]
            if after.lstrip().startswith("</p>"):
                after = after.lstrip()[4:]
            return before.rstrip() + "\n" + footer + "\n" + after.lstrip()
    # Unknown legacy affiliate markup is preserved for explicit migration review.
    if "link.coupang.com/" in content or "쿠팡 파트너스 활동의 일환" in content:
        return content
    return content.rstrip() + ("\n" if content.strip() else "") + footer
