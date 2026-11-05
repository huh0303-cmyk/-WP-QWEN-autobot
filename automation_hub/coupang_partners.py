"""Shared, soft-quota Coupang Partners footer for WordPress and Blogger."""
from __future__ import annotations
import html, json, re
from pathlib import Path
from urllib.parse import urlparse, urlunparse, unquote

ROOT = Path(__file__).resolve().parents[1]
HEADER_START = "<!-- LONDON-AFFILIATE-HEADER-START -->"
HEADER_END = "<!-- LONDON-AFFILIATE-HEADER-END -->"
START = "<!-- LONDON-COUPANG-PARTNERS-START -->"
END = "<!-- LONDON-COUPANG-PARTNERS-END -->"
LEGACY_MARKERS = ((START, END), ("<!-- KHEALTH365-COUPANG-START -->", "<!-- KHEALTH365-COUPANG-END -->"))
DISCLOSURE = "This post contains Coupang Partners affiliate links. If you purchase through these links, we may earn a commission at no additional cost to you."
COUPANG_TRADEMARK_NOTICE = "Coupang’s trademarks are used under license from Coupang, LLC or its affiliates."
LOGOS = {
    "trip_com": "https://commons.wikimedia.org/wiki/Special:FilePath/Trip.com_logo.svg",
    "olive_young_global": "https://dist.oliveyoung.com/fo/fe126e9b35/resources/images/common/logo.svg",
    "coupang_partners": "https://news.coupang.com/wp-content/uploads/2023/01/coupang-bi-brand-logo-230109-01.jpg",
}
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
    candidates.append(ROOT / "config/affiliate/default-header-buttons.json")
    for path in candidates:
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        buttons = data.get("buttons", [])
        required = {"trip_com", "olive_young_global", "coupang_partners"}
        if len(buttons) != 3 or {x.get("provider") for x in buttons} != required:
            continue
        if any(not str(x.get("affiliate_url", "")).startswith("https://") for x in buttons):
            continue
        # Olive Young's supplied reward-code URL is accepted as a destination
        # link while commission attribution remains explicitly pending.
        olive = next(x for x in buttons if x.get("provider") == "olive_young_global")
        if olive.get("status") != "redirect_test_failed_gate_url_null" and olive.get("verified") is not True:
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
    return {"url": url, "title": title.strip(), "display_title_en": str(raw.get("display_title_en") or raw.get("title_en") or "").strip(),
            "description_en": str(raw.get("description_en") or "").strip(),
            "image": image, "official_tag": official_tag, "source": source, "price_krw": price,
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
    if limit < 10:
        return []
    # K-Health365 uses a fixed ten-product catalog. Reuse the same verified
    # offers in catalog order for every article until an operator replaces it.
    if key == "khealth365":
        fixed_path = ROOT / "config/affiliate/k-health365-sitewide-10.json"
        fixed_rows = _load_json(fixed_path)
        if not isinstance(fixed_rows, list) or len(fixed_rows) != 10:
            return []
        fixed = []
        seen_urls, seen_images = set(), set()
        for raw in fixed_rows:
            item = _candidate(raw, "health")
            if not item or raw.get("enabled") is not True:
                return []
            image_key = _canonical_asset_url(item["image"])
            if item["url"] in seen_urls or not image_key or image_key in seen_images:
                return []
            seen_urls.add(item["url"])
            seen_images.add(image_key)
            fixed.append(item)
        return fixed
    pool = load_candidates(site_id)
    if len(pool) < 10:
        return []
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

def render_header(site_id=""):
    header = load_header_buttons(site_id)
    if not header:
        raise RuntimeError(f"Affiliate header requires Trip.com + Olive Young + Coupang tracking URLs for site={site_id}")
    button_order = ("trip_com", "olive_young_global", "coupang_partners")
    button_map = {item["provider"]: item for item in header["buttons"]}
    buttons = []
    for provider in button_order:
        item = button_map[provider]
        url = html.escape(item["affiliate_url"], quote=True)
        label = html.escape(item["label"])
        logo = html.escape(LOGOS[provider], quote=True)
        # Coupang's current brand guidelines prohibit using its logo as a hyperlink.
        # Keep the official logo visible and provide a separate tracked text link.
        if provider == "coupang_partners":
            buttons.append(f'<div class="london-provider-button {provider}"><img src="{logo}" alt="Coupang" loading="lazy"><a href="{url}" target="_blank" rel="sponsored nofollow noopener">Visit Coupang</a></div>')
        else:
            buttons.append(f'<a class="london-provider-button {provider}" href="{url}" target="_blank" rel="sponsored nofollow noopener" aria-label="{label}"><img src="{logo}" alt="{label}" loading="lazy"></a>')
    return (HEADER_START
        + '<nav class="london-provider-buttons" aria-label="Affiliate partners">' + ''.join(buttons) + '</nav>'
        + '<style>.london-provider-buttons{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0 0 22px;align-items:stretch}'
        '.london-provider-button{min-height:64px;display:flex;align-items:center;justify-content:center;gap:7px;padding:10px;border:1px solid #e5e7eb;border-radius:9px;background:#fff;text-decoration:none!important}'
        '.london-provider-button img{display:block;max-width:100%;width:auto;height:auto;max-height:34px;object-fit:contain}'
        '.london-provider-button.coupang_partners{flex-direction:column}.london-provider-button.coupang_partners img{max-width:125px;max-height:28px}'
        '.london-provider-button.coupang_partners a{font-size:11px;font-weight:700;color:#333;text-decoration:underline}'
        '@media(max-width:520px){.london-provider-buttons{gap:6px}.london-provider-button{min-height:56px;padding:7px}.london-provider-button img{max-height:27px}.london-provider-button.coupang_partners img{max-width:100px;max-height:23px}}</style>'
        + HEADER_END)



def render_footer(title, article_text, site_id="", lang="en"):
    products = select_products(title, article_text, site_id)
    if len(products) != 10:
        raise RuntimeError(f"Coupang footer requires exactly 10 unique verified products for site={site_id}; found {len(products)}")
    cards = []
    for p in products:
        url, image, name = (html.escape(p[k], quote=True) for k in ("url","image","title"))
        category = html.escape(p.get("category", ""))
        cards.append(
            '<article class="london-coupang-card"><a class="london-coupang-image-link" href="' + url + '" target="_blank" rel="sponsored nofollow noopener">'
            '<img src="' + image + '" alt="' + name + '" loading="lazy" decoding="async" referrerpolicy="unsafe-url">'
            '</a><small class="london-coupang-category">' + category + '</small><strong>' + name + '</strong><a class="london-coupang-button" href="' + url
            + '" target="_blank" rel="sponsored nofollow noopener">쿠팡에서 상품 확인</a></article>'
        )
    heading = "함께 살펴볼 추천 상품 10선" if lang == "ko" else "10 Coupang Picks"
    return (START + '<section class="london-coupang-wrap" aria-label="Coupang recommended products">'
        '<style>.london-coupang-wrap{margin:30px 0;padding:18px;border:1px solid #e5e7eb;border-radius:12px}'
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
            class_match = re.search(r"""\bclass\s*=\s*["']([^"']*)["']""", tag, re.I)
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
    """Place provider buttons at article top and the fixed ten-card block at article end."""
    content = _remove_legacy_single_product_modules(content or "")
    clean = content
    marker_pairs = ((HEADER_START, HEADER_END), (START, END), *LEGACY_MARKERS[1:])
    for old_start, old_end in marker_pairs:
        clean = re.sub(re.escape(old_start) + r".*?" + re.escape(old_end), "", clean, flags=re.S)
    header = render_header(site_id)
    footer = render_footer(title, clean, site_id, lang)
    return header + "\n" + clean.lstrip() + ("\n" if clean.strip() else "") + footer
