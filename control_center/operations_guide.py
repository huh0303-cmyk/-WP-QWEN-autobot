"""Authenticated operating manual and evidence summary, no publishing actions."""
import json
from pathlib import Path
from flask import render_template, request, jsonify, send_file

ROOT = Path('/opt/korea365')

OWNER_CADENCE = {
    'effective_date': '2026-09-25',
    'youtube_locked_10': '채널별 주 2~3회 · 매주 랜덤 요일 · 비공개 검수',
    'all_non_youtube': '대상별 하루 1건 · 랜덤 시각 · 쓰기 권한 확인 후 실행',
}


def apply_owner_cadence_copy(html):
    """Keep the server template aligned with the canonical owner cadence.

    The production template predates this rule and may be retained as a VPS
    operational asset. These narrow replacements avoid replacing the whole
    page while removing stale weekly-SNS and high-volume-news wording.
    """
    replacements = {
        'WP·Blogspot 매일 1건 / 기타 주 2회 / 신문 별도':
            '유튜브 10개 채널만 주 2~3회 랜덤 / 나머지 모두 하루 1건',
        '유튜브 · SNS 개별 점검': '유튜브 주 2~3회 · 기타 매일 1회 점검',
        '운영 모드: 글 사이트 자동 발행 / 영상·SNS는 이사장님 승인':
            '운영 모드: YouTube 비공개 검수 / 나머지 매일 1회 (쓰기 권한 확인 계정)',
        '계정별 주 2회 · 승인 후 공개': '계정별 하루 1회 · 쓰기 권한 확인 후 공개',
        '채널별 주 2편 목표': '채널별 주 2~3편 · 매주 랜덤 요일',
        '채널별 완성본 시험부터': '채널별 주 2~3편 랜덤 · 완성본 시험부터',
        '각 하루 1건 · 검수 후 자동': '각 하루 1건 · 출처 검수 후 자동',
    }
    for old, new in replacements.items():
        html = html.replace(old, new)
    return html

def load(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default

def install(app):
    @app.before_request
    def owner_approval_hold():
        # Existing content-less immediate publish controls cannot constitute
        # approval of a particular reviewed content revision.
        if (ROOT/'data/owner-approval-required.json').exists() and request.method in {'POST','PUT','PATCH','DELETE'}:
            if request.path in {'/account-schedule/publish-now','/social-accounts/publish-now','/control-login','/control-logout','/api/vps/publish','/trigger/wp-draft-single','/trigger/blogspot-draft-single'} or request.endpoint == 'blog_visits':
                return None
            return jsonify(error='owner_review_required', message='WP·뉴스·Blogspot은 검수 후 자동 발행 대상입니다. 이 경로는 기타 매체 승인 또는 기존 실행 경로 검증이 필요하여 보류 중입니다.'), 423

    @app.get('/operations-guide')
    def operations_guide():
        data=load(ROOT/'data/publication-board.json', {})
        rows=data.get('sites', [])
        groups={kind:[r for r in rows if r.get('kind')==kind] for kind in ['WP','Blogspot','신문사']}
        stats={k:{'sites':len(v),'posted':sum(isinstance(r.get('today'),int) and r['today']>0 for r in v),
                  'posts':sum(r.get('today') or 0 for r in v), 'errors':sum(bool(r.get('error')) for r in v)} for k,v in groups.items()}
        plan=load(ROOT/'playlist-v3/production-plan.json',{})
        jobs=plan.get('jobs',[])
        playlist={'planned':len(jobs),'uploaded':sum(bool(j.get('youtube_video_id')) for j in jobs),'checked':plan.get('last_runner_check','미확인')}
        html = render_template('operations_guide.html',stats=stats,checked=data.get('checked_at','미확인'),playlist=playlist,audit=load(ROOT/'data/operations-site-audit.json',{}),channel_audit=load(ROOT/'data/operations-channel-audit.json',{}),owner_cadence=OWNER_CADENCE)
        return apply_owner_cadence_copy(html),200,{'Cache-Control':'no-store'}

    @app.get('/api/publishing-cadence')
    def publishing_cadence():
        return jsonify(OWNER_CADENCE), 200, {'Cache-Control': 'no-store'}

    @app.get('/operations-guide/manual.md')
    def operations_manual():
        return send_file(ROOT/'docs/OPERATING-MANUAL.md',as_attachment=True,download_name='Korea365-운영지침서.md')
