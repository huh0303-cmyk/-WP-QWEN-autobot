# -*- coding: utf-8 -*-
"""SeoulMall end-of-post widget helpers for WordPress HTML content."""
from __future__ import annotations
import html
import os

STORE_URL = os.getenv("SEOULMALL_STORE_URL", "https://influencers.coupang.com/s/seoulshop").strip()
MARKER = "<!-- seoulmall-store-widget:v1 -->"

def render_widget(store_url: str = STORE_URL) -> str:
    url = html.escape(store_url, quote=True)
    return f\'''{MARKER}
<section class="seoulmall-widget" aria-label="SeoulMall shopping">
  <style>
    .seoulmall-widget{{box-sizing:border-box;max-width:960px;margin:32px auto;padding:clamp(18px,4vw,30px);border:1px solid #f0d9e8;border-radius:20px;background:linear-gradient(135deg,#fff 0%,#fff5fa 55%,#f5f1ff 100%);text-align:center;font-family:Arial,sans-serif;}}
    .seoulmall-widget *{{box-sizing:border-box;}}
    .seoulmall-widget .sm-kicker{{font-size:12px;letter-spacing:.12em;color:#8b6680;font-weight:700;text-transform:uppercase;}}
    .seoulmall-widget h2{{margin:8px 0;color:#c92c80;font-size:clamp(26px,5vw,38px);line-height:1.15;}}
    .seoulmall-widget .sm-tagline{{margin:0 auto 18px;color:#4c4050;font-size:15px;}}
    .seoulmall-widget .sm-cats{{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin:18px 0 22px;}}
    .seoulmall-widget .sm-cats span{{padding:9px 12px;border:1px solid #f0dce8;border-radius:999px;background:#fff;color:#493b48;font-size:13px;font-weight:700;}}
    .seoulmall-widget .sm-button{{display:inline-block;max-width:100%;padding:14px 24px;border-radius:999px;background:linear-gradient(90deg,#7135e9,#ec2585);color:#fff!important;text-decoration:none!important;font-weight:700;font-size:16px;}}
    .seoulmall-widget .sm-note{{margin:16px 0 0;color:#756b73;font-size:11px;line-height:1.6;}}
    @media(max-width:480px){{.seoulmall-widget{{margin:22px 0;padding:18px 14px;}}.seoulmall-widget .sm-cats span{{font-size:12px;padding:8px 10px;}}.seoulmall-widget .sm-button{{width:100%;padding:13px 12px;font-size:14px;}}}}
  </style>
  <div class="sm-kicker">Coupang Influencer Official Store</div>
  <h2>SeoulMall</h2>
  <p class="sm-tagline">Beyond BTS, Discover Korea.</p>
  <div class="sm-cats">
    <span>K-Beauty</span><span>K-Health</span><span>K-Tour</span>
    <span>K-Hotels</span><span>K-Digitals</span><span>K-Life</span>
  </div>
  <a class="sm-button" href="{url}" target="_blank" rel="sponsored nofollow noopener">서울몰 전체 상품 보기 →</a>
  <p class="sm-note">쿠팡 파트너스 활동을 통해 일정액의 수수료를 제공받을 수 있습니다.</p>
</section>
\'''


def append_widget(content: str, store_url: str = STORE_URL) -> str:
    """Append exactly once; leave existing content untouched if already present."""
    content = content or ""
    if MARKER in content:
        return content
    return content.rstrip() + "\n\n" + render_widget(store_url) + "\n"


def has_widget(content: str) -> bool:
    return MARKER in (content or "")
