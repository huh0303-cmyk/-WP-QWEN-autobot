import json
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

import pytest
import requests

from control_center.operations import Store, Worker, Conflict
from control_center.operation_gateway import GitHubGateway, publication_receipt
from control_center.rss_watch import RSSWatcher, parse_feed


def target(site="wp_one", platform="wordpress"):
    return dict(site_id=site, site_group="wp_" + site, label=site, platform=platform,
                site_url="https://example.com", workflow="writer.yml", inputs={})


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "operations.db")


def ready(store, descriptor=None):
    store.submit("wp25", [descriptor or target()], "request-1234567890")
    return store.claim()


def test_double_click_and_group_single_overlap_are_atomic(store):
    def submit(i):
        try:
            return store.submit("wp25", [target()], "request-" + str(i))
        except Conflict:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(submit, range(8)))
    assert sum(r is not None for r in results) == 1
    assert len(store.snapshot()) == 1
    request_id, _skipped = next(r for r in results if r)
    store.submit("wp25", [target()], request_id)
    assert len(store.snapshot()) == 1
    with pytest.raises(Conflict):
        store.submit("wp_wp_one", [target()], "another-request")


def test_conflicting_batch_skips_only_the_blocked_site(store):
    """2026-09-12: one stuck site (confirmed live - KFinance365's Blogger
    channel had a stale 'attention' job) used to abort an entire 33-site
    batch, leaving all 33 unsubmitted. A batch must accept every site that
    is not blocked and only report the blocked one as skipped."""
    ready(store)
    request_id, skipped = store.submit("wp25", [target("wp_two"), target()], "second-request")
    assert skipped == ["wp_one"]
    site_ids = {row["site_id"] for row in store.snapshot() if row["request_id"] == request_id}
    assert site_ids == {"wp_two"}
    assert len(store.snapshot()) == 2  # the original wp_one job plus the new wp_two job


def test_batch_raises_when_every_site_in_it_is_blocked(store):
    ready(store)
    store.submit("wp25", [target("wp_two")], "occupy-wp-two")
    store.claim()
    with pytest.raises(Conflict):
        store.submit("wp25", [target(), target("wp_two")], "third-request")


def test_single_site_submit_still_raises_conflict_when_blocked(store):
    ready(store)
    with pytest.raises(Conflict):
        store.submit("wp_wp_one", [target()], "second-request")


def test_a_stale_active_job_no_longer_blocks_new_submissions(store):
    """A job with no terminal outcome (most often 'attention', which
    nothing ever auto-clears) used to block that site forever. Past the
    staleness window it must stop counting as active."""
    from control_center.operations import STALE_ACTIVE_JOB_SECONDS
    ready(store)
    with store.connect() as db:
        db.execute("UPDATE jobs SET created=?", (time.time() - STALE_ACTIVE_JOB_SECONDS - 60,))
    request_id, skipped = store.submit("wp_wp_one", [target()], "fresh-request")
    assert skipped == []


def test_a_repeatedly_reclaimed_job_still_goes_stale_by_its_original_age(store):
    """Confirmed live: an 'attention' job keeps getting reclaimed and
    re-polled by the worker, which bumps `updated` every cycle - so a job
    stuck for 20+ hours can still show "updated moments ago" forever.
    Staleness must be measured from `created`, which never changes."""
    from control_center.operations import STALE_ACTIVE_JOB_SECONDS
    ready(store)
    with store.connect() as db:
        db.execute("UPDATE jobs SET created=?, updated=?",
                   (time.time() - STALE_ACTIVE_JOB_SECONDS - 60, time.time()))
    request_id, skipped = store.submit("wp_wp_one", [target()], "fresh-request")
    assert skipped == []


def test_claim_retires_a_job_stuck_past_the_give_up_window_instead_of_looping_forever(store):
    """The staleness window in submit() only stops a dead job from
    blocking NEW requests - the dead job itself sat in the table forever,
    endlessly reclaimed and re-polled. claim() must retire it to 'stopped'
    once it is unambiguously dead, not merely stale."""
    from control_center.operations import STALE_JOB_GIVE_UP_SECONDS
    ready(store)
    with store.connect() as db:
        db.execute("UPDATE jobs SET created=?, lease=0, next_poll=0",
                   (time.time() - STALE_JOB_GIVE_UP_SECONDS - 60,))
    assert store.claim() is None  # this cycle retires it rather than handing it to a worker
    snapshot = store.snapshot()
    assert snapshot[0]["phase"] == "stopped"


def test_restart_recovers_accepted_but_never_redispatches_ambiguous_send(store):
    data = ready(store)
    with store.connect() as db:
        db.execute("UPDATE jobs SET lease=0")
    gateway = Mock()
    reopened = Store(store.path)
    Worker(reopened, gateway).tick()
    gateway.dispatch.assert_not_called()
    assert reopened.snapshot()[0]["phase"] == "attention"
    assert reopened.secret("csrf") == store.secret("csrf")


def test_dispatch_uses_exact_returned_id_without_recent_run_search(store):
    job = ready(store)
    gateway = GitHubGateway("owner/repo", "fake", lambda: [])
    response = Mock(status_code=200)
    response.json.return_value = {"workflow_run_id":123}
    with patch("control_center.operation_gateway.requests.post", return_value=response) as post, patch.object(gateway,"get",return_value={"state":"active"}) as get:
        gateway.dispatch(job)
    assert job["run_id"] == 123 and job["phase"] == "queued"
    assert post.call_args.kwargs["json"]["return_run_details"] is True
    get.assert_called_once_with("/actions/workflows/writer.yml")


@pytest.mark.parametrize("code,phase", [(403,"failed"),(422,"failed"),(500,"attention"),(204,"attention")])
def test_dispatch_error_never_claims_acceptance(store,code,phase):
    job=ready(store)
    with patch.object(GitHubGateway,"get",return_value={"state":"active"}), patch("control_center.operation_gateway.requests.post",return_value=Mock(status_code=code)):
        GitHubGateway("owner/repo","fake",lambda:[]).dispatch(job)
    assert job["phase"] == phase and not job.get("run_id")


def test_poll_connection_loss_preserves_last_state(store):
    job=ready(store);job.update(phase="working",run_id=123);store.save(job)
    with store.connect() as db:db.execute("UPDATE jobs SET next_poll=0")
    gateway=Mock();gateway.poll.side_effect=requests.Timeout()
    Worker(store,gateway).tick()
    result=store.snapshot()[0]
    assert result["phase"]=="working" and result["connection_warning"]


def test_workflow_success_without_receipt_is_not_published(store):
    job=ready(store);job["run_id"]=123
    gateway=GitHubGateway("owner/repo","fake",lambda:[])
    with patch.object(gateway,"get",return_value={"status":"completed","conclusion":"success"}),patch.object(gateway,"artifacts",return_value={}):
        gateway.poll(job)
    assert job["phase"]=="attention" and not job["public_url"]


def test_wrong_site_or_draft_receipt_cannot_mark_published():
    job=target()
    for status,site in [("✅ DRAFT","https://example.com"),("✅ OK","https://other.com")]:
        files={"newsroom_publish_result.json":json.dumps({"records":[{"site":site,"status":status,"url":"https://example.com/post"}]})}
        assert not publication_receipt(files,job)
    files={"newsroom_publish_result.json":json.dumps({"records":[{"site":"https://example.com","status":"✅ OK","url":"https://example.com/post"}]})}
    assert publication_receipt(files,job)=="https://example.com/post"


def test_blogger_follows_only_matching_child_and_verified_job(store):
    job=ready(store,target("blogger_one","blogger"));job["run_id"]=123
    gateway=GitHubGateway("owner/repo","fake",lambda:[])
    handoff={"parent_run_id":"123","site_id":"blogger_one","job_id":"exact-job","workflow_run_id":456}
    with patch.object(gateway,"get",return_value={"status":"completed","conclusion":"success"}),patch.object(gateway,"artifacts",return_value={"control-handoff.json":json.dumps(handoff)}):
        gateway.poll(job)
    assert job["run_id"]==456 and job["phase"]=="publishing"
    receipt=dict(job_id="wrong",site_id="blogger_one",ok=True,status="published",public_url="https://example.com/post")
    assert not publication_receipt({"platform-worker.log":json.dumps(receipt)},job)
    receipt["job_id"]="exact-job"
    assert publication_receipt({"platform-worker.log":json.dumps(receipt)},job)


def test_exact_tistory_queue_row_unlocks_review_then_publication(store):
    job=ready(store,target("tistory_one","tistory"));job["run_id"]=123
    row=dict(job_id=job["review_job_id"],site_id="tistory_one",status="ready",title="Title",content_html="<p>Draft</p>")
    gateway=GitHubGateway("owner/repo","fake",lambda:[dict(row,job_id="older-job")])
    assert not gateway.poll_queue(job)
    gateway.queue_rows=lambda:[row]
    assert gateway.poll_queue(job) and job["phase"]=="review_ready"
    assert job["review_job_id"] in job["review_url"]
    row.update(status="published",public_url="https://example.com/new-post")
    gateway.poll_queue(job)
    assert job["phase"]=="published"


def test_rss_baseline_restart_and_new_article_are_idempotent(store,tmp_path):
    config=tmp_path/'rss.json';config.write_text(json.dumps({'sources':[],'poll_seconds':60}))
    watcher=RSSWatcher(store,config,lambda:[])
    source={'key':'feed','language':'ko'}
    old={'title':'Old','url':'https://example.com/old','published':time.time()}
    watcher.ingest(source,[old])
    watcher=RSSWatcher(Store(store.path),config,lambda:[])
    new=dict(old,title='New',url='https://example.com/new')
    watcher.ingest(source,[old,new]);watcher.ingest(source,[old,new])
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM rss_items WHERE state='waiting'").fetchone()[0]==1
        assert db.execute("SELECT count(*) FROM rss_items").fetchone()[0]==2


def test_rss_does_not_cap_new_articles_at_ten(store,tmp_path):
    config=tmp_path/'rss.json';config.write_text(json.dumps({'sources':[],'poll_seconds':60}))
    watcher=RSSWatcher(store,config,lambda:[]);source={'key':'feed','language':'ko'}
    watcher.ingest(source,[])
    watcher.ingest(source,[{'title':str(i),'url':f'https://example.com/{i}','published':time.time()} for i in range(25)])
    assert watcher.status()['waiting']==25


def test_rss_dispatch_keeps_detected_evidence_even_after_feed_rotation(store,tmp_path):
    config=tmp_path/'rss.json';config.write_text(json.dumps({'sources':[],'poll_seconds':60}))
    target=dict(site_id='news-ko',label='koreanews365.com',platform='news',inputs={'newsroom':'koreanews365'})
    watcher=RSSWatcher(store,config,lambda:[target]);source={'key':'feed','language':'ko'}
    watcher.ingest(source,[])
    item={'title':'New source story','url':'https://example.com/story','published':time.time(),'summary':'Captured facts'}
    watcher.ingest(source,[item])
    watcher.ingest(source,[])
    watcher.scan()
    with store.connect() as db:
        jobs=db.execute('SELECT payload FROM jobs').fetchall()
    assert len(jobs)==1
    payload=json.loads(jobs[0][0])
    assert json.loads(payload['inputs']['source_item'])['summary']=='Captured facts'
    assert payload['inputs']['source_url']==item['url']


def test_feed_parser_rejects_html_and_handles_rss_atom():
    with pytest.raises(ValueError):parse_feed('<html><body>Blocked</body></html>')
    assert parse_feed('<rss><channel><item><title>News</title><link>https://example.com/a</link></item></channel></rss>')[0]['url']=='https://example.com/a'
    assert parse_feed('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>News</title><link href="https://example.com/b"/></entry></feed>')[0]['url']=='https://example.com/b'


@pytest.mark.parametrize('phase', ['working','publishing','published'])
def test_actual_publisher_checkpoints_drive_live_stages(store,phase):
    job=ready(store);job['run_id']=123
    event=dict(phase=phase,site_url='https://example.com',run_id='123',public_url='https://example.com/post',detail='Observed checkpoint')
    def get(path):
        if '/check-runs?' in path:
            return {'check_runs':[{'id':1,'external_id':'123','output':{'summary':json.dumps(event)}}]}
        return {'head_sha':'abc','status':'in_progress'}
    gateway=GitHubGateway('owner/repo','fake',lambda:[])
    with patch.object(gateway,'get',side_effect=get):gateway.poll(job)
    assert job['phase']==phase


def test_telemetry_failure_does_not_raise_into_publisher(monkeypatch):
    from scripts import publication_progress
    for key in ('GH_TOKEN','GITHUB_REPOSITORY','GITHUB_RUN_ID','GITHUB_SHA'):monkeypatch.setenv(key,'fixture')
    monkeypatch.setattr(publication_progress,'_check_id',None)
    with patch.object(publication_progress.requests,'post',side_effect=requests.Timeout()):
        publication_progress.report('publishing','https://example.com')


def test_news_workflow_has_no_fixed_publication_schedule():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    workflow=(root/'.github/workflows/newsrooms-daily-publisher.yml').read_text(encoding='utf-8')
    assert '\n  schedule:' not in workflow
    assert 'NEWSROOM_SOURCE_URL: ${{ inputs.source_url }}' in workflow
    worker=(root/'scripts/autopost_mega.py').read_text(encoding='utf-8')
    assert 'published_today >= daily_target' not in worker


def test_newsroom_cost_hold_records_new_items_without_dispatch(store, tmp_path, monkeypatch):
    from control_center import rss_watch
    hold = tmp_path / "newsroom-hold"
    hold.touch()
    monkeypatch.setattr(rss_watch, "NEWSROOM_COST_HOLD", hold)
    source = {"key": "desk", "name": "Desk", "language": "ko", "feed": "https://example.com/feed"}
    config = tmp_path / "rss.json"
    config.write_text(json.dumps({"sources": [source], "poll_seconds": 60}))
    descriptor = dict(target(), label="koreanews365.com")
    watcher = RSSWatcher(store, config, lambda: [descriptor])
    watcher.ingest(source, [])
    response = Mock()
    response.text = '<rss><channel><item><title>New story</title><link>https://example.com/new</link></item></channel></rss>'
    monkeypatch.setattr(rss_watch.requests, "get", Mock(return_value=response))
    watcher.scan()
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM rss_items WHERE state='waiting'").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    assert "비용 중지" in watcher.status()["message"]


@pytest.mark.parametrize("state,phase", [("disabled_manually", "stopped"), ("disabled_inactivity", "stopped"), (None, "attention")])
def test_disabled_or_unknown_workflow_never_dispatches(store, state, phase):
    job = ready(store)
    gateway = GitHubGateway("owner/repo", "fake", lambda: [])
    with patch.object(gateway, "get", return_value={"state":state}), patch("control_center.operation_gateway.requests.post") as post:
        gateway.dispatch(job)
    post.assert_not_called()
    assert job["phase"] == phase and not job.get("run_id")
