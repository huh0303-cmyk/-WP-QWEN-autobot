import copy
from datetime import datetime
from pathlib import Path
import sys
from unittest.mock import Mock
import requests
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import daily_publication_floor as floor

NOW=datetime(2026,9,12,10,tzinfo=floor.KST)
WP={'site_id':'wp_example','platform':'wordpress','url':'https://example.org','secret_name':'EXAMPLE_PASS'}
BLOG={'site_id':'blogger_example','platform':'blogger','url':'https://example.blogspot.com'}

class API:
    def __init__(self,state=None,runs=None,handoff=None):
        self.state=state or {};self.runs=runs or {};self.saved=[];self.sent=[];self.child=handoff
    def load(self,sid):return copy.deepcopy(self.state),'sha'
    def save(self,sid,state,sha):self.saved.append(copy.deepcopy(state));return 'next-sha'
    def run(self,rid):return self.runs[rid]
    def handoff(self,rid,sid):return self.child
    def dispatch(self,workflow,inputs):
        assert self.saved[-1]['status']=='CLAIMED'
        self.sent.append((workflow,inputs));return 123

def test_all_25_wp_and_33_blogger_are_in_daily_scope():
    assert len(floor.sites_for('wordpress'))==25
    assert len(floor.sites_for('blogger'))==33
    assert len(floor.sites_for('newsroom'))==2

def test_already_public_site_never_dispatches():
    api=API()
    row,used=floor.reconcile(WP,{'status':'PUBLISHED','url':'https://example.org/post','published_at':NOW.isoformat()},api,NOW,True)
    assert row['status']=='PUBLISHED' and not used and not api.sent

def test_due_wp_claims_before_public_dispatch(monkeypatch):
    monkeypatch.setenv('EXAMPLE_PASS','test-not-real')
    api=API()
    row,used=floor.reconcile(WP,{'status':'DUE'},api,NOW,True)
    assert used and row['status']=='DISPATCHED'
    assert api.sent[0][1]['publication_approved']=='true'
    assert api.saved[-1]['run_id']==123

def test_unknown_dispatch_is_never_replayed():
    api=API({'status':'CLAIMED','day':'2026-09-11','attempts':1})
    row,used=floor.reconcile(WP,{'status':'DUE'},api,NOW,True)
    assert row['status']=='DISPATCH_UNCERTAIN' and not used and not api.sent

def test_timeout_leaves_claim_and_consumes_batch_slot(monkeypatch):
    monkeypatch.setenv('EXAMPLE_PASS','test-not-real')
    api=API();api.dispatch=Mock(side_effect=requests.Timeout())
    row,used=floor.reconcile(WP,{'status':'DUE'},api,NOW,True)
    assert used and row['status']=='DISPATCH_UNCERTAIN'
    assert api.saved[-1]['status']=='CLAIMED'

def test_read_failure_does_not_trigger_generation():
    api=API()
    row,used=floor.reconcile(WP,{'status':'READ_ERROR'},api,NOW,True)
    assert row['status']=='READ_ERROR' and not used and not api.saved

def test_finished_failed_worker_can_retry_once(monkeypatch):
    monkeypatch.setenv('EXAMPLE_PASS','test-not-real')
    api=API({'status':'DISPATCHED','day':'2026-09-12','attempts':1,'run_id':1}, {1:{'status':'completed','conclusion':'failure'}})
    row,used=floor.reconcile(WP,{'status':'DUE'},api,NOW,True)
    assert used and row['attempts']==2

def test_successful_draft_is_not_counted_or_duplicated():
    api=API({'status':'DISPATCHED','day':'2026-09-12','attempts':1,'run_id':1}, {1:{'status':'completed','conclusion':'success','updated_at':NOW.isoformat()}})
    row,used=floor.reconcile(WP,{'status':'DUE'},api,NOW,True)
    assert row['status']=='AWAITING_PUBLIC' and not used and not api.sent

def test_blogger_handoff_waits_for_child_not_parent_success():
    api=API({'status':'DISPATCHED','day':'2026-09-12','attempts':1,'run_id':1},
            {1:{'status':'completed','conclusion':'success'},2:{'status':'in_progress'}},
            {'workflow_run_id':2,'job_id':'exact-job'})
    row,used=floor.reconcile(BLOG,{'status':'DUE'},api,NOW,True)
    assert row['status']=='RUNNING' and row['run_id']==2 and not used

def test_failed_blogger_child_retries_same_job_without_rewriting():
    api=API({'status':'DISPATCHED','day':'2026-09-12','attempts':1,'child_run_id':2,'child_job_id':'exact-job'},
            {2:{'status':'completed','conclusion':'failure'}})
    row,used=floor.reconcile(BLOG,{'status':'DUE'},api,NOW,True)
    assert used and api.sent[0]==('platform-publish-v2.yml',{'platform':'blogger','job_id':'exact-job','max_jobs':'1'})

def test_no_more_than_two_generation_attempts_per_site_day():
    api=API({'status':'FAILED','day':'2026-09-12','attempts':2})
    row,used=floor.reconcile(BLOG,{'status':'DUE'},api,NOW,True)
    assert row['status']=='REPAIR_REQUIRED' and not used and not api.sent
