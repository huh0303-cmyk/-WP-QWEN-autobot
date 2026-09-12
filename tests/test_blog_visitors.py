from pathlib import Path
from types import SimpleNamespace
from flask import Flask
from control_center.blog_visitors import install

def test_counter_deduplicates_and_rejects_wrong_sites(tmp_path,monkeypatch):
    app=Flask(__name__);app.config['SECRET_KEY']='test-only'
    monkeypatch.setenv('BLOG_VISITOR_DB',str(tmp_path/'counter.db'))
    install(SimpleNamespace(app=app,__file__=str(Path(__file__).resolve().parents[1]/'control_center/app.py')))
    client=app.test_client();url='/api/blog-visits/kstudy365'
    headers={'Origin':'https://kstudy365.blogspot.com','User-Agent':'Mozilla/5.0'}
    data={'visitor_id':'12345678-1234-1234-1234-123456789abc'}
    assert client.post(url,headers=headers,data=data).json['counted'] is True
    second=client.post(url,headers=headers,data=data)
    assert second.json['counted'] is False
    assert second.json['today']==1 and second.json['total']==1
    assert client.get(url).json['timezone']=='Asia/Seoul'
    assert client.get('/api/blog-visits/unknown').status_code==404
    assert client.post(url,headers={'Origin':'https://wrong.example'},data=data).status_code==403
    bot=client.post(url,headers={**headers,'User-Agent':'Googlebot'},data={'visitor_id':'87654321-1234-1234-1234-123456789abc'})
    assert bot.json['total']==1
