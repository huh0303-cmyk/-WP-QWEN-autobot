#!/usr/bin/env python3
"""Render the public weekly Coupang shelf from the locked canonical catalog."""
import json
from html import escape
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'config/affiliate/global-weekly-10.json'
OUTPUT=ROOT/'docs/weekly-affiliate-shelf.html'
data=json.loads(CATALOG.read_text(encoding='utf-8-sig'))
items=data.get('items',[])
health=[x for x in items if x.get('category')=='health_functional_foods']
beauty=[x for x in items if x.get('category')=='k_beauty_skincare']
if data.get('source_of_truth') is not True or len(items)!=10 or len(health)!=5 or len(beauty)!=5:
    raise SystemExit('Global weekly catalog must be the source of truth with exactly five health and five beauty products.')
for item in items:
    if item.get('enabled') is not True or item.get('affiliate_confirmed') is not True:
        raise SystemExit(f"Unverified or disabled catalog item: {item.get('id')}")
    if not str(item.get('url','')).startswith('https://link.coupang.com/'):
        raise SystemExit(f"Invalid Coupang tracking URL: {item.get('id')}")
    if 'coupangcdn.com' not in str(item.get('image_url','')):
        raise SystemExit(f"Invalid official image URL: {item.get('id')}")

def card(item):
    category='건강기능식품' if item['category']=='health_functional_foods' else 'K-Beauty 스킨케어'
    return (
      '<article class="card"><a class="image" href="'+escape(item['url'],quote=True)+'" target="_blank" rel="sponsored nofollow noopener">'
      '<img src="'+escape(item['image_url'],quote=True)+'" alt="'+escape(item['title'])+'" loading="lazy"></a>'
      '<div class="category">'+category+'</div><h3>'+escape(item['title'])+'</h3><p>'+escape(item.get('description_en',''))+'</p>'
      '<a class="cta" href="'+escape(item['url'],quote=True)+'" target="_blank" rel="sponsored nofollow noopener">쿠팡에서 상품 확인하기</a></article>'
    )
start=data['lock_window']['starts_at'][:10]; end=data['lock_window']['ends_at'][:10]
page=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow"><title>이번 주 K-Beauty & K-Health 추천 10선</title><meta name="description" content="이번 주 공식 쿠팡 파트너스 추천 상품 10선. 건강기능식품 5개와 K-Beauty 스킨케어 5개."><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f7f8fa;color:#172033;font-family:system-ui,'Malgun Gothic',sans-serif}}.wrap{{max-width:1120px;margin:0 auto;padding:28px 18px 56px}}header{{padding:26px 24px;background:#0f2747;color:#fff;border-radius:16px}}.eyebrow{{font-size:12px;letter-spacing:.12em;color:#cbd5e1}}h1{{font-size:clamp(25px,4vw,38px);margin:8px 0}}.sub{{color:#dbeafe;line-height:1.6}}.lock{{margin-top:14px;font-size:12px;color:#dbeafe}}.notice{{margin:18px 0;padding:13px 15px;background:#fff;border:1px solid #dce3ec;border-radius:10px;font-size:13px;line-height:1.6}}h2{{font-size:21px;margin:28px 0 12px}}.grid{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}}.card{{display:flex;flex-direction:column;min-width:0;padding:12px;background:#fff;border:1px solid #e1e6ed;border-radius:12px}}.image{{display:flex;align-items:center;justify-content:center;height:160px}}.image img{{max-width:100%;max-height:150px;object-fit:contain}}.category{{font-size:11px;color:#64748b;margin-top:8px}}h3{{font-size:14px;line-height:1.5;min-height:3em;margin:6px 0}}.card p{{font-size:12px;line-height:1.55;color:#596579;margin:0 0 12px}}.cta{{margin-top:auto;text-align:center;text-decoration:none;background:#17365d;color:#fff;padding:10px 8px;border-radius:8px;font-size:12px;font-weight:700}}footer{{margin-top:26px;padding:14px;background:#eef2f7;border-radius:10px;color:#596579;font-size:12px;line-height:1.7}}@media(max-width:850px){{.grid{{grid-template-columns:repeat(3,minmax(0,1fr))}}}}@media(max-width:560px){{.wrap{{padding:16px 12px 36px}}.grid{{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}}.image{{height:125px}}.image img{{max-height:115px}}.card{{padding:9px}}}}</style></head><body><main class="wrap"><header><div class="eyebrow">LONDON PROJECT · GLOBAL WEEKLY SET</div><h1>이번 주 K-Beauty & K-Health 추천 10선</h1><div class="sub">공식 쿠팡 파트너스 추적 링크와 제휴 이미지로 구성한 주간 추천 상품입니다.</div><div class="lock">상품 세트 고정 기간: {start} – {end} (KST) · 세트 ID: {escape(data['set_id'])}</div></header><div class="notice">이 페이지에는 쿠팡 파트너스 제휴 링크가 포함되어 있습니다. 링크를 통해 구매가 발생하면 운영자가 일정액의 수수료를 제공받을 수 있습니다. 구매자의 추가 비용은 발생하지 않습니다.</div><h2>건강기능식품 · 5개</h2><section class="grid">{''.join(card(x) for x in health)}</section><h2>K-Beauty 스킨케어 · 5개</h2><section class="grid">{''.join(card(x) for x in beauty)}</section><footer>상품 정보와 가격, 재고는 쿠팡 상품 페이지에서 최종 확인해 주세요. 제품의 효과나 건강상 결과를 보장하지 않습니다. 본 상품 구성은 168시간 주간 검토 주기에 따라 변경될 수 있습니다.</footer></main></body></html>'''
OUTPUT.write_text(page,encoding='utf-8')
print(json.dumps({'output':str(OUTPUT),'set_id':data.get('set_id'),'items':len(items),'health':len(health),'beauty':len(beauty)},ensure_ascii=False))
