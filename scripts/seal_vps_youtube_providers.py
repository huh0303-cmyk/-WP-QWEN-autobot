"""Seal only the three approved provider credentials for the owner's VPS."""
import base64,json,os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.primitives.asymmetric import padding

root=Path(__file__).resolve().parents[1]
names=('OPENAI_API_KEY','ELEVENLABS_API_KEY','REPLICATE_API_TOKEN')
values={name:os.environ.get(name,'') for name in names}
if not all(values.values()):
    raise RuntimeError('Required YouTube provider credential missing; nothing exported')
recipient=serialization.load_pem_public_key((root/'config/vps-provider-recipient.pem').read_bytes())
key=Fernet.generate_key()
sealed=recipient.encrypt(key,padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
output=root/'artifacts/youtube-providers.sealed.json'
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps({'key':base64.b64encode(sealed).decode(),'payload':Fernet(key).encrypt(json.dumps(values).encode()).decode()}))
print('Encrypted provider bundle prepared for the configured VPS recipient. No plaintext artifact created.')
