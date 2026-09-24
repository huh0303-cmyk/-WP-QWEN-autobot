"""Read-only public publication evidence. No model calls or publishing."""
import json,datetime,pathlib,requests,concurrent.futures,html,os,sqlite3
ROOT=pathlib.Path('/opt/korea365')
OUT=ROOT/'data/publication-board.json'
KST=datetime.timezone(datetime.timedelta(hours=9))
def read_json(path,default):
 try:return json.loads(path.read_text(encoding='utf-8'))
 except (OSError,ValueError):return default

def attach_index_metrics(rows,now):
 audits=read_json(ROOT/'index_audit_manifest.json',{}).get('sites',{})
 snapshots=[read_json(ROOT/'data'/name,{}) for name in ['core_metrics_latest.json','core_metrics_daily_latest.json','core_metrics_cached.json']]
 history=read_json(ROOT/'data/core_metrics_history.json',{}).get('days',{})
 previous={r['url'].rstrip('/'):r for r in history.get((now.date()-datetime.timedelta(days=1)).isoformat(),{}).get('records',[])}
 latest={}
 for snapshot in snapshots:
  for r in snapshot.get('records',[]):
   url=r.get('url','').rstrip('/');stamp=r.get('index_checked_at') or ''
   if stamp and stamp>(latest.get(url,{}).get('index_checked_at') or ''):latest[url]=r
 for row in rows:
  url=row['url'].rstrip('/');r=latest.get(url,{});a=audits.get(url) or audits.get(url+'/') or {};summary=a.get('summary',{})
  if (a.get('audited_at') or '')>(r.get('index_checked_at') or ''):
   r={'indexed':summary.get('indexed'),'index_partial':bool(summary.get('unknown')) or bool(a.get('error')),'index_checked_at':a.get('audited_at')}
  value=r.get('indexed');stamp=r.get('index_checked_at');partial=r.get('index_partial',False)
  row.update(indexed=value if isinstance(value,int) and stamp else None,index_delta=None,index_checked_at=stamp,index_partial=partial)
  old=previous.get(url,{})
  try:
   day=datetime.datetime.fromisoformat(stamp).astimezone(KST).date()
   prior_day=datetime.datetime.fromisoformat(old.get('index_checked_at')).astimezone(KST).date()
   if day==now.date() and prior_day==day-datetime.timedelta(days=1) and not partial and not old.get('index_partial') and isinstance(old.get('indexed'),int) and row['indexed'] is not None:row['index_delta']=row['indexed']-old['indexed']
  except (ValueError,TypeError):pass
 return rows

def attach_daily_changes(rows,now):
 path=ROOT/'data/publication-metric-days.json'
 history=read_json(path,{'days':{}});days=history.setdefault('days',{})
 prior=days.get((now.date()-datetime.timedelta(days=1)).isoformat(),{})
 current={}
 for r in rows:
  old=prior.get(r['url'],{})
  r['published_delta']=None
  if isinstance(r.get('published_total'),int) and isinstance(old.get('published_total'),int):
   r['published_delta']=r['published_total']-old['published_total']
  # Only compare complete, freshly checked GSC counts on adjacent days.
  try:
   fresh=datetime.datetime.fromisoformat(r['index_checked_at']).astimezone(KST).date()==now.date()
   prior_fresh=datetime.datetime.fromisoformat(old['index_checked_at']).astimezone(KST).date()==now.date()-datetime.timedelta(days=1)
   if fresh and prior_fresh and not r.get('index_partial') and not old.get('index_partial') and isinstance(r.get('indexed'),int) and isinstance(old.get('indexed'),int):r['index_delta']=r['indexed']-old['indexed']
  except (KeyError,TypeError,ValueError):pass
  current[r['url']]={k:r.get(k) for k in ['published_total','indexed','index_checked_at','index_partial']}
 days[now.date().isoformat()]=current
 history['days']={k:v for k,v in days.items() if k>=(now.date()-datetime.timedelta(days=35)).isoformat()}
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(history));os.replace(temp,path)

def four_metrics_html(row):
 esc=lambda x:html.escape(str(x),quote=True)
 def number(value,delta,unit):
  if value is None:return '미확인 (—)'
  return f'{value:,}{unit} ('+('비교자료 없음' if delta is None else f'{delta:+,}')+')'
 values=[('① 일일 방문자 수',number(row.get('yesterday_visitors'),row.get('visitor_delta'),'명'),'전날 기준 · 전전일 대비'),
 ('② 누적 방문자 수',number(row.get('cumulative_visitors'),row.get('cumulative_delta'),'명'),'전날 마감 · 전전일 마감 대비 · 자체 카운터'),
 ('③ 발행 글 수',number(row.get('published_total'),row.get('published_delta'),'건'),'현재 공개 글 · 전날 마지막 집계 대비'),
 ('④ 구글 색인 글 수 · GSC',index_label(row),'GSC 확인일: '+str(row.get('index_checked_at') or '미확인'))]
 return '<div class="four-metrics" style="display:grid;grid-template-columns:1fr;gap:8px;margin:14px 0">'+''.join('<div style="background:#eef4ff;border:1px solid #c8d8f4;border-radius:9px;padding:10px"><b>'+esc(label)+'</b><div style="font-size:23px;font-weight:850">'+esc(value)+'</div><small style="color:#68788c">'+esc(note)+'</small></div>' for label,value,note in values)+'</div>'

def index_label(row):
 v=row.get('indexed');d=row.get('index_delta')
 if v is None:return '미확인 (비교 자료 없음)'
 if row.get('index_partial'):return f'{v:,}건 확인 · 일부 미확인 (비교 자료 없음)'
 return f'{v:,}건 ('+('비교 자료 없음' if d is None else f'{d:+,}')+')'

def collect():
 now=datetime.datetime.now(KST)
 profiles=json.loads((ROOT/'config/content_engine_profiles.json').read_text())['profiles']
 sites={p['wordpress']['url'].rstrip('/'):p['wordpress'] for p in profiles if p.get('wordpress',{}).get('url')}
 def check(pair):
  url,profile=pair;domain=url.split('//')[-1];news=domain in ['koreanews365.com','theseouljournal.com']
  row={'site':domain,'url':url,'kind':'신문사' if news else 'WP','target':'1건','checked_at':now.isoformat(),'today':None,'latest_url':'','latest_title':'','categories':[],'next':'작성 경로 확인 필요','error':''}
  try:
   s=requests.Session();s.params={'_audit':int(now.timestamp())}
   r=s.get(url+'/wp-json/wp/v2/posts',params={'per_page':100,'orderby':'date','order':'desc','_fields':'id,date_gmt,title,link'},timeout=25);r.raise_for_status();posts=r.json();row['published_total']=int(r.headers['X-WP-Total']) if r.headers.get('X-WP-Total') is not None else None
   row['history']=[{'id':p['id'],'title':html.unescape(p['title']['rendered']),'url':p['link'],'published_at':p['date_gmt']+'Z','published_kst':publication_date(p['date_gmt']+'Z')} for p in posts[:10]]
   row['today']=sum(datetime.datetime.fromisoformat(p['date_gmt']).replace(tzinfo=datetime.timezone.utc).astimezone(KST).date()==now.date() for p in posts)
   if posts:row.update(latest_url=posts[0]['link'],latest_title=html.unescape(posts[0]['title']['rendered']),latest_at=posts[0]['date_gmt']+'Z')
   r=s.get(url+'/wp-json/wp/v2/categories',params={'per_page':100,'hide_empty':'true','_fields':'id,name,count'},timeout=25);r.raise_for_status();row['categories']=[html.unescape(c['name']) for c in r.json()]
   row['status']=('오늘 발행 확인' if row['today']>= 1 else '목표까지 추가 발행 필요')
   if news:
    row['next']='RSS 감지 중 · 유료 작성 승인 대기' if pathlib.Path('/etc/korea365/newsroom-cost-hold').exists() else 'RSS 감지 중 · OpenAI 잔액/한도 부족(429), Gemini 403 해결 필요'
   else:row['next']='무료 검수 원고 준비 필요 · 자동작성 복구 미완료'
  except Exception as e:row.update(status='확인 실패',error=type(e).__name__+': '+str(e)[:180])
  return row
 def traffic(row):
  row.update(yesterday_visitors=None,visitor_delta=None,visitor_error='')
  try:
   r=requests.get(row['url']+'/wp-json/site-stats/v1/visitors',params={'_audit':int(now.timestamp())},timeout=20);r.raise_for_status();v=r.json()
   yesterday=(now.date()-datetime.timedelta(days=1)).isoformat();prior=(now.date()-datetime.timedelta(days=2)).isoformat()
   if v.get('yesterday_date')!=yesterday:raise ValueError('집계 날짜 불일치')
   if isinstance(v.get('yesterday_count'),int) and v['yesterday_count']>=0:row['yesterday_visitors']=v['yesterday_count']
   if row['yesterday_visitors'] is not None and v.get('day_before_yesterday_date')==prior and isinstance(v.get('day_before_yesterday_count'),int):row['visitor_delta']=v['yesterday_count']-v['day_before_yesterday_count']
   row['visitor_date']=yesterday
   if v.get('date')==now.date().isoformat() and isinstance(v.get('total'),int) and isinstance(v.get('count'),int) and v['total']>=v['count']:
    row['cumulative_visitors']=v['total']-v['count'];row['cumulative_delta']=row['yesterday_visitors']
  except Exception as e:row['visitor_error']=type(e).__name__+': '+str(e)[:120]
  return row
 rows=list(concurrent.futures.ThreadPoolExecutor(max_workers=5).map(check,sites.items()))
 rows=list(concurrent.futures.ThreadPoolExecutor(max_workers=5).map(traffic,rows))
 def blogcheck(p):
  b=p['blogspot'];url=b['url'].rstrip('/');row={'site':url.split('//')[-1],'url':url,'kind':'Blogspot','target':'1건','today':None,'latest_url':'','latest_title':'','categories':[],'next':'무료 원고 순차 발행 중','error':'','checked_at':now.isoformat()}
  try:
   response=requests.get(url+'/feeds/posts/default',params={'alt':'json','max-results':100,'_audit':int(now.timestamp())},timeout=25);response.raise_for_status();feed=response.json()['feed'];entries=feed.get('entry',[]);row['published_total']=int(feed['openSearch$totalResults']['$t']) if feed.get('openSearch$totalResults') else None
   row['history']=[{'id':e['id']['$t'],'title':e['title']['$t'],'url':next(x['href'] for x in e['link'] if x['rel']=='alternate'),'published_at':e['published']['$t'],'published_kst':publication_date(e['published']['$t'])} for e in entries[:10]]
   row['today']=sum(datetime.datetime.fromisoformat(e['published']['$t']).astimezone(KST).date()==now.date() for e in entries)
   if entries:
    e=entries[0];row.update(latest_at=e['published']['$t'],latest_title=e['title']['$t'],latest_url=next(x['href'] for x in e['link'] if x['rel']=='alternate'),categories=[c['term'] for c in e.get('category',[])])
   row['status']='오늘 발행 확인' if row['today'] else '오늘 발행 필요'
   row['next']='오늘 목표 완료 · 다음 무료 원고 준비 필요' if row['today'] else '무료 원고 준비·발행 필요'
  except Exception as e:row.update(status='확인 실패',error=type(e).__name__)
  row.update(yesterday_visitors=None,visitor_delta=None,visitor_error='전날 방문 기록 없음',visitor_date=(now.date()-datetime.timedelta(days=1)).isoformat())
  try:
   with sqlite3.connect('file:'+str(ROOT/'data/blog-visitor-counts.sqlite3')+'?mode=ro',uri=True) as conn:
    y=conn.execute('SELECT count FROM daily WHERE site_key=? AND date=?',(p['site_key'],row['visitor_date'])).fetchone()
    previous=conn.execute('SELECT count FROM daily WHERE site_key=? AND date=?',(p['site_key'],(now.date()-datetime.timedelta(days=2)).isoformat())).fetchone()
    total=conn.execute('SELECT SUM(count) FROM daily WHERE site_key=? AND date<=?',(p['site_key'],row['visitor_date'])).fetchone()[0]
   if y is not None:row.update(cumulative_visitors=total,cumulative_delta=y[0])
   if y is not None:row.update(yesterday_visitors=y[0],visitor_error='',visitor_delta=y[0]-previous[0] if previous else None)
  except Exception as e:row['visitor_error']=type(e).__name__
  return row
 rows+=list(concurrent.futures.ThreadPoolExecutor(max_workers=6).map(blogcheck,profiles))
 rows=attach_index_metrics(rows,now)
 attach_daily_changes(rows,now)
 data={'checked_at':now.isoformat(),'timezone':'Asia/Seoul','sites':rows,'paid_api_calls':0}
 OUT.parent.mkdir(exist_ok=True);tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False));os.replace(tmp,OUT)
 print(json.dumps({'sites':len(rows),'today_published_sites':sum(bool(r['today']) for r in rows),'errors':sum(bool(r['error']) for r in rows)},ensure_ascii=False))
def sorted_cards(rows):
 return sorted(rows,key=lambda r:(r.get('yesterday_visitors') is None,-(r.get('yesterday_visitors') or 0),r['site']))

def visitor_label(row):
 count=row.get('yesterday_visitors');delta=row.get('visitor_delta')
 if count is None:return '미확인 (비교 자료 없음)'
 change='비교 자료 없음' if delta is None else (f'+{delta:,}' if delta>0 else f'{delta:,}')
 return f'{count:,}명 ({change})'

def publication_date(value):
 try:return datetime.datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(KST).strftime('%Y-%m-%d %H:%M KST')
 except (AttributeError,TypeError,ValueError):return '발행일 확인 필요'

def board():
 try:data=json.loads(OUT.read_text())
 except (OSError,ValueError):return '<p>발행 현황 수집 중입니다.</p>'
 esc=lambda x:html.escape(str(x),quote=True)
 checked=datetime.datetime.fromisoformat(data['checked_at']);visitor_day=(checked.date()-datetime.timedelta(days=1)).isoformat()
 sections=[]
 for kind,title in [('WP','WordPress 25개'),('Blogspot','블로그스팟 33개'),('신문사','신문사 2개 · 별도 운영')]:
  accent,tint={'WP':('#1d4ed8','#eff6ff'),'Blogspot':('#c2410c','#fff7ed'),'신문사':('#047857','#ecfdf5')}[kind]
  group=sorted_cards([r for r in data['sites'] if r['kind']==kind]);cards=[]
  complete=sum(r['today'] is not None and r['today'] >= (3 if kind=='신문사' else 1) for r in group)
  published=sum(r['today'] or 0 for r in group)
  last=None;rank=0
  for i,r in enumerate(group,1):
   count=r.get('yesterday_visitors')
   if count is not None:
    if count!=last:rank=i
    badge=f'{rank}위';last=count
   else:badge='순위 미확인'
   next_step=r['next']
   if kind=='WP' and r['today']:next_step='오늘 발행 완료 · 다음날 무료 자동작성 복구 확인 필요'
   cards.append('<article data-card-site="'+esc(r['site'])+'" style="background:white;border:1px solid #cbd5e1;border-top:5px solid '+accent+';border-radius:14px;padding:18px"><div style="display:flex;align-items:center;gap:14px;margin-bottom:16px"><div aria-label="방문자 순위" style="min-width:68px;padding:12px 8px;background:'+accent+';color:white;border-radius:12px;font-size:36px;font-weight:900;line-height:1.1;text-align:center">'+(str(rank)+'<span style="font-size:15px">위</span>' if count is not None else '<span style="font-size:16px">미확인</span>')+'</div><a style="font-weight:bold;color:#0369a1" href="'+esc(r['url'])+'" target="_blank" rel="noopener">'+esc(r['site'])+'</a></div><p style="font-size:12px;color:#64748b">카테고리</p><p style="font-size:23px;line-height:1.35;font-weight:800;color:'+accent+';background:'+tint+';border-radius:10px;padding:12px;margin:4px 0 16px">'+esc(' · '.join(r['categories']) or '공개 글 분류 없음')+'</p>'+four_metrics_html(r)+'<hr style="margin:12px 0"><p>오늘 발행 <b>'+('미확인' if r['today'] is None else str(r['today'])+'건')+'</b> / 목표 '+r['target']+'</p><p>'+esc(r['status'])+'</p><p style="font-size:12px">'+esc(next_step)+'</p><p style="color:#b91c1c">'+esc(r['error'])+'</p>'+('<a style="color:#0369a1;text-decoration:underline" href="'+esc(r['latest_url'])+'" target="_blank" rel="noopener">최근 글: '+esc(r['latest_title'])+'</a><p style="font-size:13px;margin-top:6px;color:#475569">발행일: '+esc(publication_date(r.get('latest_at')))+'</p>' if r['latest_url'] else '')+'<button type="button" data-card-publish-url="'+esc(r['url'])+'" style="width:50%;margin-top:18px;padding:13px 6px;background:'+accent+';color:white;border:0;border-radius:10px;font-size:16px;font-weight:800;cursor:pointer">즉시발행</button><p data-quick-status="" role="status" aria-live="polite" style="font-size:12px;margin-top:6px;color:#475569"></p></article>')
  sections.append('<section data-platform="'+kind+'" style="margin-top:28px"><h3 style="font-size:23px;font-weight:bold;color:'+accent+';background:'+tint+';border-left:6px solid '+accent+';padding:12px 16px;border-radius:8px">'+title+'</h3><p>오늘 목표 달성 '+str(complete)+'/'+str(len(group))+'곳 · 공개 '+str(published)+'건 · 어제 방문자 내림차순</p><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:14px">'+''.join(cards)+'</div></section>')
 stale=(datetime.datetime.now(KST)-checked).total_seconds()>1200
 return '<section id="publication-board" style="max-width:1280px;margin:24px auto;padding:16px"><h2 style="font-size:28px;font-weight:bold">사이트별 운영 카드</h2><p>방문자 기준일 '+visitor_day+' · 한국시간 00:00~24:00 · 괄호는 전전일 대비 증감</p><p>같은 방문자 수는 공동 순위 · 미확인은 맨 아래 · 수집 기록이 없으면 0명으로 표시하지 않습니다.</p><p style="font-size:12px">방문자는 사이트 자체 카운터 집계이며 플랫폼 간 측정 방식이 다를 수 있습니다. 갱신 '+esc(data['checked_at'])+(' · 갱신 지연' if stale else '')+'</p>'+''.join(sections)+'</section>'
if __name__=='__main__':collect()
