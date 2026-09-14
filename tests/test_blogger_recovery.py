import base64,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from datetime import datetime
from scripts import budget_guard as b
from automation_hub.blogger_rewriter import normalize_rewrite_format,extract_http_links,plain_text
class RecoveryTests(unittest.TestCase):
 def test_budget_conflict_reloads_and_keeps_other_writer(self):
  month=datetime.now(b.KST).strftime('%Y-%m')
  def state(sha,total):
   return Mock(status_code=200,json=lambda:{'sha':sha,'content':base64.b64encode(json.dumps({'month':month,'spent_estimate_usd':total,'calls':[]}).encode()).decode()})
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'BUDGET_GITHUB_REPOSITORY':'owner/repo','GH_TOKEN':'secret','GITHUB_RUN_ID':'1','GITHUB_RUN_ATTEMPT':'1'}),patch.object(b,'STATE_FILE',Path(d)/'budget.json'),patch.object(b.requests,'get',side_effect=[state('old',1),state('new',2)]),patch.object(b.requests,'put',side_effect=[Mock(status_code=409),Mock(status_code=200)]) as put,patch.object(b.time,'sleep'):
   b.check_and_record(.03,label='site')
   sent=put.call_args.kwargs['json']
   self.assertEqual(sent['sha'],'new')
   saved=json.loads(base64.b64decode(sent['content']))
   self.assertEqual(saved['spent_estimate_usd'],2.03)
   self.assertEqual(saved['calls'][0]['cost_type'],'estimate')
 def test_budget_failure_blocks_paid_execution(self):
  with patch.dict(os.environ,{'BUDGET_GITHUB_REPOSITORY':'owner/repo','GH_TOKEN':'secret','GITHUB_RUN_ID':'1'}),patch.object(b.requests,'get',return_value=Mock(status_code=403)):
   with self.assertRaises(RuntimeError):b.check_and_record(.03,label='site')
 def test_clipping_never_collapses_article_to_intro(self):
  article={'title':'Title','meta_description':'Description.','content_html':'<p>Short intro.</p><p>'+('Substantive detail. '*400)+'</p>'}
  result=normalize_rewrite_format(article,target_chars=1800)
  self.assertEqual(result['content_html'],article['content_html'])
 def test_clipping_keeps_verified_evidence(self):
  urls=['https://example.org/a','https://example.net/b']
  body='<p>'+('Details about the topic. '*40)+'</p>'
  article={'title':'Title','meta_description':'Description.','content_html':body*5+''.join(f'<p><a href="{u}">Evidence</a></p>' for u in urls)}
  result=normalize_rewrite_format(article,target_chars=1800,preserve_urls=urls)
  self.assertTrue(set(urls)<=set(extract_http_links(result['content_html'])))
if __name__=='__main__':unittest.main()
