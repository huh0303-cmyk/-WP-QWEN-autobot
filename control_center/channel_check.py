import json
from pathlib import Path
from flask import render_template,abort
ROOT=Path('/opt/korea365')
PLATFORMS={'youtube':'YouTube','tiktok':'TikTok','facebook':'Facebook','instagram':'Instagram','threads':'Threads'}
def install(app):
 @app.get('/channel-check/<platform>')
 def channel_check(platform):
  if platform not in PLATFORMS:abort(404)
  try:d=json.loads((ROOT/'data/operations-channel-audit.json').read_text())
  except (OSError,ValueError):d={}
  items=[]
  if platform=='youtube':
   for c in d.get('youtube',[]):
    connection_ok=c.get('connection_ok',c.get('oauth_ok',c.get('status')=='채널 일치 · 읽기 확인'))
    items.append(dict(name=c.get('actual_name') or c['name'],group='플레이리스트' if c.get('type')=='playlist' else '지식',status=c['status'],ok=connection_ok,identity=c['channel_id'],topic='확정된 채널별 제작 지침 유지',next='완성본·권리 검수 후 비공개 업로드 시험' if connection_ok else '기존 읽기 연결 확인 필요 · 자동 공개 안 함',url='https://www.youtube.com/channel/'+c['channel_id']))
   connected_count=sum(1 for c in d.get('youtube',[]) if c.get('connection_ok'))
   note=f'영구 고정 10개 채널: {connected_count}개 기존 읽기 연결 정상, {len(d.get("youtube",[]))-connected_count}개 확인 필요. 채널 ID 기준이며 업로드·공개는 수행하지 않았습니다.'
  else:
   plans={
    'instagram':[('SIS TOPIK','sis_topik1','한국어·TOPIK 교육'),('Rosie’s Picks','seoul_item365','뷰티·상품·생활용품'),('서울 라이프365','seoul_life365','지원금·여행·생활정보'),('서울 헬스365','seoul_health365','건강·식품 정보')],
    'threads':[('Rosie’s Picks','seoul_item365','상품 발견 · 가벼운 말투'),('서울 라이프365','seoul_life365','생활·여행·검증된 화제'),('서울 헬스365','seoul_health365','건강·식품 정보')],
    'tiktok':[('SIS TOPIK','sis_topik','한국어·TOPIK 교육'),('English Survival','','영어 서바이벌'),('언어교육 채널','','기타 언어 · 최신 채널 매핑 확인'),('Rosie’s Picks','','쇼핑 콘텐츠')],
    'facebook':[('TOPIK 페이지','','한국어·TOPIK 교육'),('기존 영어 페이지','','페이지 식별 후 운영 주제 대조'),('기존 Language 페이지','','라이프·상품 운영안과 페이지 매핑 대조')]}
   for name,handle,topic in plans[platform]:
    url=''
    if handle:url=('https://www.instagram.com/'+handle+'/' if platform=='instagram' else 'https://www.threads.com/@'+handle if platform=='threads' else 'https://www.tiktok.com/@'+handle)
    items.append(dict(name=name,group='운영 대상 · 실제 연결 별도 확인',status='VPS 게시 인증 연결 미확인',ok=False,identity='@'+handle if handle else '정확한 계정 / 페이지 ID 확인 필요',topic=topic,next='기존 계정 확인 → 게시 권한 연결 → 비공개 또는 검토용 시험',url=url))
   note='VPS control.env 및 연결 런타임에서 운영용 계정·토큰을 확인하지 못했습니다. 브라우저 로그인이나 다른 저장소에 연결이 있을 가능성은 남아 있습니다. 표시된 SNS 이름은 사용자 제공 기록과 운영안 기준이며 변경 완료를 의미하지 않습니다.'
  return render_template('channel_check.html',platform=platform,label=PLATFORMS[platform],platforms=PLATFORMS,items=items,checked=d.get('checked_at','미확인'),note=note),200,{'Cache-Control':'no-store'}
