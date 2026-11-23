"""Publish one selected account test, reserve first, and prevent duplicates."""
import json,os,time
from datetime import datetime,timedelta,timezone
from meta_12_publisher import ROOT,POLICY,READINESS,api,make_image,commit
KST=timezone(timedelta(hours=9));REPO='huh0303-cmyk/-WP-QWEN-autobot'
SAMPLE={
 'english_sos1':'ENGLISH SOS connection test. Could I get a coffee, please? | Korean meaning: 커피 한 잔 주시겠어요? #EnglishSOS',
 'japanese_sos1':'JAPANESE SOS connection test. こんにちは = konnichiwa = 안녕하세요. #JapaneseSOS',
 'chinese_sos1':'CHINESE SOS connection test. 你好 = nǐ hǎo = 안녕하세요. #ChineseSOS',
 'korean_sos1':'KOREAN SOS 연결 테스트. 안녕하세요 = annyeonghaseyo = hello. #KoreanSOS',
 'seoul_jisoo1':'서울지수 연결 테스트입니다. 구매 전 용도와 필수 기능을 먼저 확인해요. #서울지수',
 'seoul_journal1':'서울저널 계정 연결 테스트입니다. 실제 뉴스가 아닌 게시 연결 확인용 글입니다. #서울저널'
}
def main():
    platform=os.environ.get('PUBLISH_PLATFORM','').lower();key=os.environ.get('PUBLISH_ACCOUNT','').lower()
    if platform not in POLICY['platforms']:raise SystemExit('BLOCKED=INVALID_PLATFORM')
    account=next((a for a in POLICY['accounts'] if a['key']==key),None)
    if not account:raise SystemExit('BLOCKED=INVALID_ACCOUNT')
    data=json.loads(READINESS.read_text(encoding='utf-8'));row=next(x for x in data['targets'] if x['platform']==platform and x['account_key']==key)
    if row.get('test_public_url') or row.get('test_attempted_at'):
        print('RESULT=ALREADY_TESTED_OR_RESERVED; no duplicate post');return
    prefix=f'META_{platform.upper()}_{key.upper()}';token=os.environ.get(prefix+'_ACCESS_TOKEN','').strip();uid=os.environ.get(prefix+'_USER_ID','').strip()
    if not token or not uid.isdigit():raise SystemExit('BLOCKED=MISSING_TARGET_CREDENTIALS')
    expected=account[platform].lower().lstrip('@');base='https://graph.instagram.com/v25.0' if platform=='instagram' else 'https://graph.threads.net/v1.0'
    me=api(('https://graph.instagram.com/v25.0/me?fields=user_id,username' if platform=='instagram' else 'https://graph.threads.net/v1.0/me?fields=id,username'),token)
    actualid=str(me.get('user_id' if platform=='instagram' else 'id',''));handle=str(me.get('username','')).lower().lstrip('@')
    if actualid!=uid or handle!=expected:raise SystemExit('BLOCKED=IDENTITY_MISMATCH; no post sent')
    now=datetime.now(KST);row.update({'identity_verified':True,'test_status':'ATTEMPT_RESERVED','test_attempted_at_kst':now.isoformat()});data['updated_at_kst']=now.isoformat();READINESS.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');commit([str(READINESS.relative_to(ROOT))],'meta: reserve one destination test before publish')
    caption=SAMPLE[key];slot={'date_kst':now.date().isoformat()}
    if platform=='instagram':
        slot.update({'slot_id':'test:'+platform+':'+key,'account_key':key});post={'image_title':key.replace('_',' ').upper(),'image_subtitle':'PUBLIC CONNECTION TEST'}
        asset=f'demo_assets/meta_12/tests/{platform}_{key}.png';make_image(ROOT/asset,account,slot,post);commit([asset],'meta: add one-account test card')
        image_url=f'https://raw.githubusercontent.com/{REPO}/main/{asset}';container=api(f'{base}/{uid}/media',token,'POST',{'image_url':image_url,'caption':caption});cid=str(container.get('id',''))
        if not cid:raise RuntimeError('Instagram test container missing')
        for _ in range(36):
            status=api(f'{base}/{cid}?fields=status_code',token).get('status_code')
            if status=='FINISHED':break
            if status!='IN_PROGRESS':raise RuntimeError('Instagram test media processing failed')
            time.sleep(5)
        else:raise RuntimeError('Instagram test media processing timeout')
        result=api(f'{base}/{uid}/media_publish',token,'POST',{'creation_id':cid});pid=str(result.get('id',''));verified=api(f'{base}/{pid}?fields=id,permalink',token);url=str(verified.get('permalink',''))
    else:
        container=api(f'{base}/{uid}/threads',token,'POST',{'media_type':'TEXT','text':caption});cid=str(container.get('id',''))
        if not cid:raise RuntimeError('Threads test container missing')
        time.sleep(5);result=api(f'{base}/{uid}/threads_publish',token,'POST',{'creation_id':cid});pid=str(result.get('id',''));verified=api(f'{base}/{pid}?fields=id,permalink',token);url=str(verified.get('permalink',''))
    if not pid or str(verified.get('id',''))!=pid or not url.startswith('https://'):raise RuntimeError('Test post permalink verification failed')
    row.update({'identity_verified':True,'write_scope_verified':True,'test_status':'PUBLISHED','test_public_url':url,'test_published_at_kst':datetime.now(KST).isoformat()});data['updated_at_kst']=datetime.now(KST).isoformat();READINESS.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');commit([str(READINESS.relative_to(ROOT))],'meta: record verified destination test post')
    print(f'RESULT=TEST_PUBLISHED_AND_VERIFIED platform={platform} handle={expected} url={url}')
if __name__=='__main__':main()