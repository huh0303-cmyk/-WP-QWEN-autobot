"""Shared, soft-quota Coupang Partners footer for WordPress and Blogger."""
from __future__ import annotations
import html, json, re
from pathlib import Path
from urllib.parse import urlparse, urlunparse, unquote

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
    # Keep Blogger and WordPress destination keys distinct. Product pools and
    # provider links must never silently bleed between different domains.
    if key.startswith("wp_"):
        key = key[len("wp_"):]
    return key

def load_header_buttons(site_id=""):
    key = _resolve_site_key(site_id)
    candidates = [
        ROOT / f"data/affiliate/{key}-header-buttons.json",
        ROOT / f"config/affiliate/header-buttons/{key}.json",
    ]
    for path in candidates:
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        buttons = data.get("buttons", [])
        required = ("coupang_partners", "olive_young_global", "trip_com")
        if tuple(x.get("provider") for x in buttons) != required:
            continue
        if any(not str(x.get("affiliate_url", "")).startswith("https://") for x in buttons):
            continue
        # Olive Young's account reward-code URL is retained as supplied, but its
        # redirect/commission attribution is explicitly marked pending.
        olive = next(x for x in buttons if x.get("provider") == "olive_young_global")
        if olive.get("status") != "redirect_test_failed_gate_url_null" and olive.get("verified") is not True:
            continue
        trip_categories = data.get("trip_com_categories", [])
        if tuple(x.get("key") for x in trip_categories) != ("hotels", "flights", "tours_and_packages"):
            continue
        if any(x.get("verified") is not True or not str(x.get("affiliate_url", "")).startswith("https://") for x in trip_categories):
            continue
        return data
    return None

def _candidate(raw, source):
    if not isinstance(raw, dict): return None
    url = raw.get("affiliate_url") or raw.get("url")
    title = raw.get("title_ko") or raw.get("product_title") or raw.get("title") or raw.get("display_title_en")
    image = raw.get("official_image_url") or raw.get("image_url")
    official_tag = raw.get("official_blog_html_tag") or raw.get("blog_html_tag") or ""
    if not image and isinstance(official_tag, str):
        match = re.search(r"<img[^>]+src=[\x22\x27]([^\x22\x27]+)", official_tag, re.I)
        if match: image = match.group(1)
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
    return {"url": url, "title": title.strip(), "image": image, "official_tag": official_tag, "source": source, "price_krw": price,
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

def _canonical_asset_url(value):
    """Normalize equivalent escaped/unescaped URLs for duplicate-image checks."""
    try:
        parsed = urlparse(str(value or "").strip())
        if not parsed.scheme or not parsed.netloc:
            return ""
        path = unquote(parsed.path)
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))
    except (TypeError, ValueError):
        return ""

def select_products(title, article_text, site_id="", limit=10):
    # Ten unique, verified Coupang offers are mandatory. Never publish a partial block.
    key = _resolve_site_key(site_id)
    pool = load_candidates(site_id)
    if len(pool) < 10 or limit < 10: return []
    clean_text = article_text or ""
    for old_start, old_end in LEGACY_MARKERS:
        clean_text = re.sub(re.escape(old_start) + r".*?" + re.escape(old_end), " ", clean_text, flags=re.S)
    # Never add a product already linked in the article's own content (including
    # a standalone topic recommendation outside the managed footer).
    existing_urls = set(re.findall(r"""https://link\.coupang\.com/a/[A-Za-z0-9]+""", clean_text, re.I))
    existing_images = {
        _canonical_asset_url(src)
        for src in re.findall(r"""<img\b[^>]*\bsrc\s*=\s*["']([^"']+)["']""", clean_text, re.I)
    }
    unique_pool, seen_urls, seen_images = [], set(), set()
    for item in pool:
        image_key = _canonical_asset_url(item.get("image"))
        if item["url"] in existing_urls or (image_key and image_key in existing_images):
            continue
        if item["url"] in seen_urls or not image_key or image_key in seen_images:
            continue
        seen_urls.add(item["url"])
        seen_images.add(image_key)
        unique_pool.append(item)
    pool = unique_pool
    if len(pool) < 10: return []
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
    chosen = chosen[:10] if len(chosen) >= 10 else []
    return chosen

def render_footer(title, article_text, site_id="", lang="en"):
    products = select_products(title, article_text, site_id)
    if len(products) != 10:
        raise RuntimeError(f"Coupang footer requires exactly 10 unique verified products for site={site_id}; found {len(products)}")
    header = load_header_buttons(site_id)
    if not header:
        raise RuntimeError(f"Affiliate header requires verified Coupang + Olive Young + Trip.com buttons and hotel/flight/tour tracking links for site={site_id}")
    provider_buttons = []
    for button in header["buttons"]:
        url = html.escape(button["affiliate_url"], quote=True)
        label = html.escape(button["label"])
        provider_buttons.append(f'<a class="london-provider-button" href="{url}" target="_blank" rel="sponsored nofollow noopener">{label}</a>')
    trip_buttons = []
    for item in header["trip_com_categories"]:
        url = html.escape(item["affiliate_url"], quote=True)
        label = html.escape(item["label"])
        trip_buttons.append(f'<a class="london-trip-category-button" href="{url}" target="_blank" rel="sponsored nofollow noopener">Trip.com ? {label}</a>')
    cards = []
    for p in products:
        url, image, name = (html.escape(p[k], quote=True) for k in ("url","image","title"))
        category = html.escape(p.get("category", ""))
        cards.append(
            '<article class="london-coupang-card"><a class="london-coupang-image-link" href="' + url + '" target="_blank" rel="sponsored nofollow noopener">'
            '<img src="' + image + '" alt="' + name + '" loading="lazy" decoding="async" referrerpolicy="unsafe-url">'
            '</a><small class="london-coupang-category">' + category + '</small><strong>' + name + '</strong><a class="london-coupang-button" href="' + url
            + '" target="_blank" rel="sponsored nofollow noopener">???? ????</a></article>'
        )
    heading = "?? ?? ?? 10?" if lang == "ko" else "10 Coupang Picks"
    return (START + '<section class="london-coupang-wrap" aria-label="Affiliate partners and Coupang products">'
        '<nav class="london-provider-buttons" aria-label="Affiliate partners">' + ''.join(provider_buttons) + '</nav>'
        '<nav class="london-trip-category-buttons" aria-label="Trip.com travel categories">' + ''.join(trip_buttons) + '</nav>'
        '<style>.london-coupang-wrap{margin:30px 0;padding:18px;border:1px solid #e5e7eb;border-radius:12px}'
        '.london-provider-buttons,.london-trip-category-buttons{display:flex;flex-wrap:wrap;gap:9px;margin:0 0 14px}'
        '.london-provider-button{flex:1 1 28%;text-align:center;padding:12px 10px;border-radius:8px;background:#17365d;color:#fff!important;text-decoration:none;font-weight:700}'
        '.london-trip-category-button{flex:1 1 28%;text-align:center;padding:9px 10px;border:1px solid #17365d;border-radius:7px;color:#17365d!important;text-decoration:none;font-size:13px;font-weight:600}'
        '.london-coupang-wrap h2{font-size:20px;margin:14px 0 10px}.london-coupang-disclosure{font-size:12px;color:#666;margin:0 0 14px}'
        '.london-coupang-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;align-items:stretch}'
        '.london-coupang-card{min-width:0;border:1px solid #e5e7eb;border-radius:10px;padding:10px;text-align:center;display:flex;flex-direction:column;background:#fff}'
        '.london-coupang-card img{width:100%;height:155px;object-fit:contain}.london-coupang-card strong{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:13px;line-height:1.45;margin:8px 0;min-height:2.9em;overflow-wrap:anywhere}'
        '.london-coupang-category{font-size:11px;color:#777}.london-coupang-button{margin-top:auto;background:#17365d;color:#fff!important;text-decoration:none;padding:9px 12px;border-radius:7px;font-size:13px;font-weight:700}'
        '@media(max-width:760px){.london-coupang-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.london-coupang-card img{height:125px}}</style>'
        '<h2>' + heading + '</h2><p class="london-coupang-disclosure">' + DISCLOSURE + '</p>'
        '<div class="london-coupang-grid">' + ''.join(cards) + '</div></section>' + END)

def _remove_legacy_single_product_modules(content):
    """Remove only known standalone affiliate-recommendation divs; keep article images."""
    content = content or ""
    tag_re = re.compile(r"</?div\b[^>]*>", re.I | re.S)
    offset = 0
    while True:
        start_tag = None
        for match in tag_re.finditer(content, offset):
            tag = match.group(0)
            if tag.startswith("</"):
                continue
            class_match = re.search(r"""\bclass\\s*=\\s*["']([^"']*)["']""", tag, re.I)
            classes = set((class_match.group(1).split() if class_match else []))
            if "affiliate-recommendation" in classes:
                start_tag = match
                break
        if start_tag is None:
            break
        depth = 1
        end_pos = None
        for match in tag_re.finditer(content, start_tag.end()):
            if match.group(0).startswith("</"):
                depth -= 1
                if depth == 0:
                    end_pos = match.end()
                    break
            else:
                depth += 1
        if end_pos is None:
            break
        block = content[start_tag.start():end_pos]
        # Require both an actual tracked Coupang destination and an image before
        # treating this as the obsolete one-product affiliate module.
        if "link.coupang.com/" in block and re.search(r"<img\b", block, re.I):
            content = content[:start_tag.start()] + content[end_pos:]
            offset = start_tag.start()
        else:
            offset = end_pos
    return content

def apply_footer(content, title, site_id="", lang="en"):
    """Replace shared/K-Health legacy marker blocks or append once; never duplicate."""
    content = _remove_legacy_single_product_modules(content or "")
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
