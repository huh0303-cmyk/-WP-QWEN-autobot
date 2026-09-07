"""Audit latest three posts per WP/Blogger site; repair existing IDs only."""
import json, os, sys, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from automation_hub.repetition_guard import repetition_issues, history_prompt, clean_opening, opening, plain
from automation_hub.editorial_language_policy import title_cliches, body_cliches
from openai_text import openai_generate_text
from audit_repair_all_blogger_posts import access_token
OUT = ROOT / 'artifacts/recent-editorial-repair.json'


def decode(raw):
    return json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip()))


def propose(post, history):
    soup = BeautifulSoup(clean_opening(post['title'], post['content_html']), 'html.parser')
    lead = next((p for p in soup.find_all('p') if len(plain(str(p))) >= 50), None)
    headings = [h for h in soup.find_all(['h2', 'h3']) if not h.find_parent(class_=re.compile('related|author|faq'))]
    source = {'title':post['title'], 'body':plain(post['content_html'])[:22000], 'headings':[plain(str(h)) for h in headings]}
    for attempt in range(3):
        raw = openai_generate_text(history_prompt(history) + '\nEdit this published article using ONLY facts already present. Preserve language. Return JSON {"title":str,"opening":str,"headings":[str]}. Each heading must describe its original section, in the same order and count. No invented statistics, novelty, claims or personal experience. Opening must summarize this article specifically. SOURCE: ' + json.dumps(source, ensure_ascii=False), temperature=.6, max_retries=1)
        edit = decode(raw)
        if len(edit.get('headings', [])) != len(headings) or not 15 <= len(edit.get('title', '')) <= 180 or len(edit.get('opening', '')) < 50: continue
        if title_cliches(edit['title']) or body_cliches(edit['opening']): continue
        if repetition_issues(edit['title'], '<p>' + edit['opening'] + '</p>', history): continue
        verdict = decode(openai_generate_text('Verify an edit against the original article. Every factual claim in the new title/opening/headings must be supported by the original; each heading must match its original section and language. Reject vague keyword-swapped prose. Return JSON {"ok":true/false,"reason":str}. ORIGINAL: ' + json.dumps(source, ensure_ascii=False) + '\nEDIT: ' + json.dumps(edit, ensure_ascii=False), temperature=0, max_retries=1))
        if verdict.get('ok') is not True: continue
        if lead: lead.clear(); lead.append(edit['opening'])
        for h, text in zip(headings, edit['headings']): h.clear(); h.append(text)
        return edit['title'], str(soup)
    raise RuntimeError('Editorial rewrite failed factuality/repetition checks')


def audit_site(site):
    result = {'site_id':site['site_id'], 'url':site['url'], 'posts':[]}
    try:
        wp = site['platform'] == 'wordpress'
        if wp:
            auth = (os.environ.get('WP_USER', ''), os.environ.get(site['secret_name'], ''))
            endpoint = site['url'].rstrip('/') + '/wp-json/wp/v2/posts'
            resp = requests.get(endpoint, auth=auth, params={'per_page':50,'status':'publish','orderby':'date','order':'desc'}, timeout=35)
        else:
            auth = None
            endpoint = 'https://www.googleapis.com/blogger/v3/blogs/' + str(site['destination_id']) + '/posts'
            resp = requests.get(endpoint, headers={'Authorization':'Bearer ' + access_token()}, params={'maxResults':50,'status':'live','fetchBodies':'true'}, timeout=35)
        resp.raise_for_status()
        raw = resp.json() if wp else resp.json().get('items', [])
        posts = [{'id':p['id'], 'title':p['title']['rendered'] if wp else p['title'], 'content_html':p['content']['rendered'] if wp else p.get('content',''), 'url':p.get('link') if wp else p.get('url'), 'original':p} for p in raw]
        for post in posts[:3]:
            history = [p for p in posts if p['id'] != post['id']]
            issues = repetition_issues(post['title'], post['content_html'], history)
            if title_cliches(post['title']): issues.append('TITLE_CLICHE')
            cleaned = clean_opening(post['title'], post['content_html'])
            echo = plain(cleaned) != plain(post['content_html'])
            if echo: issues.append('HEADLINE_ECHO_IN_BODY')
            record = {'id':post['id'], 'url':post['url'], 'old_title':post['title'], 'issues':issues, 'status':'clean'}
            result['posts'].append(record)
            if not issues: continue
            record['status'] = 'needs_repair'
            if os.environ.get('APPLY_CHANGES') != 'true': continue
            record['backup'] = post['original']
            title, body = propose(post, history) if any(i != 'HEADLINE_ECHO_IN_BODY' for i in issues) else (post['title'], cleaned)
            backup_path = OUT.parent / ('backup-' + site['site_id'] + '-' + str(post['id']) + '.json')
            backup_path.write_text(json.dumps(post['original'], ensure_ascii=False), encoding='utf-8')
            target = endpoint + '/' + str(post['id'])
            # Re-read before writing; never overwrite a concurrent editorial edit.
            headers = {} if wp else {'Authorization':'Bearer ' + access_token()}
            current = requests.get(target, auth=auth, headers=headers, timeout=35); current.raise_for_status()
            version_field = 'modified_gmt' if wp else 'updated'
            if current.json().get(version_field) != post['original'].get(version_field): raise RuntimeError('Concurrent edit detected; retry audit')
            payload = {'title':title,'content':body}
            if wp: payload['excerpt'] = opening(body)
            saved = requests.request('POST' if wp else 'PATCH', target, auth=auth, headers=headers, json=payload, timeout=45)
            saved.raise_for_status()
            check = requests.get(target, auth=auth, headers=headers, timeout=35); check.raise_for_status()
            verified = check.json()
            actual = verified['title']['rendered'] if wp else verified['title']
            if plain(actual) != plain(title): raise RuntimeError('Saved title mismatch')
            public = requests.get(post['url'], timeout=35); public.raise_for_status()
            if plain(title).casefold() not in plain(public.text).casefold(): raise RuntimeError('Public page still has old title; cache verification pending')
            post.update(title=title, content_html=body)
            record.update(status='repaired_public_verified', new_title=title)
    except Exception as exc:
        result['error'] = str(exc)
    return result


def main():
    sites = json.loads((ROOT/'config/automation_hub_sites.json').read_text(encoding='utf-8'))['sites']
    sites = [s for s in sites if s.get('enabled',True) and s['platform'] in {'wordpress','blogger'}]
    OUT.parent.mkdir(exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for item in pool.map(audit_site, sites):
            results.append(item)
            OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'site_id':item['site_id'],'statuses':[p['status'] for p in item['posts']], 'error':item.get('error')}, ensure_ascii=False), flush=True)
    return int(any(x.get('error') for x in results))

if __name__ == '__main__': raise SystemExit(main())
