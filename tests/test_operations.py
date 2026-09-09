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
    request_id = next(r for r in results if r)
    store.submit("wp25", [target()], request_id)
    assert len(store.snapshot()) == 1
    with pytest.raises(Conflict):
        store.submit("wp_wp_one", [target()], "another-request")


def test_conflicting_batch_accepts_nothing(store):
    ready(store)
    with pytest.raises(Conflict):
        store.submit("wp25", [target("wp_two"), target()], "second-request")
    assert len(store.snapshot()) == 1


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
    with patch("control_center.operation_gateway.requests.post", return_value=response) as post, patch.object(gateway,"get") as get:
        gateway.dispatch(job)
    assert job["run_id"] == 123 and job["phase"] == "queued"
    assert post.call_args.kwargs["json"]["return_run_details"] is True
    get.assert_not_called()


@pytest.mark.parametrize("code,phase", [(403,"failed"),(422,"failed"),(500,"attention"),(204,"attention")])
def test_dispatch_error_never_claims_acceptance(store,code,phase):
    job=ready(store)
    with patch("control_center.operation_gateway.requests.post",return_value=Mock(status_code=code)):
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
