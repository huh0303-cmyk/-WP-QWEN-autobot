"""Seal the selected runtime credentials to the existing owner's VPS public key."""
import base64, json, os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
keys=json.loads(Path('deploy/vps/runtime-secret-names.json').read_text())
values={key:os.environ[key] for key in keys if os.environ.get(key)}
public=serialization.load_pem_public_key(Path('deploy/vps/runtime-transfer.pub').read_bytes())
key=Fernet.generate_key()
sealed={'key':base64.b64encode(public.encrypt(key,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))).decode(),
        'data':Fernet(key).encrypt(json.dumps(values).encode()).decode()}
Path('sealed-runtime.json').write_text(json.dumps(sealed))
print('Encrypted runtime package created; no plaintext artifact written')
