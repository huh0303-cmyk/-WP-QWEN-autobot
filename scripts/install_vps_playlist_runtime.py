"""Install an encrypted runtime artifact on its intended VPS only."""
import base64, io, json, os, sys, zipfile
from pathlib import Path
import requests
from dotenv import dotenv_values
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
settings=dotenv_values('/etc/korea365/control.env')
token=next((settings[k] for k in ('CONTROL_CENTER_GITHUB_TOKEN','GH_TOKEN','GITHUB_TOKEN','GH_PAT') if settings.get(k)), None)
if not token: raise SystemExit('Existing control GitHub token unavailable')
base='https://api.github.com/repos/huh0303-cmyk/-WP-QWEN-autobot'
headers={'Authorization':'Bearer '+token, 'Accept':'application/vnd.github+json'}
response=requests.get(base+'/actions/runs/'+sys.argv[1]+'/artifacts',headers=headers,timeout=30);response.raise_for_status()
artifact=next(a for a in response.json()['artifacts'] if a['name']=='sealed-vps-runtime')
response=requests.get(artifact['archive_download_url'],headers=headers,timeout=30);response.raise_for_status()
sealed=json.loads(zipfile.ZipFile(io.BytesIO(response.content)).read('sealed-runtime.json'))
private=serialization.load_pem_private_key(Path('/etc/korea365/runtime-transfer.pem').read_bytes(),password=None)
key=private.decrypt(base64.b64decode(sealed['key']),padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
values=json.loads(Fernet(key).decrypt(sealed['data'].encode()))
os.umask(0o077)
out=Path('/etc/korea365/youtube-runtime.json');out.write_text(json.dumps(values));out.chmod(0o600)
print('Installed runtime credentials:', len(values), 'values; none displayed')
