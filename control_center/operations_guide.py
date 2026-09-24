"""Authenticated operating manual and evidence summary, no publishing actions."""
import json
from pathlib import Path
from flask import render_template, request, jsonify, send_file

ROOT = Path('/opt/korea365')

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
        return render_template('operations_guide.html',stats=stats,checked=data.get('checked_at','미확인'),playlist=playlist,audit=load(ROOT/'data/operations-site-audit.json',{}),channel_audit=load(ROOT/'data/operations-channel-audit.json',{})),200,{'Cache-Control':'no-store'}

    @app.get('/operations-guide/manual.md')
    def operations_manual():
        return send_file(ROOT/'docs/OPERATING-MANUAL.md',as_attachment=True,download_name='Korea365-운영지침서.md')
