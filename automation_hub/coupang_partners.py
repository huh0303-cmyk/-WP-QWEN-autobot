"""Shared, soft-quota Coupang Partners footer for WordPress and Blogger."""
from __future__ import annotations
import html, json, re
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlparse, urlunparse, unquote

ROOT = Path(__file__).resolve().parents[1]
HEADER_START = "<!-- LONDON-AFFILIATE-HEADER-START -->"
HEADER_END = "<!-- LONDON-AFFILIATE-HEADER-END -->"
START = "<!-- LONDON-COUPANG-PARTNERS-START -->"
END = "<!-- LONDON-COUPANG-PARTNERS-END -->"
LEGACY_MARKERS = ((START, END), ("<!-- KHEALTH365-COUPANG-START -->", "<!-- KHEALTH365-COUPANG-END -->"))
DISCLOSURE = "This post contains Coupang Partners affiliate links. If you visit Coupang through one of these links and make a purchase within 24 hours, including a purchase of another eligible product, we may earn a commission at no additional cost to you. Attribution rules, cancellations and returns may affect commission eligibility. / 이 게시물에는 쿠팡 파트너스 제휴 링크가 포함되어 있습니다. 이 링크를 통해 쿠팡에 방문한 뒤 24시간 이내에 다른 상품을 구매하더라도 운영정책상 실적으로 인정되는 구매라면 수수료를 제공받을 수 있습니다. 구매 경로의 최종 기여, 주문 취소 및 반품 등에 따라 수수료가 인정되지 않을 수 있습니다."
COUPANG_TRADEMARK_NOTICE = "Coupang’s trademarks are used under license from Coupang, LLC or its affiliates."
# Official company/partner logo artwork. Keep these as image assets; never
# substitute text-only labels, emoji, or CSS-drawn wordmarks.
LOGOS = {
    "coupang_partners": "https://commons.wikimedia.org/wiki/Special:FilePath/Coupang_logo.svg",
    "olive_young_global": "https://dist.oliveyoung.com/fo/fe126e9b35/resources/images/common/logo.svg",
    "trip_com": "https://commons.wikimedia.org/wiki/Special:FilePath/Trip.com_logo.svg",
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
        ROOT / "config/affiliate/default-header-buttons.json",
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
        coupang = next(x for x in buttons if x.get("provider") == "coupang_partners")
        olive = next(x for x in buttons if x.get("provider") == "olive_young_global")
        trip = next(x for x in buttons if x.get("provider") == "trip_com")
        if coupang.get("verified") is not True or trip.get("verified") is not True:
            continue
        if olive.get("verified") is not True and olive.get("status") != "redirect_test_failed_gate_url_null":
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
    raw = str(item.get("category", "")).lower()
    if raw in {"kbeauty", "beauty", "beauty_cosmetics", "toner", "serum", "mask", "cleanser", "moisturizer", "sunscreen", "k_beauty_skincare"}:
        return "k_beauty_skincare"
    if raw in {"health", "k_health", "supplement", "supplements", "vitamin", "health_supplements", "health_functional_foods"}:
        return "health_functional_foods"
    s = item["search_text"]
    if any(term in s for term in CATEGORY_TERMS["k_beauty_olive_young"]):
        return "k_beauty_skincare"
    if any(term in s for term in CATEGORY_TERMS["k_health_supplements"]):
        return "health_functional_foods"
    return "other"

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
    """Use the same verified ten-product global weekly set on every destination."""
    if limit < 10:
        return []
    weekly_data = _load_json(ROOT / "config/affiliate/global-weekly-10.json")
    if not isinstance(weekly_data, dict) or weekly_data.get("source_of_truth") is not True:
        raise RuntimeError("Global weekly Coupang catalog is missing or is not the source of truth.")
    window = weekly_data.get("lock_window", {})
    try:
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        starts_at = datetime.fromisoformat(window["starts_at"])
        ends_at = datetime.fromisoformat(window["ends_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Global weekly catalog must define valid KST starts_at and ends_at.") from exc
    if not (starts_at <= now < ends_at):
        raise RuntimeError(f"Global weekly set is outside its 168-hour lock window ({starts_at.isoformat()} to {ends_at.isoformat()}); update the weekly set before publishing.")
    if weekly_data.get("status") != "weekly_catalog_ready_global_rollout_approved":
        raise RuntimeError("Global weekly catalog has not passed the owner-approved fleet rollout gate.")
    fixed = []
    seen_urls, seen_images = set(), set()
    counts = {"health_functional_foods": 0, "k_beauty_skincare": 0}
    for raw in weekly_data.get("items", []):
        if not isinstance(raw, dict) or raw.get("enabled") is not True or raw.get("affiliate_confirmed") is not True:
            continue
        category = str(raw.get("category", "")).lower()
        if category not in counts:
            continue
        item = _candidate(raw, "global_weekly")
        if not item:
            continue
        image_key = item["image"].strip()
        if item["url"] in seen_urls or image_key in seen_images:
            continue
        if "/image/affiliate/banner/" not in urlparse(image_key).path:
            continue
        item["display_title_en"] = raw.get("display_title_en", "")
        item["description_en"] = raw.get("description_en", "")
        item["category"] = category
        seen_urls.add(item["url"])
        seen_images.add(image_key)
        counts[category] += 1
        fixed.append(item)
    if len(fixed) != 10 or counts != {"health_functional_foods": 5, "k_beauty_skincare": 5}:
        raise ValueError(f"Global weekly catalog must contain 10 unique verified Coupang offers (5 health + 5 beauty); found {len(fixed)} and {counts}.")
    # The owner-approved weekly display order is K-Beauty first, then K-Health.
    fixed.sort(key=lambda item: 0 if item.get("category") == "k_beauty_skincare" else 1)
    return fixed

def render_header(site_id=""):
    """Render three official company logos in one horizontal footer row."""
    header = load_header_buttons(site_id)
    if not header:
        raise RuntimeError(f"Affiliate header requires the three approved partner destinations for site={site_id}")
    button_map = {item.get("provider"): item for item in header.get("buttons", [])}
    coupang = button_map["coupang_partners"]
    olive = button_map["olive_young_global"]
    trip = button_map["trip_com"]
    partners = [
        ("coupang_partners", coupang, LOGOS["coupang_partners"], "Coupang company logo"),
        ("olive_young_global", olive, LOGOS["olive_young_global"], "OLIVE YOUNG company logo"),
        ("trip_com", trip, LOGOS["trip_com"], "Trip.com company logo"),
    ]
    cards = []
    for provider, item, default_logo, alt in partners:
        logo = html.escape(item.get("logo_url") or default_logo, quote=True)
        url = html.escape(item["affiliate_url"], quote=True)
        cards.append(
            '<a class="london-partner-logo ' + provider + '" href="' + url
            + '" target="_blank" rel="sponsored nofollow noopener" aria-label="' + html.escape(alt, quote=True) + '">'
            + '<img src="' + logo + '" alt="' + html.escape(alt, quote=True)
            + '" loading="lazy" decoding="async"></a>'
        )
    return (HEADER_START
        + '<div class="london-affiliate-partner-strip" aria-label="Three affiliate partner company logos">'
        + ''.join(cards) + '</div>'
        + '<style>.london-affiliate-partner-strip{box-sizing:border-box;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));align-items:center;gap:12px;width:100%;margin:0 0 18px;padding:12px;border:1px solid #e5e7eb;border-radius:12px;background:#fff}'
        '.london-partner-logo{box-sizing:border-box;display:flex;min-width:0;min-height:78px;align-items:center;justify-content:center;padding:10px;border-radius:8px;background:#fff;text-decoration:none!important}'
        '.london-partner-logo img{display:block;width:100%;max-width:210px;height:58px;object-fit:contain}'
        '.london-partner-logo.coupang_partners{border-top:4px solid #e87518}'
        '.london-partner-logo.olive_young_global{border-top:4px solid #168a43}'
        '.london-partner-logo.trip_com{border-top:4px solid #1769d2}'
        '@media(max-width:520px){.london-affiliate-partner-strip{gap:4px;padding:6px}.london-partner-logo{min-height:58px;padding:4px}.london-partner-logo img{height:38px}}</style>'
        + HEADER_END)

def render_footer(title, article_text, site_id="", lang="en"):
    products = select_products(title, article_text, site_id)
    if not products:
        raise RuntimeError("No verified destination-specific affiliate products are available.")
    products = products[:10]
    cards = []
    for p in products:
        url, image, name = (html.escape(p[k], quote=True) for k in ("url","image","title"))
        category = html.escape(p.get("category", "").replace("_", " ").title())
        title_en = html.escape(p["title"] if lang == "ko" else (p.get("display_title_en") or p["title"]))
        description = ("성분과 함량, 원료 및 섭취 방법을 상품 페이지에서 확인하세요." if lang == "ko" and _category(p) == "health_functional_foods" else "피부 타입과 전성분, 사용 방법을 상품 페이지에서 확인하세요." if lang == "ko" else p.get("description_en")) or {
            "korea_digital_esim_sim": "Stay connected in Korea with convenient mobile data and SIM or eSIM access.",
            "korea_travel_power": "A practical travel accessory designed to make charging devices easier on the go.",
            "k_beauty_olive_young": "A Korean beauty pick for everyday skincare and personal care routines.",
            "k_health_supplements": "A wellness supplement option. Review the ingredients and directions before use.",
            "korea_lifestyle_hot_items": "A useful everyday item selected for convenience at home or while traveling.",
        }.get(_category(p), "A useful product selected for everyday convenience. Check the product page for full specifications.")
        description = html.escape(description)
        cards.append(
            '<article class="london-coupang-card"><a class="london-coupang-image-link" href="' + url + '" target="_blank" rel="sponsored nofollow noopener">'
            '<img src="' + image + '" alt="' + title_en + '" loading="lazy" decoding="async" referrerpolicy="unsafe-url">'
            '</a><small class="london-coupang-category">' + category + '</small><strong>' + title_en + '</strong>'
            '<p class="london-coupang-description">' + description + '</p><a class="london-coupang-button" href="' + url
            + '" target="_blank" rel="sponsored nofollow noopener">Shop on Coupang</a></article>'
        )
    heading = ("함께 살펴볼 추천 상품 10선" if lang == "ko" else f"{len(products)} Recommended Products") if products else "Affiliate Disclosure"
    partner_strip = render_header(site_id)
    return (START + '<section class="london-coupang-wrap" aria-label="Coupang recommended products">'
        + partner_strip
        + '<style>.london-coupang-wrap{margin:30px 0;padding:18px;border:1px solid #e5e7eb;border-radius:12px}'
        '.london-coupang-wrap h2{font-size:20px;margin:14px 0 10px}.london-coupang-disclosure{font-size:12px;color:#666;margin:0 0 14px}'
        '.london-coupang-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;align-items:stretch}'
        '.london-coupang-card{min-width:0;border:1px solid #e5e7eb;border-radius:10px;padding:10px;text-align:center;display:flex;flex-direction:column;background:#fff}'
        '.london-coupang-card img{width:100%;height:155px;object-fit:contain}.london-coupang-card strong{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:13px;line-height:1.45;margin:8px 0;min-height:2.9em;overflow-wrap:anywhere}'
        '.london-coupang-category{font-size:11px;color:#777}.london-coupang-description{font-size:12px;line-height:1.5;color:#555;margin:0 0 12px;min-height:4.5em}.london-coupang-button{margin-top:auto;background:#17365d;color:#fff!important;text-decoration:none;padding:9px 12px;border-radius:7px;font-size:13px;font-weight:700}'
        '.london-coupang-legal{font-size:10px;color:#777;text-align:center;margin:4px 0 0}'
        '@media(max-width:760px){.london-coupang-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.london-coupang-card img{height:125px}}</style>'
        '<h2>' + heading + '</h2><p class="london-coupang-disclosure">' + DISCLOSURE + '</p>'
        '<div class="london-coupang-grid">' + ''.join(cards) + '</div>'
        '<p class="london-coupang-legal">' + COUPANG_TRADEMARK_NOTICE + '</p></section>' + END)

def _remove_managed_affiliate_blocks(content):
    """Remove legacy header/footer containers wherever they were previously inserted."""
    tag_re = re.compile(r"</?(div|section|nav)\b[^>]*>", re.I | re.S)
    targets = {
        "london-affiliate-partner-strip",
        "london-coupang-wrap",
        "khealth365-coupang-wrap",
        "affiliate-recommendation",
    }
    offset = 0
    while True:
        opening = None
        for match in tag_re.finditer(content, offset):
            tag = match.group(0)
            if tag.startswith("</"):
                continue
            cm = re.search(r"""\bclass\s*=\s*["']([^"']*)["']""", tag, re.I)
            classes = set(cm.group(1).split()) if cm else set()
            if classes & targets:
                opening = match
                break
        if opening is None:
            break
        tag_name = re.match(r"<(div|section|nav)", opening.group(0), re.I).group(1).lower()
        depth = 1
        end_pos = None
        for match in tag_re.finditer(content, opening.end()):
            token = match.group(0)
            token_name = re.match(r"</?(div|section|nav)", token, re.I).group(1).lower()
            if token_name != tag_name:
                continue
            if token.startswith("</"):
                depth -= 1
                if depth == 0:
                    end_pos = match.end()
                    break
            else:
                depth += 1
        if end_pos is None:
            break
        content = content[:opening.start()] + content[end_pos:]
        offset = opening.start()
    # Drop the obsolete style block from the old partner strip; the new footer
    # supplies a single, self-contained style block.
    content = re.sub(r"<style[^>]*>[\s\S]*?(?:london-affiliate-partner-strip|london-coupang-wrap)[\s\S]*?</style>", "", content, flags=re.I)
    return content


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

def _remove_legacy_provider_and_product_shelf(content):
    """Remove the old text-button/Trip category/ Korean product shelf as one block.

    The legacy block starts at its Coupang Partners tracked button and ends
    after the old three-provider logo row. The new canonical footer is rebuilt
    immediately afterwards, so article copy and related links remain intact.
    """
    content = content or ""
    start = re.search(
        r'<a\b(?=[^>]*href=[\x22\x27]https://link\.coupang\.com/)[^>]*>\s*Coupang\s+Partners\s*</a>',
        content, re.I | re.S
    )
    if not start:
        return content
    tail = content[start.start():]
    logo = re.search(
        r'<a\b(?=[^>]*aria-label=[\x22\x27]Trip\.com company logo[\x22\x27])[^>]*>[\s\S]*?</a>',
        tail, re.I
    )
    if logo:
        return content[:start.start()] + tail[logo.end():]
    # Fallback for older versions without a logo row: remove only the legacy
    # block up to the next canonical category/tags/footer boundary.
    boundary = re.search(r'<(?:div|section)\b[^>]*(?:class=[\x22\x27][^\x22\x27]*(?:post-categories|entry-footer|tags-links)[^\x22\x27]*[\x22\x27])', tail, re.I)
    if boundary:
        return content[:start.start()] + tail[boundary.start():]
    return content

def apply_footer(content, title, site_id="", lang="en"):
    """Render one idempotent commerce footer followed by the SeoulMall storefront CTA.

    This is the shared final-content boundary for WordPress and Blogger.  Keeping
    the storefront here (rather than in individual publishers) ensures that a
    new post cannot receive its verified product cards while silently missing the
    broader SeoulMall destination.
    """
    content = _remove_managed_affiliate_blocks(content or "")
    content = _remove_legacy_single_product_modules(content)
    content = _remove_legacy_provider_and_product_shelf(content)
    clean = content
    marker_pairs = ((HEADER_START, HEADER_END), (START, END), *LEGACY_MARKERS[1:])
    for old_start, old_end in marker_pairs:
        clean = re.sub(re.escape(old_start) + r".*?" + re.escape(old_end), "", clean, flags=re.S)
    footer = render_footer(title, clean, site_id, lang)
    from .seoulmall_widget import append_widget
    rendered = clean.rstrip() + ("\n" if clean.strip() else "") + footer
    return append_widget(rendered)
