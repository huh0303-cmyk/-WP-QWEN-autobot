import json
from datetime import datetime, timezone, timedelta
from automation_hub.cached_wp_sources import cached_posts

def test_cache_rejects_stale_unpublished_and_foreign_hosts(tmp_path):
    folder=tmp_path/'data/wp-source-snapshots';folder.mkdir(parents=True)
    now=datetime.now(timezone.utc)
    data={'site_url':'https://example.com','fetched_at':now.isoformat(),'posts':[
        {'status':'publish','link':'https://example.com/a','content':{'rendered':'<p>Source</p>'}},
        {'status':'draft','link':'https://example.com/b','content':{'rendered':'private'}},
        {'status':'publish','link':'https://other.com/a','content':{'rendered':'other'}}]}
    p=folder/'example.com.json';p.write_text(json.dumps(data))
    assert len(cached_posts('https://example.com',root=tmp_path,now=now))==1
    assert cached_posts('https://example.com',root=tmp_path,now=now+timedelta(days=2))==[]
    assert cached_posts('https://example.com',root=tmp_path,now=now-timedelta(hours=1))==[]
