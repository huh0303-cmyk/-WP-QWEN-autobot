import json,re,html,hashlib,random
from pathlib import Path
from collections import Counter
SRC='reports/oliveyoung-kskin365-coupang-products-2026-11-01.ndjson'
POSTS='reports/oliveyoung-kskin365-post-content-2026-11-01.json'
OUT='reports/oliveyoung-kskin365-affiliate-placement-map-2026-11-01.json'
POOL_OUT='data/affiliate/oliveyoung-kskin365-verified-product-pool.json'
LABELS={
'oy01':('Anua Heartleaf 77 Soothing Toner','toner','A calming daily toner with heartleaf for a balanced skincare routine.'),
'oy02':('Torriden Dive-In Hyaluronic Acid Toner','toner','A hydrating toner for a fresh, moisture-focused routine.'),
'oy03':('Round Lab Birch Juice Moisturizing Cream Set','moisturizer','A daily moisturizing cream set for comfortable, hydrated skin.'),
'oy04':('Beauty of Joseon Relief Sun SPF50+','sunscreen','A lightweight daily sunscreen for broad-spectrum UV protection.'),
'oy05':('COSRX Snail Radiance Dual Essence','serum','A dual-texture essence for a hydrated, radiant-looking complexion.'),
'oy06':('SKIN1004 Madagascar Centella Ampoule Set','serum','A centella-focused ampoule for a soothing skincare routine.'),
'oy07':('Dr.G R.E.D Blemish Clear Soothing Cream','moisturizer','A soothing cream for blemish-prone and sensitive-feeling skin.'),
'oy08':('Round Lab 1025 Dokdo Toner Set','toner','A daily toner set designed for gentle hydration.'),
'oy09':('Torriden Dive-In Soothing Cream','moisturizer','A hydrating cream for a comfortable moisture barrier routine.'),
'oy10':('Dr.G Green Deep Cleansing Oil','cleanser','An oil cleanser for removing sunscreen and daily makeup.'),
'oy11':('Aestura Atobarrier 365 Gentle Foaming Cleanser','cleanser','A gentle foaming cleanser for daily face washing.'),
'oy12':('COSRX Low pH Good Morning Gel Cleanser','cleanser','A low-pH gel cleanser for a gentle morning routine.'),
'oy13':('Beauty of Joseon Glow Propolis Serum','serum','A glow-focused propolis serum for daily skincare.'),
'oy14':('Goodal Green Tangerine Vita C Dark Spot Serum Set','serum','A vitamin C-focused serum set for brightening routines.'),
'oy15':('Some By Mi Retinol Intense Reactivating Serum','serum','A retinol serum for an evening skincare routine.'),
'oy16':('Medicube PDRN Pink Peptide Serum','serum','A PDRN and peptide serum for a firm-looking, hydrated complexion.'),
'oy17':('VT Cosmetics Collagen Reedle Shot 100','serum','A collagen-focused K-beauty treatment essence.'),
'oy18':('Mediheal Madecassoside Blemish Pads','mask','Madecassoside toner pads for targeted soothing care.'),
'oy19':('Abib Heartleaf Spot Pads','mask','Heartleaf spot pads for a quick calming skincare step.'),
'oy21':('Illiyoon Ceramide Ato Concentrate Body Cream','moisturizer','A ceramide-rich cream for dry skin and body barrier care.'),
'oy22':('Aestura Atobarrier 365 Hydro Soothing Cream','moisturizer','A lightweight barrier-focused cream for daily hydration.'),
'oy23':('Etude SoonJung 2x Barrier Intensive Cream','moisturizer','A barrier-care cream for sensitive-feeling skin.'),
'oy24':('Laneige Water Sleeping Mask','mask','An overnight sleeping mask for an intensive hydration step.'),
'oy25':('Medicube Collagen Night Wrapping Mask','mask','A collagen night mask for an overnight skincare routine.'),
'oy26':('Biodance Bio-Collagen Real Deep Mask','mask','A bio-collagen sheet mask for a moisture-focused treatment.'),
'oy27':('Mediheal Tea Tree Essential Mask','mask','A tea tree sheet mask for a refreshing skincare routine.'),
'oy28':('Torriden Dive-In Hyaluronic Acid Mask','mask','A hyaluronic acid sheet mask for hydration.'),
'oy29':('Beauty of Joseon Revive Eye Retinal Cream','eye_care','A retinal eye cream for a targeted evening routine.'),
'oy30':('Isntree Hyaluronic Acid Watery Sun Gel SPF50+','sunscreen','A watery sunscreen gel for daily UV protection.'),
'oy31':('SKIN1004 Hyalu-Cica Water-Fit Sun Serum','sunscreen','A hydrating sun serum for everyday UV protection.'),
'oy32':('Dr.Jart Ceramidin Skin Barrier Serum Toner','toner','A ceramide-focused toner for a moisture barrier routine.'),
'oy33':('Sulwhasoo First Care Eye Serum','luxury','A premium Sulwhasoo eye-care serum.'),
'oy34':('Sulwhasoo Concentrated Ginseng Renewing Cream','luxury','A premium ginseng cream from Sulwhasoo.'),
'oy35':('The History of Whoo Bichup Ja Saeng Essence','luxury','A premium Korean skincare essence from The History of Whoo.'),
'oy36':('Medicube Age-R Booster Pro','device','A premium at-home beauty device for a tech-focused skincare routine.'),
'oy37':('Medicube Age-R Booster Pro Mini Plus','device','A compact at-home beauty device from Medicube.'),
'oy38':('LG Pra.L Derma LED Mask','device','A premium LED skincare mask for at-home beauty routines.'),
'oy42':('Dyson Supersonic Nural Hair Dryer','device','A premium hair-care appliance for a salon-style home routine.'),
'oy43':('ReFa CAXA M1 Facial Massage Roller','device','A premium facial massage tool for at-home beauty care.'),
'oy45':('Medicube Zero Pore Pad 2.0 Set','mask','Pore-care toner pads for a simple exfoliating routine.'),
'oy46':('Anua Peach 70 Niacinamide Serum Set','serum','A niacinamide serum set for a brightening-focused routine.'),
'oy47':('Numbuzin No.5 Glutathione C Tone-Up Cream','moisturizer','A tone-up cream with glutathione and vitamin C positioning.'),
'oy48':('Dr.Althea 345 Relief Moisturizing Cream','moisturizer','A daily relief cream for a moisture-focused routine.'),
'oy49':('ma:nyo Pure Cleansing Oil','cleanser','A cleansing oil for removing makeup and sunscreen.'),
'oy50':('KAHI Wrinkle Bounce Multi Balm','eye_care','A portable multi balm for targeted moisture and wrinkle-care routines.')
}
# products intentionally omitted: oy20 duplicates oy03; oy44 is a generic facial brush unrelated to the named FOREO search.
def main():
 latest={}
 for line in open(SRC,encoding='utf-8-sig'):
  try:x=json.loads(line.lstrip('\ufeff'))
  except:continue
  latest[x.get('candidate_id')]=x
 pool=[];seen=set()
 for cid,x in latest.items():
  if x.get('status')!='CAPTURED' or cid not in LABELS:continue
  pid=str(x.get('product_id') or '')
  if not pid or pid in seen:continue
  seen.add(pid)
  link=x.get('affiliate_url','');img=x.get('official_image_url','');tag=x.get('official_blog_html_tag','')
  if not link.startswith('https://link.coupang.com/') or '.coupangcdn.com/' not in img or '<a ' not in tag:continue
  name,cat,desc=LABELS[cid]
  price=int(x.get('price') or 0)
  pool.append({'candidate_id':cid,'product_id':pid,'item_id':x.get('item_id'),'vendor_item_id':x.get('vendor_item_id'),'query':x.get('query'),'title_ko':x.get('product_title'),'display_title_en':name,'category':cat,'description_en':desc,'price_krw':price,'affiliate_url':link,'official_image_url':img,'official_blog_html_tag':tag,'high_ticket':price>=100000 or cat in ('device','luxury'),'status':'VERIFIED_ACCOUNT_GENERATED'})
 assert len(pool)>=40, len(pool)
 Path(POOL_OUT).parent.mkdir(parents=True,exist_ok=True)
 Path(POOL_OUT).write_text(json.dumps({'date':'2026-11-01','site_scope':['oliveyoungkorea.com','kskin365.com'],'source':'Authenticated Coupang Partners generated blog tags','count':len(pool),'products':pool},ensure_ascii=False,indent=2),encoding='utf-8')
 posts=json.load(open(POSTS,encoding='utf-8'))
 usage=Counter(); mapping={'date':'2026-11-01','sites':{},'product_pool_file':POOL_OUT,'products_per_post':8,'selection_policy':'3 topical + 2 daily essentials + 2 premium/high-ticket + 1 randomized; frequency-balanced and no duplicate product within post'}
 core={'cleanser','toner','sunscreen','moisturizer'}
 premium=[p for p in pool if p['high_ticket']]
 topical_patterns={
 'sunscreen':['sunscreen','sun protection','spf','uv','photoprotection','sun exposure'],
 'cleanser':['cleanser','cleansing','cleansing oil','foam cleanser','makeup removal'],
 'toner':['toner','hydration','hydrating','skin prep'],
 'serum':['serum','essence','niacinamide','retinol','vitamin c','pdrn','tranexamic','brightening','peptide','antioxidant','glutathione'],
 'moisturizer':['moisturizer','moisturizing','moisture barrier','barrier','ceramide','cream','soothing','sensitive skin','dry skin'],
 'mask':['mask','sheet mask','sleeping mask','toner pad','pads','patch'],
 'eye_care':['eye','wrinkle','retinal','anti-aging','aging'],
 'device':['device','led','at-home beauty','hair dryer','facial roller','microcurrent']
 }
 def stable_rng(site,pid):
  seed=int(hashlib.sha256(f'{site}:{pid}'.encode()).hexdigest()[:16],16)
  return random.Random(seed)
 def choose(candidates,n,chosen,rng,score_map=None):
  candidates=[p for p in candidates if p['candidate_id'] not in {x['candidate_id'] for x in chosen}]
  rng.shuffle(candidates)
  candidates.sort(key=lambda p:(-(score_map or {}).get(p['candidate_id'],0),usage[p['candidate_id']]))
  out=[]
  for p in candidates:
   if len(out)>=n:break
   out.append(p);chosen.append(p);usage[p['candidate_id']]+=1
  return out
 for site,rows in posts.items():
  out=[]
  for post in rows:
   text=(post.get('title','')+' '+post.get('body_excerpt','')).lower()
   rng=stable_rng(site,post['id'])
   cat_scores={}
   for cat,terms in topical_patterns.items():
    hits=sum(1 for term in terms if term in text)
    if hits:cat_scores[cat]=hits
   # Product-specific ingredient matches boost exact relevance.
   scores={}
   for p in pool:
    sc=cat_scores.get(p['category'],0)*2
    hay=(p['display_title_en']+' '+p['query']+' '+p['description_en']).lower()
    for kw in ['niacinamide','retinol','vitamin c','pdrn','tranexamic','ceramide','heartleaf','centella','snail','hyaluronic','collagen','tea tree','ginseng','peptide','glutathione','spf','sunscreen','led']:
     if kw in text and kw in hay:sc+=5
    scores[p['candidate_id']]=sc
   chosen=[]
   # Three topical products; if text is broad, pick highest-scoring skincare products.
   topical=[p for p in pool if p['category'] in cat_scores] if cat_scores else [p for p in pool if p['category'] in core or p['category']=='serum']
   choose(topical,3,chosen,rng,scores)
   # Two everyday essentials, biased toward topical relevance.
   choose([p for p in pool if p['category'] in core],2,chosen,rng,scores)
   # Two premium/high-ticket products.
   choose(premium,2,chosen,rng)
   # One additional randomized product from the remaining pool.
   choose(pool,1,chosen,rng)
   if len(chosen)<8:choose(pool,8-len(chosen),chosen,rng)
   assert len(chosen)==8,(site,post['id'],len(chosen))
   out.append({'post_id':post['id'],'title':post['title'],'link':post['link'],'modified_snapshot':post['modified'],'products':[{'candidate_id':p['candidate_id'],'display_title_en':p['display_title_en'],'category':p['category'],'description_en':p['description_en'],'price_krw':p['price_krw'],'affiliate_url':p['affiliate_url'],'official_image_url':p['official_image_url'],'official_blog_html_tag':p['official_blog_html_tag']} for p in chosen]})
  mapping['sites'][site]=out
 Path(OUT).write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
 print('POOL',len(pool),'POSTS', {s:len(v) for s,v in mapping['sites'].items()},'TOTAL',sum(map(len,mapping['sites'].values())),'LINKS',sum(len(x['products']) for v in mapping['sites'].values() for x in v),'PRODUCT_USAGE_MINMAX',(min(usage.values()),max(usage.values())))
if __name__=='__main__':main()
