"""Shared, cross-domain Coupang Partners catalog and deterministic 10-card rotation.

Only account-generated tracking URLs and official Coupang CDN images are eligible.
This module never creates affiliate links or scrapes the logged-in partner portal.
"""
from __future__ import annotations
import csv, hashlib, json, re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
POOL_PATH = ROOT / "data/affiliate/global-coupang-product-pool.json"
CATEGORIES = (
    "k_beauty", "k_electronics", "k_health",
    "korea_travel", "korea_hotels", "k_lifestyle",
)
TARGETS = {
    "k_beauty": 40,
    "k_electronics": 40,
    "k_health": 40,
    "korea_travel": 30,
    "korea_hotels": 30,
    "k_lifestyle": 20,
}
MIN_PRICE_KRW = 10000

def _valid(row: dict) -> tuple[bool, str]:
    url = str(row.get("affiliate_url", "")).strip()
    image = str(row.get("image_url", "")).strip()
    title = str(row.get("title", "")).strip()
    category = str(row.get("category", "")).strip()
    if not re.fullmatch(r"https://link\.coupang\.com/a/[A-Za-z0-9]+", url):
        return False, "not_account_tracking_url"
    if not title or len(title) < 4:
        return False, "missing_title"
    if category not in CATEGORIES:
        return False, "unknown_category"
    if not image.startswith("https://") or "coupangcdn.com" not in urlparse(image).netloc.lower():
        return False, "missing_or_unofficial_image"
    if row.get("affiliate_confirmed") is not True:
        return False, "account_link_not_confirmed"
    try:
        price = int(row.get("price_krw") or 0)
    except (TypeError, ValueError):
        return False, "invalid_price"
    if price and price < MIN_PRICE_KRW:
        return False, "low_price_filter"
    return True, "ok"

def load_pool() -> list[dict]:
    if not POOL_PATH.exists():
        return []
    data = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    products = data.get("products", [])
    good, seen = [], set()
    for row in products:
        ok, _ = _valid(row)
        if ok and row["affiliate_url"] not in seen:
            good.append(row)
            seen.add(row["affiliate_url"])
    return good

def import_csv(csv_path: str | Path, replace: bool = False) -> dict:
    """Import a Coupang Partners portal-exported CSV; never synthesizes URLs."""
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    existing = [] if replace else load_pool()
    by_url = {p["affiliate_url"]: p for p in existing}
    rejected = []
    accepted = 0
    for raw in rows:
        row = dict(raw)
        row["affiliate_confirmed"] = str(row.get("affiliate_confirmed", "")).lower() in {"1", "true", "yes", "confirmed"}
        try:
            row["price_krw"] = int(re.sub(r"[^0-9]", "", str(row.get("price_krw", ""))) or "0")
        except ValueError:
            row["price_krw"] = 0
        ok, reason = _valid(row)
        if not ok:
            rejected.append({"title": row.get("title", ""), "reason": reason})
            continue
        row["popularity_score"] = float(row.get("popularity_score") or 0)
        row["rating"] = float(row.get("rating") or 0)
        row["review_count"] = int(row.get("review_count") or 0)
        row["verified_source"] = "coupang_partners_portal"
        by_url[row["affiliate_url"]] = row
        accepted += 1
    POOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "policy": "cross_domain_shared_pool",
        "targets": TARGETS,
        "products": list(by_url.values()),
    }
    POOL_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {c: sum(1 for p in by_url.values() if p["category"] == c) for c in CATEGORIES}
    return {"accepted": accepted, "total_verified": len(by_url), "category_counts": counts, "rejected": rejected}

def _rank(row: dict, article_text: str, seed: str) -> tuple:
    words = set(re.findall(r"[a-z0-9가-힣]{2,}", article_text.lower()))
    title_words = set(re.findall(r"[a-z0-9가-힣]{2,}", row["title"].lower()))
    relevance = len(words & title_words)
    # Popularity/reviews help prioritize click-worthy items; seeded tie-breaker
    # rotates products reproducibly per post and per site.
    popularity = float(row.get("popularity_score") or 0)
    reviews = int(row.get("review_count") or 0)
    rating = float(row.get("rating") or 0)
    digest = hashlib.sha256((seed + "|" + row["affiliate_url"]).encode()).hexdigest()
    return (relevance, popularity, min(reviews, 100000), rating, digest)

def select_ten(article_text: str, post_key: str, pool: list[dict] | None = None) -> list[dict]:
    """Return 10 unique products; stable per post, rotated across different posts."""
    pool = pool if pool is not None else load_pool()
    if len(pool) < 10:
        raise RuntimeError(f"Need 10 verified products; pool currently has {len(pool)}")
    seed = str(post_key)
    ranked = sorted(pool, key=lambda p: _rank(p, article_text, seed), reverse=True)
    chosen, used = [], set()
    # Category guide: 2 beauty, 2 electronics, 2 health, 1 travel, 1 hotel, 2 lifestyle.
    quotas = {"k_beauty": 2, "k_electronics": 2, "k_health": 2,
              "korea_travel": 1, "korea_hotels": 1, "k_lifestyle": 2}
    for category, quota in quotas.items():
        candidates = [p for p in ranked if p["category"] == category and p["affiliate_url"] not in used]
        for item in candidates[:quota]:
            chosen.append(item)
            used.add(item["affiliate_url"])
    # If a category is underfilled, fill from all remaining verified offers.
    for item in ranked:
        if len(chosen) == 10:
            break
        if item["affiliate_url"] not in used:
            chosen.append(item)
            used.add(item["affiliate_url"])
    if len(chosen) != 10:
        raise RuntimeError("Could not assemble 10 unique verified products")
    return chosen

def render_cards(products: list[dict]) -> str:
    if len(products) != 10 or len({p["affiliate_url"] for p in products}) != 10:
        raise ValueError("Exactly 10 unique products required")
    cards = []
    for p in products:
        title = p["title"].replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
        url = p["affiliate_url"].replace('"', "%22")
        image = p["image_url"].replace('"', "%22")
        cards.append(
            f'<article class="global-coupang-card"><a href="{url}" target="_blank" rel="sponsored nofollow noopener">'
            f'<img src="{image}" alt="{title}" loading="lazy"></a><strong>{title}</strong>'
            f'<a class="global-coupang-cta" href="{url}" target="_blank" rel="sponsored nofollow noopener">쿠팡에서 확인하기</a></article>'
        )
    return (
        '<!-- GLOBAL-COUPANG-10-START --><section class="global-coupang-wrap">'
        '<p class="global-coupang-disclosure">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>'
        '<h2>함께 살펴볼 추천 상품</h2><style>'
        '.global-coupang-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}'
        '.global-coupang-card{border:1px solid #e5e7eb;border-radius:10px;padding:10px;display:flex;flex-direction:column;align-items:center;text-align:center;min-width:0}'
        '.global-coupang-card img{width:100%;height:125px;object-fit:contain}.global-coupang-card strong{font-size:12px;line-height:1.4;margin:8px 0;min-height:2.8em}'
        '.global-coupang-cta{margin-top:auto;background:#17365d;color:white!important;padding:7px 10px;border-radius:6px;text-decoration:none;font-size:12px}'
        '@media(max-width:700px){.global-coupang-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}</style>'
        '<div class="global-coupang-grid">' + "".join(cards) + '</div></section><!-- GLOBAL-COUPANG-10-END -->'
    )
