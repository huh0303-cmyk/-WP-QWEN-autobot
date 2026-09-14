import json
from control_center.operation_gateway import publication_wait, publication_receipt

def test_daily_cap_is_deferral_for_exact_job_only():
    files={'platform-worker.log':json.dumps({'job_id':'one','site_id':'blogger_a','status':'waiting','reason':'daily_limit_reached'})}
    job={'publish_job_id':'one','site_id':'blogger_a','site_url':'https://a.blogspot.com'}
    assert publication_wait(files,job)
    assert not publication_receipt(files,job)
    assert not publication_wait(files,dict(job,publish_job_id='other'))
    assert not publication_wait(files,dict(job,site_id='blogger_b'))

def test_inventory_failure_does_not_become_normal_wait():
    files={'platform-worker.log':json.dumps({'job_id':'one','status':'waiting','reason':'publication_count_unavailable'})}
    assert not publication_wait(files,{'publish_job_id':'one','site_id':'blogger_a'})
