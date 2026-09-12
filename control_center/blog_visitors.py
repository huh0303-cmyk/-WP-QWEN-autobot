"""Approximate daily browser visits, counted from installation onward."""
import hashlib
import hmac
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import jsonify, request

BOT_RE = re.compile(r'bot|crawl|spider|slurp|bingpreview|facebookexternalhit|pingdom|uptime|ahrefs|semrush|mj12', re.I)
KST = timezone(timedelta(hours=9))
VISITOR_RE = re.compile(r'^[A-Za-z0-9_-]{20,80}$')

def _today():
    return datetime.now(KST).strftime('%Y-%m-%d')

@contextmanager
def _connect(path):
    conn=sqlite3.connect(path,timeout=15)
    conn.row_factory=sqlite3.Row
    try:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS daily(site_key TEXT,date TEXT,count INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(site_key,date));
            CREATE TABLE IF NOT EXISTS total(site_key TEXT PRIMARY KEY,count INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS seen(site_key TEXT,date TEXT,visitor TEXT,PRIMARY KEY(site_key,date,visitor));
        ''')
        with conn:
            yield conn
    finally:
        conn.close()

def install(module):
    app=module.app
    root=Path(module.__file__).resolve().parents[1]
    path=os.environ.get('BLOG_VISITOR_DB',str(root/'data/blog-visitor-counts.sqlite3'))
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    profiles=json.loads((root/'config/content_engine_profiles.json').read_text())['profiles']
    origins={p['site_key']:p['blogspot']['url'].rstrip('/') for p in profiles}

    def respond(payload,code=200):
        response=jsonify(payload)
        response.status_code=code
        origin=request.headers.get('Origin','')
        if origin in origins.values():
            response.headers['Access-Control-Allow-Origin']=origin
            response.headers['Vary']='Origin'
            response.headers['Access-Control-Allow-Methods']='GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers']='Content-Type'
        response.headers['Cache-Control']='no-store'
        return response

    @app.route('/api/blog-visits/<site_key>',methods=['GET','POST','OPTIONS'])
    def blog_visits(site_key):
        if site_key not in origins:
            return respond({'error':'unknown site'},404)
        if request.method=='OPTIONS':
            return respond({})
        counted=False
        today=_today()
        with _connect(path) as conn:
            if request.method=='POST':
                if request.headers.get('Origin','') != origins[site_key]:
                    return respond({'error':'invalid origin'},403)
                ua=request.headers.get('User-Agent','')
                visitor=request.form.get('visitor_id','')
                if not VISITOR_RE.fullmatch(visitor):
                    return respond({'error':'visitor identifier required'},400)
                if ua and not BOT_RE.search(ua):
                    key=str(app.config['SECRET_KEY']).encode()
                    digest=hmac.new(key,f'{site_key}:{today}:{visitor}'.encode(),hashlib.sha256).hexdigest()
                    conn.execute('BEGIN IMMEDIATE')
                    counted=conn.execute('INSERT OR IGNORE INTO seen VALUES(?,?,?)',(site_key,today,digest)).rowcount==1
                    if counted:
                        conn.execute('INSERT INTO daily VALUES(?,?,1) ON CONFLICT(site_key,date) DO UPDATE SET count=count+1',(site_key,today))
                        conn.execute('INSERT INTO total VALUES(?,1) ON CONFLICT(site_key) DO UPDATE SET count=count+1',(site_key,))
                    cutoff=(datetime.now(KST)-timedelta(days=8)).date().isoformat()
                    conn.execute('DELETE FROM seen WHERE date<?',(cutoff,))
            day=conn.execute('SELECT count FROM daily WHERE site_key=? AND date=?',(site_key,today)).fetchone()
            total=conn.execute('SELECT count FROM total WHERE site_key=?',(site_key,)).fetchone()
        return respond({'today':day['count'] if day else 0,'total':total['count'] if total else 0,
                        'counted':counted,'date':today,'timezone':'Asia/Seoul','metric':'daily_browser_visits_since_install'})
