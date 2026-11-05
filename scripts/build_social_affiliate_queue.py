#!/usr/bin/env python3
"""Build a no-publish social/video queue from the single locked weekly catalog."""
from __future__ import annotations
import argparse, json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/'config/affiliate_distribution_policy.json').read_text(encoding='utf-8-sig'))
YT=json.loads((ROOT/'config/YOUTUBE_23_CHANNEL_MASTER_LOCK_2026-09-27.json').read_text(encoding='utf-8-sig'))
SNS=json.loads((ROOT/'config/sns_six_channel_policy.json').read_text(encoding='utf-8-sig'))
CATALOG=json.loads((ROOT/'config/affiliate/global-weekly-10.json').read_text(encoding='utf-8-sig'))
AUTH=json.loads((ROOT/'config/youtube-auth-preflight-snapshot-2026-11-05.json').read_text(encoding='utf-8-sig'))
EXPECTED={'coupang_partners':10}
MARKER='london-omnichannel-social-v2'
PLACEMENTS={
 'youtube':['video_description','pinned_comment'],
 'tiktok':['profile_bio_link','native_product_links_only_if_enabled'],
 'instagram':['profile_link','story_link_sticker'],
 'threads':['profile_link','post_body_link_when_supported'],
 'facebook':['page_post_links','page_link'],
}
def slug(value): return re.sub(r'[^a-z0-9]+','_',str(value).lower()).strip('_')
def valid_https(value):
 try:
  u=urlparse(str(value or '')); return u.scheme=='https' and bool(u.netloc)
 except Exception: return False
def validate_global_catalog():
 errors=[]; items=CATALOG.get('items',[]); counts=Counter(); urls=set(); images=set(); offers=[]
 if CATALOG.get('source_of_truth') is not True: errors.append('global_catalog_not_source_of_truth')
 if CATALOG.get('status')!='weekly_catalog_ready_global_rollout_approved': errors.append('global_catalog_rollout_not_approved')
 try:
  now=datetime.now(ZoneInfo('Asia/Seoul')); start=datetime.fromisoformat(CATALOG['lock_window']['starts_at']); end=datetime.fromisoformat(CATALOG['lock_window']['ends_at'])
  if not start<=now<end: errors.append('global_catalog_outside_168h_lock_window')
 except Exception: errors.append('global_catalog_lock_window_invalid')
 if len(items)!=10: errors.append(f'expected_10_global_items_got_{len(items)}')
 for i,item in enumerate(items,1):
  url=item.get('url',''); image=item.get('image_url',''); category=item.get('category','')
  if item.get('enabled') is not True or item.get('affiliate_confirmed') is not True: errors.append(f'unverified_or_disabled_item:{item.get("id",i)}')
  if not valid_https(url) or urlparse(url).netloc!='link.coupang.com': errors.append(f'invalid_tracking_url:{item.get("id",i)}')
  if not valid_https(image) or 'coupangcdn.com' not in urlparse(image).netloc or '/image/affiliate/banner/' not in urlparse(image).path: errors.append(f'invalid_official_affiliate_image:{item.get("id",i)}')
  if not item.get('title'): errors.append(f'missing_title:{item.get("id",i)}')
  if url in urls: errors.append('duplicate_tracking_url')
  if image in images: errors.append('duplicate_image_url')
  urls.add(url); images.add(image); counts[category]+=1
  offers.append({'slot':f'coupang_{i:02d}','provider':'coupang_partners','title':item.get('title'),'display_title_en':item.get('display_title_en',''),'description_en':item.get('description_en',''),'url':url,'image_url':image,'category':category})
 if counts!={'health_functional_foods':5,'k_beauty_skincare':5}: errors.append(f'category_mix_mismatch:{dict(counts)}')
 return offers,sorted(set(errors))
def youtube_destinations():
 verified=AUTH.get('verified_channels',{}); rows=[]
 for group,channels in YT.get('groups',{}).items():
  for channel in channels:
   key=channel.get('key',''); channel_id=channel.get('channel_id')
   rows.append({'platform':'youtube','destination_key':key,'display_name':channel.get('title',''),'channel_id':channel_id,
    'identity_verified':bool(channel.get('verified')),'publish_connected':verified.get(key)==channel_id,
    'auth_preflight_verified':verified.get(key)==channel_id,'catalog_key':'global-weekly-10','group':group})
 return rows
def social_destinations():
 rows=[]
 for account in SNS.get('accounts',[]):
  platform=slug(account.get('platform','')); role=account.get('role','')
  rows.append({'platform':platform,'destination_key':f'{platform}_{role}','display_name':account.get('display_name',''),
   'account_url':account.get('url',''),'account_exists':account.get('account_exists') is True,
   'identity_verified':account.get('identity_verified') is True,'publish_connected':account.get('publish_connected') is True,
   'catalog_key':'global-weekly-10'})
 return rows
def build_job(destination,content,offers,catalog_errors):
 errors=list(catalog_errors)
 if destination['platform']=='youtube' and not destination.get('channel_id'): errors.append('youtube_channel_id_missing')
 if destination['platform']!='youtube' and not destination.get('account_exists'): errors.append('social_account_not_created_or_verified')
 if not destination.get('identity_verified'): errors.append('destination_identity_not_verified')
 if not destination.get('publish_connected'): errors.append('publish_oauth_not_connected')
 links=[{'slot':o['slot'],'provider':o['provider'],'category':o['category'],'title':o['title'],'url':o['url']} for o in offers]
 job_id=f"{destination['platform']}:{destination['destination_key']}:{content.get('content_id','manual')}"
 return {'job_id':job_id,'marker':MARKER,'platform':destination['platform'],'destination':destination,'content':content,
  'global_catalog_id':CATALOG.get('set_id'),'affiliate_links':links,'affiliate_link_count':len(links),
  'provider_counts':dict(Counter(x['provider'] for x in links)),'supported_placements':PLACEMENTS[destination['platform']],
  'status':'blocked' if errors else 'ready_for_platform_adapter','blockers':sorted(set(errors)),
  'publish_attempted':False,'receipt':None,'retry_scope':'this_destination_only'}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--content-id',default='manual-preview'); ap.add_argument('--title',default=''); ap.add_argument('--url',default=''); ap.add_argument('--summary',default=''); ap.add_argument('--mode',choices=['new','backfill'],default='new'); args=ap.parse_args()
 content={'content_id':args.content_id,'title':args.title,'url':args.url,'summary':args.summary,'mode':args.mode}
 offers,catalog_errors=validate_global_catalog(); destinations=youtube_destinations()+social_destinations(); jobs=[build_job(d,content,offers,catalog_errors) for d in destinations]
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'policy':{'per_content_total':10,'provider_allocation':EXPECTED,'catalog_set_id':CATALOG.get('set_id'),'lock_window':CATALOG.get('lock_window')},
  'source_content':content,'scope':{'youtube_registry':sum(x['platform']=='youtube' for x in destinations),'social_accounts_listed':sum(x['platform']!='youtube' for x in destinations)},
  'global_catalog_validation_errors':catalog_errors,'global_catalog_offer_count':len(offers),'jobs_total':len(jobs),
  'ready_for_adapter':sum(j['status']=='ready_for_platform_adapter' for j in jobs),'blocked':sum(j['status']=='blocked' for j in jobs),
  'publish_attempted':False,'jobs':jobs}
 out=ROOT/'reports/social-affiliate-distribution-queue.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:report[k] for k in ('global_catalog_validation_errors','global_catalog_offer_count','jobs_total','ready_for_adapter','blocked','publish_attempted','scope')},ensure_ascii=False))
if __name__=='__main__': main()
