from pathlib import Path
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import render_template_string
ROOT=Path('/opt/korea365')
def install(app):
 @app.get('/pipeline-status')
 def pipeline_status():
  d=json.loads((ROOT/'data/pipeline-connection-audit.json').read_text())
  board_file=ROOT/'data/publication-board.json'
  board=json.loads(board_file.read_text()) if board_file.exists() else {}
  today=datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
  summaries={}
  for kind,total in [('WP',25),('Blogspot',33),('신문사',2)]:
   rows=[r for r in board.get('sites',[]) if r.get('kind')==kind]
   fresh=[r for r in rows if str(r.get('checked_at','')).startswith(today) and not r.get('error')]
   completed=sum(isinstance(r.get('today'),int) and r['today']>0 for r in fresh)
   summaries[kind]=f'오늘 실제 발행 {completed}/{total}곳 · 미발행 {sum(r.get("today")==0 for r in fresh)}곳 · 조회 미확인 {total-len(fresh)}곳'
  stages=[('WP 25','VPS 시간표 → 무료 작성·검수 → VPS 발행기 → WP REST → 공개 확인',summaries['WP']),('블로그스팟 33','VPS 시간표 → 무료 작성·검수 → Blogger API → 공개 확인',summaries['Blogspot']),('신문 2','VPS RSS → 운영 대기열 → GitHub Actions → 작성·검수 → WP REST',summaries['신문사']+' · 대체 작성·검수 및 RSS 대기열 복구 반영'),('플레이리스트 5','제작 계획 → 음원·권리·영상 검수 → VPS release_runner → 비공개 업로드 → 소유자 승인','40개 슬롯이 planned_not_uploaded 상태. 완성본 업로드 확인 없음. 2개 채널 신원 일치, 3개 채널 확인 권한 부족.'),('지식 유튜브 5','자료·권리 확인 → 대본·음성·영상 → 최종 승인 → 업로드','5개 모두 채널 신원 조회 권한 부족. 시간표 실행기는 approval_required에서 멈추며 승인 발행 연결은 미완료.'),('인스타·페북·스레드·틱톡','계정 연결 → 콘텐츠 검수 → 소유자 최종 승인 → 플랫폼별 게시 → 결과 확인','현재 VPS 런타임에 게시 인증 미등록. 브라우저 로그인 및 GitHub 시크릿 존재 여부는 별도 확인 필요.'),('GitHub','소스·워크플로 보관 및 일부 기존 발행 실행','신문·WP 워크플로 active, 예전 플리 워크플로 deleted. 활성 상태만으로 자동 발행 중이라는 뜻은 아님.')]
  return render_template_string('''<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="60"><title>Korea365 실제 연결 점검</title><style>body{font:16px/1.7 system-ui;background:#f2f5fa;color:#182b42;max-width:1100px;margin:30px auto;padding:20px}section{background:white;padding:20px;border-radius:12px;margin:14px 0}h2{margin:0}a{color:#245bea}strong{color:#a64210}</style><h1>실제 발행 경로 점검</h1><p>공개 글 집계 {{board.checked_at}} · 한국시간 기준 · 1분마다 화면 갱신</p><a href="/account-schedule?platform=전체">전체 계정 카드 한눈에 보기</a>{% for title,path,status in stages %}<section><h2>{{title}}</h2><p>{{path}}</p><strong>{{status}}</strong></section>{% endfor %}<h2>오늘 실제 발행된 글</h2>{% for r in board.sites %}{% if r.today and r.today > 0 %}<section><b>{{r.site}}</b> · {{r.today}}건<br>{% for h in r.history %}{% if h.published_kst.startswith(today) %}<a href="{{h.url}}" target="_blank" rel="noopener">{{h.title}}</a> · {{h.published_kst}}<br>{% endif %}{% endfor %}</section>{% endif %}{% endfor %}<h2>유튜브 채널별 실제 조회</h2>{% for y in d.youtube %}<section>{{y.name}} · {{'신원 일치' if y.channel_match else '채널 확인 권한 필요'}}{% if y.reason %} · {{y.reason|join(', ')}}{% endif %}</section>{% endfor %}<p>실행 중: 미발행 WP·블로그스팟은 무료 작성 → 검수 → 발행 → 공개 확인 순서로 처리합니다. 방문자 집계 오류는 글 발행을 막지 않습니다. 유튜브·SNS는 최종 승인 후 공개합니다.</p>''',d=d,stages=stages,board=board,today=today),200,{'Cache-Control':'no-store'}

