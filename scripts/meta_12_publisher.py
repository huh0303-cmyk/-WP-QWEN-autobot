"""Fail-closed randomized publisher for six Instagram and six Threads accounts."""
import hashlib,json,os,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from meta_12_identity import validated_user_id
ROOT=Path(__file__).resolve().parents[1];POLICY=json.loads((ROOT/'config/meta_12_account_daily_policy.json').read_text(encoding='utf-8'))
STATE=ROOT/'data/meta_12_publishing_receipts.json';READINESS=ROOT/'data/meta_12_destination_readiness.json';QUEUE=ROOT/'data/meta_12_seoul_journal_queue.json';KST=timezone(timedelta(hours=9));REPO='huh0303-cmyk/-WP-QWEN-autobot'

def api(url,token,method='GET',form=None):
    body=urllib.parse.urlencode(form).encode() if form is not None else None
    headers={'Authorization':'Bearer '+token,'User-Agent':'LondonProject-Meta12-Publisher/1.0'}
    if body:headers['Content-Type']='application/x-www-form-urlencoded'
    try:
        with urllib.request.urlopen(urllib.request.Request(url,data=body,headers=headers,method=method),timeout=40) as r:return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:raise RuntimeError('Meta API HTTP '+str(e.code)) from None
    except Exception as e:raise RuntimeError('Meta API request failed: '+type(e).__name__) from None

def ready_gate():
    data=json.loads(READINESS.read_text(encoding='utf-8'));rows=data.get('targets',[])
    by={(x.get('platform'),x.get('account_key')):x for x in rows}
    expected={(p,a['key']) for a in POLICY['accounts'] for p in POLICY['platforms']}
    if set(by)!=expected:return False,'readiness registry does not contain exactly 12 destinations'
    pending=[f'{p}:{k}' for (p,k),r in by.items() if not(r.get('identity_verified') and r.get('write_scope_verified') and str(r.get('test_public_url','')).startswith('https://'))]
    return (not pending),('all 12 destination tests verified' if not pending else 'readiness incomplete: '+','.join(sorted(pending)))

def credentials():
    found={};missing=[]
    for a in POLICY['accounts']:
        for p in POLICY['platforms']:
            prefix=f"META_{p.upper()}_{a['key'].upper()}";token=os.environ.get(prefix+'_ACCESS_TOKEN','').strip();uid=os.environ.get(prefix+'_USER_ID','').strip()
            if not token:missing.append(prefix)
            found[(p,a['key'])]=(token,uid)
    return found,missing

def source_for(slot):
    if not next(a for a in POLICY['accounts'] if a['key']==slot['account_key']).get('source_required'):return None
    data=json.loads(QUEUE.read_text(encoding='utf-8')) if QUEUE.exists() else {'items':{}}
    item=data.get('items',{}).get(slot['slot_id'])
    if not item or item.get('reviewed') is not True or not str(item.get('source_url','')).startswith('https://') or not item.get('verified_facts'):raise RuntimeError('source-backed reviewed queue item required')
    return item

def generate(account,platform,slot,source):
    key=os.environ.get('GEMINI_API_KEY','').strip()
    if not key:raise RuntimeError('content-generation secret missing')
    if source:
        brief='Verified source URL: '+source['source_url']+'\nVerified facts: '+json.dumps(source['verified_facts'],ensure_ascii=False)
        content_rule='Use only the listed verified facts. Include the source URL. Do not add claims.'
    elif account['key'] in ('english_sos1','japanese_sos1','chinese_sos1','korean_sos1'):
        brief='Create exactly three short practical beginner phrases in '+account['language']+'. Include original script, Latin romanization, Korean phonetic reading, Korean meaning and English meaning. Keep each platform version self-contained.'
        content_rule='Educational content only; do not invent facts or reuse a prior phrase. Image title/subtitle must be concise Latin characters (transliteration is allowed).'
    elif account['key']=='seoul_jisoo1':
        brief='Create one useful Seoul shopping or everyday lifestyle tip in Korean.'
        content_rule='No current prices, health treatment promises, fake rankings, or invented links.'
    else:
        brief='Create one concise neutral Korean politics/current-affairs post from the provided source brief.'
        content_rule='No unsupported claims, predictions, polling numbers or partisan insults.'
    limit=460 if platform=='threads' else 1700
    prompt=(f"Return strict JSON with keys caption, image_title, image_subtitle. Account={account['key']}; platform={platform}; slot={slot['slot_id']}. "
      f"Topic={account['topic']}. {brief} {content_rule} Caption <= {limit} characters. image_title and image_subtitle must be ASCII Latin text, each <= 70 chars. Original, useful, no markdown fences.")
    model=os.environ.get('META_GEMINI_FREE_MODEL','gemini-2.5-flash-lite');url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    req=urllib.request.Request(url+'?key='+urllib.parse.quote(key),data=json.dumps({'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'temperature':0.6,'responseMimeType':'application/json'}}).encode(),headers={'Content-Type':'application/json','User-Agent':'LondonProject-Meta12-Content/1.0'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=50) as r:payload=json.loads(r.read().decode())
    except urllib.error.HTTPError as e:raise RuntimeError('content API HTTP '+str(e.code)) from None
    except Exception as e:raise RuntimeError('content generation failed: '+type(e).__name__) from None
    raw=''.join(part.get('text','') for c in payload.get('candidates',[]) for part in c.get('content',{}).get('parts',[]))
    try:post=json.loads(raw)
    except Exception:raise RuntimeError('content response was not valid JSON') from None
    caption=str(post.get('caption','')).strip();title=str(post.get('image_title','')).strip();subtitle=str(post.get('image_subtitle','')).strip()
    if not caption or len(caption)>limit:raise RuntimeError('caption empty or exceeds platform limit')
    if platform=='threads' and len(caption)>500:raise RuntimeError('Threads character limit exceeded')
    return {'caption':caption,'image_title':title[:70],'image_subtitle':subtitle[:70]}

def make_image(path,account,slot,post):
    w,h=1080,1350;colors={'english_sos1':(18,38,74),'japanese_sos1':(106,29,51),'chinese_sos1':(120,36,33),'korean_sos1':(24,72,104),'seoul_jisoo1':(102,53,119),'seoul_journal1':(45,55,69)}
    im=Image.new('RGB',(w,h),colors[account['key']]);d=ImageDraw.Draw(im)
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';bold_path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    font=ImageFont.truetype(font_path,42);big=ImageFont.truetype(bold_path,70);small=ImageFont.truetype(font_path,30)
    d.rounded_rectangle((70,75,1010,1275),radius=46,outline=(255,255,255),width=4)
    brand=account['key'].replace('_',' ').upper();d.text((115,145),brand,font=font,fill=(255,255,255))
    d.line((115,220,965,220),fill=(255,255,255),width=3)
    title=''.join(c for c in post['image_title'] if ord(c)<128).strip() or 'TODAY\'S LESSON'
    subtitle=''.join(c for c in post['image_subtitle'] if ord(c)<128).strip()
    d.text((115,340),title[:32],font=big,fill=(255,224,105),spacing=12)
    wrapped=[]
    for line in subtitle.splitlines() or ['A useful idea for today']:
        wrapped.extend(__import__('textwrap').wrap(line,width=34) or [''])
    y=500
    for line in wrapped[:5]:d.text((120,y),line,font=font,fill=(255,255,255));y+=68
    d.text((115,1150),'LONDON PROJECT  •  '+slot['date_kst'],font=small,fill=(205,218,238))
    path.parent.mkdir(parents=True,exist_ok=True);im.save(path,format='PNG',optimize=True)

def commit(paths,message):
    if not paths:return
    subprocess.run(['git','add',*paths],cwd=ROOT,check=True,capture_output=True)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode==0:return
    subprocess.run(['git','-c','user.name=london-meta-bot','-c','user.email=actions@users.noreply.github.com','commit','-m',message],cwd=ROOT,check=True,capture_output=True)
    # Another workflow or operator may update main after checkout. Rebase this
    # isolated receipt commit once before retrying; never force-push.
    push=subprocess.run(['git','push','origin','HEAD:main'],cwd=ROOT,text=True,capture_output=True)
    if push.returncode==0:return
    fetch=subprocess.run(['git','fetch','origin','main'],cwd=ROOT,text=True,capture_output=True)
    if fetch.returncode!=0:
        raise RuntimeError('GitHub receipt push failed; fetch failed: '+fetch.stderr[-500:].strip())
    rebase=subprocess.run(['git','rebase','origin/main'],cwd=ROOT,text=True,capture_output=True)
    if rebase.returncode!=0:
        subprocess.run(['git','rebase','--abort'],cwd=ROOT,capture_output=True)
        raise RuntimeError('GitHub receipt push failed; rebase conflict: '+rebase.stderr[-500:].strip())
    retry=subprocess.run(['git','push','origin','HEAD:main'],cwd=ROOT,text=True,capture_output=True)
    if retry.returncode!=0:
        raise RuntimeError('GitHub receipt push failed after one safe rebase retry: '+retry.stderr[-500:].strip())

def main():
    if os.environ.get('META_LIVE_PUBLISH','false').lower()!='true':print('RESULT=BLOCKED_LIVE_SWITCH_OFF');return
    creds,missing=credentials()
    if missing:print('MISSING_CREDENTIALS '+','.join(missing),flush=True)
    from meta_12_daily_schedule import plan
    now=datetime.now(KST);today=now.date().isoformat();state=json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
    due=[];assets=[];changed=False
    for slot in plan(today):
        if slot['slot_id'] in state:continue
        hh,mm=map(int,slot['time_kst'].split(':'));target=now.replace(hour=hh,minute=mm,second=0,microsecond=0);delay=(now-target).total_seconds()
        if delay<0 or delay>POLICY['daily_cadence']['catchup_minutes']*60:continue
        account=next(x for x in POLICY['accounts'] if x['key']==slot['account_key'])
        token,uid=creds.get((slot['platform'],slot['account_key']),('',''))
        if not token:
            print(f"SKIPPED_SLOT={slot['slot_id']} REASON=missing_token",flush=True)
            continue
        try:
            endpoint='https://graph.instagram.com/v25.0/me?fields=user_id,username' if slot['platform']=='instagram' else 'https://graph.threads.net/v1.0/me?fields=id,username'
            me=api(endpoint,token);uid=validated_user_id(slot['platform'],me,slot['expected_handle'],uid)
            source=source_for(slot);post=generate(account,slot['platform'],slot,source)
            row={'status':'ATTEMPT_RESERVED','platform':slot['platform'],'account_key':account['key'],'expected_handle':slot['expected_handle'],'at_kst':now.isoformat(),'content_sha256':hashlib.sha256(post['caption'].encode()).hexdigest()}
            if slot['platform'] in ('instagram','threads'):
                asset=f"demo_assets/meta_12/{slot['slot_id'].replace(':','_')}.png";asset_path=ROOT/asset;make_image(asset_path,account,slot,post);row['image_path']=asset
                row['image_url']=f'https://raw.githubusercontent.com/{REPO}/main/{asset}'
                assets.append(asset)
            row['caption']=post['caption'];state[slot['slot_id']]=row;due.append((slot,token,uid,row));changed=True
        except Exception as e:
            print(f"SKIPPED_SLOT={slot['slot_id']} REASON={str(e)[:100]}",flush=True)
    if changed:
        STATE.parent.mkdir(parents=True,exist_ok=True);STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');commit(assets+[str(STATE.relative_to(ROOT))],'meta: reserve verified 12-target slots and images')
    for slot,token,uid,row in due:
        try:
            if slot['platform']=='instagram':
                base='https://graph.instagram.com/v25.0';container=api(f'{base}/{uid}/media',token,'POST',{'image_url':row['image_url'],'caption':row['caption']});cid=str(container.get('id',''))
                if not cid:raise RuntimeError('Instagram container missing')
                for _ in range(36):
                    status=api(f'{base}/{cid}?fields=status_code',token).get('status_code')
                    if status=='FINISHED':break
                    if status not in ('IN_PROGRESS',):raise RuntimeError('Instagram container processing failed')
                    time.sleep(5)
                else:raise RuntimeError('Instagram media processing timeout')
                result=api(f'{base}/{uid}/media_publish',token,'POST',{'creation_id':cid});pid=str(result.get('id',''))
                verified=api(f'{base}/{pid}?fields=id,permalink,timestamp',token);url=str(verified.get('permalink',''))
            else:
                base='https://graph.threads.net/v1.0';container=api(f'{base}/{uid}/threads',token,'POST',{'media_type':'IMAGE','image_url':row['image_url'],'text':row['caption']});cid=str(container.get('id',''))
                if not cid:raise RuntimeError('Threads container missing')
                time.sleep(5);result=api(f'{base}/{uid}/threads_publish',token,'POST',{'creation_id':cid});pid=str(result.get('id',''))
                verified=api(f'{base}/{pid}?fields=id,permalink',token);url=str(verified.get('permalink',''))
            if not pid or str(verified.get('id',''))!=pid or not url.startswith('https://'):raise RuntimeError('Public permalink verification failed')
            state[slot['slot_id']].update({'status':'PUBLISHED','id':pid,'public_url':url,'published_at_kst':now.isoformat()});print(f"PUBLISHED destination={slot['platform']}:{slot['expected_handle']} url={url}",flush=True)
        except Exception as e:
            state[slot['slot_id']].update({'status':'NEEDS_RECONCILIATION','error':str(e)[:120]});print(f"NEEDS_RECONCILIATION destination={slot['platform']}:{slot['expected_handle']} error={str(e)[:100]}",flush=True)
        STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');changed=True
    if changed:commit([str(STATE.relative_to(ROOT))],'meta: record 12-target publication receipts')
    print(f"RESULT=DISPATCH_FINISHED reserved={len(due)} live_posts_attempted={len(due)}")
if __name__=='__main__':main()
