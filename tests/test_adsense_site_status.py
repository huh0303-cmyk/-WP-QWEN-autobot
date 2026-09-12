import ast,json
from pathlib import Path

def test_ads_txt_authorized_is_not_site_approval():
    root=Path(__file__).resolve().parents[1]
    tree=ast.parse((root/'control_center/app.py').read_text(encoding='utf-8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='adsense_site_status')
    ns={'json':json,'Path':Path,'__file__':str(root/'control_center/app.py')}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'status','exec'),ns)
    status=ns['adsense_site_status']
    assert status('k-health365.com')['google_approved'] is True
    for domain in ['k-trip365.com','koreamedicaltour.com']:
        assert status(domain)['ads_txt_status']=='authorized'
        assert status(domain)['google_approved'] is False
    assert status('kskin365.com')['adsense_status_label']=='미확인'
