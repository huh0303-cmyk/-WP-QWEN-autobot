import datetime as dt,fcntl,hashlib,hmac,json
from pathlib import Path
from flask import request,jsonify
ROOT=Path('/opt/korea365');DATA=ROOT/'data';KST=dt.timezone(dt.timedelta(hours=9))
def read(p,default):return json.loads(p.read_text()) if p.exists() else default
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix('.tmp');t.write_text(json.dumps(d,ensure_ascii=False));t.chmod(0o600);t.replace(p)
def install(app):
 @app.post('/account-schedule/publish-now')
 def account_publish_now():
  data=request.get_json(silent=True) or {}
  if not hmac.compare_digest(str(data.get('csrf_token','')),str(app.config['CONTROL_CENTER_CSRF'])):return jsonify(message='새로고침 후 다시 눌러주세요.'),403
  cards=read(DATA/'account-schedule-20260923.json',{}).get('cards',[])
  c=next((x for x in cards if x['key']==data.get('account_key')),None)
  if not c:return jsonify(message='등록된 계정이 아닙니다.'),404
  if c['approval']:
   platform=c['platform'].lower();url='/channel-check/'+platform if platform in ('youtube','tiktok','facebook','instagram','threads') else '/operations-guide'
   return jsonify(message='최종 승인 대상입니다. 계정 점검 화면에서 발행할 콘텐츠와 연결 상태를 먼저 확인해 주세요. 아직 공개하지 않았습니다.',review_url=url),409
  with (DATA/'account-manual-publish.lock').open('w') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   now=dt.datetime.now(KST)
   if c['platform']=='신문사':
    from .rss_watch import _dispatch_count,_increment_dispatch_count,NEWSROOM_DAILY_MAX
    ops=app.extensions['operations'];rss=ops['rss'];store=ops['store'];name=c['url'].split('//')[-1].split('.')[0]
    if _dispatch_count(store,name)>=NEWSROOM_DAILY_MAX:return jsonify(message='오늘 신문 발행 요청 한도에 도달했습니다. 기존 요청 결과를 확인해 주세요.'),409
    with store.connect() as db:
     item=db.execute("SELECT i.*,e.payload FROM rss_items i JOIN rss_item_evidence e ON i.id=e.id WHERE i.newsroom=? AND i.state='waiting' AND i.published BETWEEN ? AND ? ORDER BY i.published DESC LIMIT 1",(name,now.timestamp()-72*3600,now.timestamp()+600)).fetchone()
    if not item:return jsonify(message='발행 가능한 새 RSS 자료가 없습니다. 자료 검증 후 다시 시도해 주세요.'),409
    descriptor=next((dict(t) for t in rss.targets() if t['label'].split('.')[0]==name),None)
    if not descriptor:return jsonify(message='신문 발행 연결을 확인해야 합니다.'),409
    descriptor.update(source='rss',source_title=item['title'],source_url=item['url']);descriptor['inputs']=dict(descriptor['inputs'],source_url=item['url'],source_item=item['payload'])
    try:store.submit('news2',[descriptor],'rss-'+item['id'])
    except Exception:return jsonify(message='진행 중인 신문 요청이 있습니다. 중복 접수하지 않았습니다.'),409
    _increment_dispatch_count(store,name)
    with store.connect() as db:db.execute("UPDATE rss_items SET state='accepted' WHERE id=?",(item['id'],))
    return jsonify(message='선택한 신문의 RSS 기사 검증·발행 요청을 접수했습니다. 공개 완료는 발행 이력에서 확인하세요.'),202
   slots=[s for s in c['slots'] if dt.datetime.fromisoformat(s).date()==now.date()]
   if not slots:return jsonify(message='오늘 이 계정의 발행 슬롯이 없습니다.'),409
   slot=slots[0];jid=hashlib.sha256((c['key']+'|'+slot).encode()).hexdigest()[:24]
   state=read(DATA/'account-schedule-runtime.json',{}).get('jobs',{}).get(jid,{})
   if state.get('status') in ('public_verified','queued','readback_pending','inserting_draft','draft_created','publish_uncertain','failed','held','credential_required'):
    return jsonify(message='이미 발행됐거나 처리·확인이 필요한 요청입니다. 중복 발행하지 않습니다.',status=state['status']),409
   file=DATA/'manual-publish-requests'/f'{jid}.json';previous=read(file,{})
   if previous and dt.datetime.fromisoformat(previous['expires_at'])>now:return jsonify(message='이미 즉시발행 요청을 접수했습니다. 검수 원고 준비 후 순차 처리합니다.'),202
   write(file,{'job_id':jid,'account_key':c['key'],'slot':slot,'requested_at':now.isoformat(),'expires_at':(now+dt.timedelta(minutes=60)).isoformat()})
   return jsonify(message='즉시발행 요청을 접수했습니다. 검수 원고가 있으면 1분 내 처리하고, 없으면 무료 원고 준비부터 진행합니다. 오늘 1건 제한은 유지합니다.'),202
