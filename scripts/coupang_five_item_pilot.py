import os, requests, html, sys, json
from requests.auth import HTTPBasicAuth

BASE="https://k-health365.com"
USER=os.getenv("WP_USER","huh0303@gmail.com")
PASS=os.getenv("KHEALTH365COM","")
if not PASS: raise SystemExit("KHEALTH365COM secret missing")
S=requests.Session(); S.auth=HTTPBasicAuth(USER,PASS)
links=[
("관절엔 콘드로이친 1200","관절 건강을 주제로 한 제품 선택지","https://link.coupang.com/a/ihKqEBmP48"),
("고려은단 칼슘·마그네슘·비타민D·K2","뼈 건강과 영양 균형을 함께 살펴볼 때","https://link.coupang.com/a/ihPTujzeyy"),
("순수식품 rTG 오메가3 + 비타민D","일상적인 영양 관리 선택지","https://link.coupang.com/a/ihaVByREei"),
("고려은단 멀티비타민 올인원 우먼 60 플러스","종합적인 비타민·미네랄 보충 선택지","https://link.coupang.com/a/ihPGNw5JzU"),
("쿠팡에서 다른 상품 둘러보기","위 제품 외 다른 브랜드와 상품을 직접 비교","https://link.coupang.com/a/ihRMHfQzKf"),
]
marker="<!-- coupang-five-product-pilot-20261031 -->"
r=S.get(BASE+"/wp-json/wp/v2/posts",params={"status":"publish","per_page":100,"page":1,"orderby":"date","order":"desc","_fields":"id,link,date,featured_media,title,content"},timeout=30)
r.raise_for_status()
posts=r.json()
matches=[]
for p in posts:
 t=html.unescape(p["title"]["rendered"])
 if any(k in t for k in ("관절","뼈 건강","골다공증")):
  matches.append((p,t))
if not matches:
 raise SystemExit("최근 100개 공개글에서 관절/뼈 건강 주제 글을 찾지 못했습니다. 수정 없음.")
p,title=matches[0]
if marker in p["content"]["rendered"]:
 raise SystemExit(f"Pilot marker already exists on post {p['id']}; no duplicate insert.")
cards=[]
for name,desc,url in links:
 cards.append(f'''<li style="list-style:none;border:1px solid #e5e7eb;border-radius:9px;padding:14px;margin:10px 0;">
 <div style="font-weight:700;font-size:16px;margin-bottom:5px;">{name}</div>
 <div style="font-size:13px;color:#555;margin-bottom:10px;">{desc}</div>
 <a href="{url}" target="_blank" rel="sponsored nofollow noopener" style="display:inline-block;background:#1769aa;color:#fff;text-decoration:none;padding:9px 16px;border-radius:6px;">쿠팡에서 상품 확인하기</a>
 </li>''')
section=marker+'''
<section class="coupang-five-product-pilot" style="margin:28px 0;padding:18px;border:1px solid #ddd;border-radius:12px;">
<h2 style="margin-top:0;">함께 살펴볼 만한 건강 관련 상품 5가지</h2>
<p>관절과 뼈 건강에 관심이 있을 때 함께 비교해 볼 수 있는 영양 관련 제품들입니다. 성분과 섭취 대상, 주의사항은 각 제품의 상세 설명을 확인하세요.</p>
<ul style="padding:0;margin:0;">'''+''.join(cards)+'''</ul>
<p style="font-size:12px;color:#666;margin-bottom:0;">'''+ "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다." +'''</p>
</section>'''
# Update using rendered content, retaining post metadata; WordPress content is updated only.
newbody=p["content"]["rendered"].rstrip()+"\n"+section
u=S.post(BASE+f"/wp-json/wp/v2/posts/{p['id']}",json={"content":newbody},timeout=40)
u.raise_for_status()
# readback
v=S.get(BASE+f"/wp-json/wp/v2/posts/{p['id']}",params={"_fields":"id,link,date,featured_media,status,content"},timeout=30)
v.raise_for_status(); q=v.json(); body=q["content"]["rendered"]
ok=all(x in body for x in [marker]+[x[2] for x in links]) and q["status"]=="publish" and q["date"]==p["date"] and q["featured_media"]==p["featured_media"]
print(json.dumps({"ok":ok,"post_id":p["id"],"title":title,"url":q["link"],"products":len(links),"status":q["status"],"date_preserved":q["date"]==p["date"],"featured_media_preserved":q["featured_media"]==p["featured_media"],"all_five_links_readback":all(x[2] in body for x in links)},ensure_ascii=False))
if not ok: sys.exit(2)
