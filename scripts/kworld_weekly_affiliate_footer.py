"""Idempotent SeoulMall + weekly ten Coupang products footer for Kworld365."""
import html,json,re
from pathlib import Path
from bs4 import BeautifulSoup

CATALOG=Path(__file__).resolve().parents[1]/"config/affiliate/global-weekly-10.json"
STORE="https://influencers.coupang.com/s/seoulshop"
MARKER="kworld-weekly-affiliate-v1"

def render():
    data=json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    items=[x for x in data["items"] if x.get("enabled") and x.get("affiliate_confirmed")]
    if len(items)!=10 or len({x["url"] for x in items})!=10:
        raise ValueError("Weekly affiliate catalog must contain exactly ten distinct verified products")
    cards=[]
    for x in items:
        name=html.escape(x.get("display_title_en") or x["title"])
        url=html.escape(x["url"],quote=True)
        img=html.escape(x["image_url"],quote=True)
        cards.append(f'<a href="{url}" rel="sponsored nofollow noopener" target="_blank" style="display:block;text-decoration:none;color:#18344e;border:1px solid #e0e6ed;border-radius:10px;padding:12px;background:white"><img src="{img}" alt="{name}" loading="lazy" style="width:100%;height:140px;object-fit:contain"/><span style="display:block;font-size:14px;line-height:1.45;margin-top:9px;font-weight:650">{name}</span></a>')
    return (f'<section id="{MARKER}" style="max-width:780px;margin:36px auto 0;border-top:3px solid #d9a441;padding:24px 0;font-family:inherit">'
        '<h2 style="font-size:1.4rem;color:#17365d">Discover SeoulMall</h2>'
        f'<p style="line-height:1.8">Beyond BTS, Discover Korea. Explore our curated Korean products at <a href="{STORE}" rel="sponsored nofollow noopener" target="_blank">SeoulMall</a>.</p>'
        '<h2 style="font-size:1.3rem;color:#17365d;margin-top:22px">This Week’s 10 Coupang Picks</h2>'
        '<p style="font-size:13px;color:#556">Affiliate disclosure: We may earn a commission from qualifying purchases through these links, at no additional cost to you.</p>'
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:14px">'+''.join(cards)+'</div></section>')

def replace(html_text):
    soup=BeautifulSoup(html_text or "","html.parser")
    for node in soup.find_all(id=MARKER):
        node.decompose()
    # Remove previous exact generated footer without affecting article or other ads.
    return str(soup)+render()
