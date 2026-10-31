#!/usr/bin/env python3
# Append only verified, account-owned Coupang HTML creatives to relevant published JobKorea365 posts.
import os, requests, time, json, re, sys
from requests.auth import HTTPBasicAuth
BASE='https://jobkorea365.com'
USER='huh0303@gmail.com'; PW=os.getenv('JOBKOREA365COM','')
DISC='이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.'
PRODUCTS=[
 {'id':'glove','html':'<a href="https://link.coupang.com/a/iiyoxj40WG" target="_blank" referrerpolicy="unsafe-url"><img src="https://image9.coupangcdn.com/image/affiliate/banner/18b6b7bbb39a158a194724a92eecb3e4@2x.jpg" alt="쓰리엠 슈퍼그립 장갑 200, 그레이, 10개" width="120" height="240"></a>','rx':r'\b(PPE|personal protective equipment|safety glove|protective glove|factory floor|manufacturing workplace|industrial worksite)\b'},
 {'id':'korean-language','html':'<a href="https://link.coupang.com/a/iiwBtrzlQa" target="_blank" referrerpolicy="unsafe-url"><img src="https://image6.coupangcdn.com/image/affiliate/banner/a024a08f8b0232329a2c917f5cf04b1e@2x.jpg" alt="배워서 바로 써먹는 찰떡 한국어, 필수 회화, 시대고시기획" width="120" height="240"></a>','rx':r'\b(Korean office slang|office slang|workplace conversation|Korean language learning|Korean conversation|Korean vocabulary)\b'},
 {'id':'interview-guide','html':'<a href="https://link.coupang.com/a/iiwTIacwpw" target="_blank" referrerpolicy="unsafe-url"><img src="https://image8.coupangcdn.com/image/affiliate/banner/5dbd284f2fbdf01a500cb9aab465d56b@2x.jpg" alt="Job Interview: An Essential Guide, Bravex Publications" width="120" height="240"></a>','rx':r'\b(interview preparation|interview questions|job interview|interview process|interview skills)\b'},
]
if not PW: raise SystemExit('Missing JOBKOREA365COM secret')
s=requests.Session(); s.auth=HTTPBasicAuth(USER,PW); s.headers['User-Agent']='LondonProject-Coupang-Verified-Insertion/1.0'
results=[]; page=1
while True:
 r=s.get(BASE+'/wp-json/wp/v2/posts',params={'status':'publish','per_page':100,'page':page,'_fields':'id,status,date,featured_media,link,title,content'},timeout=40)
 if r.status_code!=200: raise SystemExit(f'LIST_FAILED {r.status_code} {r.text[:250]}')
 posts=r.json()
 if not posts: break
 for p in posts:
  raw=p.get('content',{}).get('raw') or p.get('content',{}).get('rendered') or ''
  txt=re.sub(r'<[^>]+>',' ',raw); txt=re.sub(r'\s+',' ',txt)
  selected=[x for x in PRODUCTS if re.search(x['rx'],txt,re.I)]
  # Every remaining JobKorea365 article concerns work or settlement in Korea; the verified Korean conversation book is the relevant general-purpose item for foreign job seekers and workers.
  if not selected: selected=[PRODUCTS[1]]
  # Avoid repeating existing affiliate content or any prior disclosure block.
  if 'coupang.com/a/' in raw or DISC in raw: continue
  block='\n<section class="coupang-partners-products" style="margin:24px 0;padding:16px;border-top:1px solid #ddd"><p><strong>관련 추천 상품</strong></p><div style="display:flex;flex-wrap:wrap;gap:16px">'+''.join(x['html'] for x in selected)+'</div><p style="font-size:12px;color:#666">'+DISC+'</p></section>\n'
  new=raw.rstrip()+block
  u=s.post(BASE+f"/wp-json/wp/v2/posts/{p['id']}",json={'content':new},timeout=40)
  if u.status_code not in (200,201):
   results.append({'id':p['id'],'url':p.get('link'),'status':'WRITE_FAILED','http':u.status_code}); continue
  v=s.get(BASE+f"/wp-json/wp/v2/posts/{p['id']}",params={'context':'edit','_fields':'id,status,date,featured_media,content'},timeout=40)
  if v.status_code==200:
   q=v.json(); body=q.get('content',{}).get('raw') or q.get('content',{}).get('rendered') or ''
   ok=all(x['html'].split(' target=')[0] in body for x in selected) and DISC in body and q.get('status')==p.get('status') and q.get('date')==p.get('date') and q.get('featured_media')==p.get('featured_media')
   results.append({'id':p['id'],'url':p.get('link'),'products':[x['id'] for x in selected],'status':'VERIFIED' if ok else 'VERIFY_FAILED'})
  else: results.append({'id':p['id'],'url':p.get('link'),'status':'READBACK_FAILED','http':v.status_code})
  time.sleep(.2)
 if len(posts)<100: break
 page+=1
print(json.dumps(results,ensure_ascii=False,indent=2))
open('jobkorea365-coupang-insert-report.json','w',encoding='utf-8').write(json.dumps(results,ensure_ascii=False,indent=2))
if any(x['status']!='VERIFIED' for x in results): sys.exit(2)
