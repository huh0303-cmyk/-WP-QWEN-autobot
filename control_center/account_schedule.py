import json,io,csv
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from flask import request,render_template,Response
from scripts.publication_board import four_metrics_html
FILE=Path('/opt/korea365/data/account-schedule-20260923.json')
def rank_cards(cards, day):
 for c in cards:
  v=c.get('audience_value',c.get('visitors'))
  c['rank_valid']=isinstance(v,(int,float)) and not isinstance(v,bool) and v>=0 and c.get('audience_date',c.get('visitor_date'))==day
 cards.sort(key=lambda c:(not c['rank_valid'], -c.get('audience_value',c.get('visitors')) if c['rank_valid'] else 0, c.get('name',''), c.get('key','')))
 previous=None
 for i,c in enumerate(cards,1):
  c['visitor_rank']=None
  if c['rank_valid']:
   if previous!=c.get('audience_value',c.get('visitors')): rank=i
   c['visitor_rank']=rank
   previous=c.get('audience_value',c.get('visitors'))
 return cards

def install(app):
 @app.get('/account-schedule')
 def account_schedule():
  d=json.loads(FILE.read_text());runtime_file=FILE.parent/'account-schedule-runtime.json';runtime=json.loads(runtime_file.read_text()) if runtime_file.exists() else {};d['runtime_checked_at']=runtime.get('checked_at','미확인');
  labels={'scheduled':'예정 시간 대기','content_required':'무료 검수 원고 준비 필요','approval_required':'최종 승인 필요 · 공개 차단','missed_no_catchup':'예정 시간 경과 · 몰아발행 안 함','queued':'발행기 전달 · 공개 확인 대기','public_verified':'공개 페이지 검증 완료','readback_pending':'게시 결과 재확인 중','failed':'처리 오류 · 확인 필요','held':'발행 보류','credential_required':'인증 연결 필요','separate_rss':'별도 RSS 운영','publish_uncertain':'발행 결과 확인 필요 · 중복 재시도 차단','inserting_draft':'초안 생성 결과 확인 필요','draft_created':'초안 생성 · 후속 확인 필요'};
  evidence_path=FILE.parent/'publication-board.json';evidence=json.loads(evidence_path.read_text()) if evidence_path.exists() else {};by_url={r['url'].rstrip('/'):r for r in evidence.get('sites',[])}
  for c in d['cards']:
   evidence_row=by_url.get(c.get('url','').rstrip('/'),{});c['history']=evidence_row.get('history',[]);c['history_checked_at']=evidence_row.get('checked_at');c['history_error']=evidence_row.get('error','');c['today_actual']=evidence_row.get('today')
   c['visitors']=evidence_row.get('yesterday_visitors');c['visitor_delta']=evidence_row.get('visitor_delta');c['visitor_date']=evidence_row.get('visitor_date');c['visitor_error']=evidence_row.get('visitor_error','집계 연결 확인 필요');c['four_metrics_html']=four_metrics_html(evidence_row)
   live=runtime.get('cards',{}).get(c['key'],{});c['execution']=labels.get(live.get('status'),live.get('detail','실행 상태 대기'));c['next_slot']=live.get('next_slot');
   if c['history']: c['latest_url']=c['history'][0]['url'];c['latest_title']=c['history'][0]['title'];c['latest_at']=c['history'][0]['published_kst']
  supply_path=FILE.parent/'free-article-supplier.json';supply=json.loads(supply_path.read_text()) if supply_path.exists() else {}
  reasons={'free_quota_wait_no_paid_fallback':'무료 한도 대기 · 유료 전환 안 함','editorial_review_rejected':'검수 기준 미달 · 원고 보류','two_readable_authoritative_sources_required':'공식 근거 자료 보완 필요','free_tier_recheck_due':'무료 등급 재확인 필요','matching_free_photo_missing':'내용에 맞는 무료 사진 필요','structure_review_failed':'원고 형식 보완 필요'}
  for c in d['cards']:
   jobs=[x for x in supply.get('jobs',{}).values() if x.get('account_key')==c['key']]
   c['supplier_status']=('새 원고 검수 통과 · 시간표에 공급됨' if jobs[-1].get('status')=='ready' else reasons.get(jobs[-1].get('reason'),'원고 준비 중 · 재검수 대기')) if jobs else ('무료 원고 순차 준비 대기' if c['platform'] in ('WP','Blogspot') else '')
  verified_path=FILE.parent/'schedule-connection-verification.json';verified=json.loads(verified_path.read_text()) if verified_path.exists() else {};deliveries={x['account']:x for x in verified.get('draft_handoffs',[])}
  for c in d['cards']:
   c['delivery_detail']='실제 초안 전송·저장 검사 통과' if c['key'] in deliveries else ''
  audience_file=FILE.parent/'account-audience-metrics.json'
  audience=json.loads(audience_file.read_text()).get('accounts',{}) if audience_file.exists() else {}
  for c in d['cards']:
   a=audience.get(c.get('identity'),{})
   website=c['platform'] in ('WP','Blogspot','신문사','Tistory','Naver')
   c.update(audience_label='전날 방문자 수' if website else '전날 조회수',audience_value=c.get('visitors') if website else a.get('views'),audience_delta=c.get('visitor_delta') if website else a.get('delta'),audience_date=c.get('visitor_date') if website else a.get('date'),last_month=a.get('last_month'),audience_total=a.get('total_views'),subscribers=a.get('subscribers'),audience_timezone='KST' if website else a.get('timezone','플랫폼 집계 기준'),audience_error=c.get('visitor_error') if website else a.get('error','통계 연결 필요'))
  sns_path=FILE.parent/'sns-account-status.json'
  sns=json.loads(sns_path.read_text()) if sns_path.exists() else {}
  for c in d['cards']:
   c['sns_status']=sns.get('accounts',{}).get(c['key'])
   if c['sns_status']:
    st=c['sns_status'];c.update(name=st['target_name']+' · 운영명',identity=st['handle'],topic=st['role'],approval=True,execution=st['connection'],slots=[])
  d['cards']=[c for c in d['cards'] if not(c['key']=='TikTok-3' and not c.get('identity'))]
  platforms=['전체']+list(dict.fromkeys(c['platform'] for c in d['cards']));selected=request.args.get('platform','전체');selected=selected if selected in platforms else '전체'
  now=datetime.now(ZoneInfo('Asia/Seoul'))
  cards=[dict(c,display_slots=[s[:10]+' '+s[11:16] for s in c['slots'] if datetime.fromisoformat(s)>now]) for c in d['cards'] if selected=='전체' or c['platform']==selected]
  d['ranking_date']=(datetime.now(ZoneInfo('Asia/Seoul')).date()-timedelta(days=1)).isoformat()
  cards=[c for platform in platforms[1:] for c in rank_cards([x for x in cards if x['platform']==platform],d['ranking_date'])]
  return render_template('account_schedule.html',data=d,cards=cards,platforms=platforms,selected=selected),200,{'Cache-Control':'no-store'}
 @app.get('/account-schedule.csv')
 def account_schedule_csv():
  d=json.loads(FILE.read_text());f=io.StringIO();w=csv.writer(f);w.writerow(['플랫폼','계정/운영대상','계정ID','예정시간 KST','승인필요','상태'])
  for c in d['cards']:
   for s in c['slots']:w.writerow([c['platform'],c['name'],c['identity'],s,'예' if c['approval'] else '아니오',c['execution']])
  return Response('\ufeff'+f.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=korea365-schedule-20260923.csv'})
