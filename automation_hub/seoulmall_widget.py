# -*- coding: utf-8 -*-
"""SeoulMall standardized responsive end-of-post card for WordPress and Blogger.

Standardized for WP25 and Blogger33 fleets with:
- Canonical Hub: https://influencers.coupang.com/s/seoulshop
- rel="nofollow sponsored" link attributes
- Statutory FTC compliance notices (KR + EN)
- Mobile-first responsive flex/grid layouts
- Vertical-aware card themes (K-Health, K-Beauty, General SeoulMall)
- Dynamic loading from data/seoulmall_curated_catalog.json when available
- AdSense safety gating (throttled on 24 review sites, active on k-health365 & approved blogs)
"""
from __future__ import annotations
import html
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

CANONICAL_HUB = "https://influencers.coupang.com/s/seoulshop"
STORE_URL = os.getenv("SEOULMALL_STORE_URL", CANONICAL_HUB).strip()
MARKER = "<!-- seoulmall-store-widget:v2 -->"
LEGACY_MARKERS = ("<!-- seoulmall-store-widget:v1 -->", "<!-- seoulmall-widget -->")

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "seoulmall_curated_catalog.json"

# AdSense safety whitelist: domains cleared for full affiliate card rendering
APPROVED_AFFILIATE_DOMAINS = {
    "k-health365.com",
    "job.k-health365.com",
}

FTC_DISCLOSURE_KR = "※ 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
FTC_DISCLOSURE_EN = "※ This article contains Coupang Partners affiliate links. We may earn a commission at no extra cost to you."


def load_curated_catalog() -> Optional[Dict[str, Any]]:
    """Load weekly curated items from catalog if present."""
    if CATALOG_PATH.exists():
        try:
            return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def render_card(
    store_url: str = STORE_URL,
    vertical: str = "general",
    sub_id: str = "",
    title_override: Optional[str] = None,
    include_product_pills: bool = True,
) -> str:
    """Render a responsive, accessible SEOULMALL footer card with nofollow sponsored links."""
    base_url = store_url if store_url.startswith("https://") else CANONICAL_HUB
    target_url = base_url
    if sub_id:
        sep = "&" if "?" in target_url else "?"
        target_url = f"{target_url}{sep}subId={html.escape(sub_id, quote=True)}"
    url = html.escape(target_url, quote=True)

    catalog = load_curated_catalog()

    # Vertical-specific configuration
    if vertical == "health":
        badge = "K-Health Official Curation"
        headline = title_override or "SEOULMALL 헬스 & 영양제 케어"
        tagline = "식약처 인증 관절 영양제, 고순도 MSM, 콘드로이친 특가 모음"
        default_chips = ["관절·연골", "혈당·대사", "수면·마그네슘", "항산화·면역", "간 건강·피로"]
        primary_color = "#059669"
        gradient = "linear-gradient(135deg, #f0fdf4 0%, #ffffff 50%, #ecfdf5 100%)"
        border_color = "#bbf7d0"
        btn_bg = "linear-gradient(90deg, #059669, #10b981)"
        cat_key = "k_health"
    elif vertical == "beauty":
        badge = "K-Beauty Curated Store"
        headline = title_override or "SEOULMALL 프리미엄 K-스킨케어"
        tagline = "올리브영 베스트셀러, 장벽 강화 세라마이드 & 진정 토너 특가"
        default_chips = ["피부장벽 리페어", "시카·어성초 진정", "PDRN·콜라겐", "데일리 선케어", "마스크팩"]
        primary_color = "#db2777"
        gradient = "linear-gradient(135deg, #fdf2f8 0%, #ffffff 50%, #fce7f3 100%)"
        border_color = "#fbcfe8"
        btn_bg = "linear-gradient(90deg, #db2777, #f43f5e)"
        cat_key = "k_beauty"
    else:
        badge = "Coupang Influencer Official Store"
        headline = title_override or "SeoulMall (서울몰)"
        tagline = "Beyond BTS, Discover Authentic Korean Lifestyle & Wellness"
        default_chips = ["K-Health", "K-Beauty", "Korea Travel", "Sim & eSIM", "Living & Food"]
        primary_color = "#7c3aed"
        gradient = "linear-gradient(135deg, #faf5ff 0%, #ffffff 50%, #f3e8ff 100%)"
        border_color = "#e9d5ff"
        btn_bg = "linear-gradient(90deg, #7c3aed, #ec4899)"
        cat_key = ""

    # Dynamic chips from catalog if available
    chips = default_chips
    if include_product_pills and catalog and cat_key in catalog.get("categories", {}):
        top_items = catalog["categories"][cat_key][:5]
        item_chips = [item.get("name", "").split()[0] + " " + item.get("name", "").split()[1] if len(item.get("name", "").split()) > 1 else item.get("name", "") for item in top_items]
        if item_chips:
            chips = item_chips

    chips_html = "".join(f"<span>{html.escape(c)}</span>" for c in chips)

    return f"""{MARKER}
<section class="seoulmall-card-container" aria-label="SeoulMall Curated Store">
  <style>
    .seoulmall-card-container {{
      box-sizing: border-box;
      max-width: 880px;
      margin: 36px auto 20px auto;
      padding: clamp(18px, 4vw, 28px);
      border: 1px solid {border_color};
      border-radius: 16px;
      background: {gradient};
      text-align: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
    }}
    .seoulmall-card-container * {{ box-sizing: border-box; }}
    .seoulmall-badge {{
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: {primary_color};
      background: #ffffff;
      padding: 4px 12px;
      border-radius: 999px;
      border: 1px solid {border_color};
      margin-bottom: 10px;
    }}
    .seoulmall-title {{
      margin: 6px 0 8px 0;
      color: #1e293b;
      font-size: clamp(22px, 4vw, 30px);
      font-weight: 800;
      line-height: 1.25;
    }}
    .seoulmall-tagline {{
      margin: 0 auto 16px auto;
      color: #475569;
      font-size: clamp(13px, 2.5vw, 15px);
      line-height: 1.5;
      max-width: 600px;
    }}
    .seoulmall-chips {{
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 6px;
      margin: 14px 0 20px 0;
    }}
    .seoulmall-chips span {{
      padding: 6px 12px;
      border: 1px solid #e2e8f0;
      border-radius: 999px;
      background: #ffffff;
      color: #334155;
      font-size: 12px;
      font-weight: 600;
    }}
    .seoulmall-cta-btn {{
      display: inline-block;
      max-width: 100%;
      padding: 13px 28px;
      border-radius: 999px;
      background: {btn_bg};
      color: #ffffff !important;
      text-decoration: none !important;
      font-weight: 700;
      font-size: 15px;
      letter-spacing: -0.01em;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .seoulmall-cta-btn:hover {{
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.16);
    }}
    .seoulmall-ftc {{
      margin: 16px 0 0 0;
      color: #64748b;
      font-size: 11px;
      line-height: 1.5;
      border-top: 1px dashed #cbd5e1;
      padding-top: 12px;
    }}
    .seoulmall-ftc p {{ margin: 2px 0; }}
    @media (max-width: 600px) {{
      .seoulmall-card-container {{ margin: 24px 0; padding: 18px 12px; }}
      .seoulmall-cta-btn {{ width: 100%; padding: 13px 16px; font-size: 14px; }}
      .seoulmall-chips span {{ font-size: 11px; padding: 5px 9px; }}
    }}
  </style>
  <div class="seoulmall-badge">{badge}</div>
  <h3 class="seoulmall-title">{html.escape(headline)}</h3>
  <p class="seoulmall-tagline">{html.escape(tagline)}</p>
  <div class="seoulmall-chips">{chips_html}</div>
  <a class="seoulmall-cta-btn" href="{url}" target="_blank" rel="nofollow sponsored noopener">SEOULMALL 추천 상품 보러가기 →</a>
  <div class="seoulmall-ftc">
    <p>{FTC_DISCLOSURE_KR}</p>
    <p>{FTC_DISCLOSURE_EN}</p>
  </div>
</section>
"""


def should_render_for_domain(domain: str) -> bool:
    """AdSense safety gate: full insertion on approved sites; throttled/deferred on review sites."""
    clean_domain = domain.lower().replace("https://", "").replace("http://", "").strip("/")
    if clean_domain in APPROVED_AFFILIATE_DOMAINS:
        return True
    if clean_domain.endswith(".blogspot.com"):
        return True
    # 24 pending review WP sites return False during initial review
    return False


def append_card_safe(
    content: str,
    domain: str,
    vertical: str = "general",
    sub_id: str = "",
    force: bool = False,
) -> str:
    """Safely append SEOULMALL card to post content respecting AdSense gate."""
    content = content or ""
    if MARKER in content or any(m in content for m in LEGACY_MARKERS):
        return content

    if not force and not should_render_for_domain(domain):
        # Gatekeeper policy: deferred on unapproved AdSense sites to prevent thin-affiliate flags
        return content

    card_html = render_card(vertical=vertical, sub_id=sub_id)
    return content.rstrip() + "\n\n" + card_html + "\n"
