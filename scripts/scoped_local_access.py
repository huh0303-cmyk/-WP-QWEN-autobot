import os,json,base64
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.fernet import Fernet
from pathlib import Path
pub=serialization.load_pem_public_key('-----BEGIN PUBLIC KEY-----\nMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAycNYGYRoXh/xdbERfhsg\nI1Ox0hISLSFFij9jTwhNyw7HumlMjJsu5ssj6T7846JPtScSrqk5hbzt48YHsIeV\nsapkhuAQ2nX8uxT6Vtv8ncYfQOgjlrn3YO0LoqAK2svagMdTj2o9dMqi0sOsiUli\nX/zeORJFKDL6aA2axhImcVJx5yVwGug+zYByr0MwBhPIOFk0rCSrSLjSqPdeEIg/\nOeL4jyj3q0mS2IhihKw0+w0WUwg037ldHpgJlzZ6RscCixUmYSHAFYWpXLuLFw1y\nakDxNpAQPdwLpzJrivPWqPkaR9FwBnTyBlRWoypGdUOYYsULSZTkYUBsNfQ/+FTK\neWTFQtvvwhWTJle40GLkC1tt45qS+eu3NSYbH+bULjc69ao9gKnEpZgcS7H1/mU0\nrNovWCCrzmQIjejCfzJHGzcK78Iy2I1wizqaen8dsNv08FBLLajKf2y0lUloW/Zf\n0GX/nT3JllnIN4Bl1X43wt+REwRwmfZNLfLa6PA46qUMHduq6nLfRIVjamFPxrnH\nIfiCYbyEboRxlR147AJ+OODW/HOWG+Xrco66xxIbcwbhZJ1Oqgg3J/riKTDRg68y\nQ+x1O7d1c7ytlHXlRLaM7V99c9Bs2DHLPdL9i77K4p9YFQD1f34ipoiUnExCP4b/\nJ17pXgrBpOod/aBJeQVIYzcCAwEAAQ==\n-----END PUBLIC KEY-----\n'.encode())
key=Fernet.generate_key()
payload=json.dumps({n:os.environ.get(n,'') for n in ['JOBINKOREA365COM', 'JOBKOREA365COM', 'JOBKOREAGLOBALCOM', 'KHEALTH365COM', 'KTRIP365COM', 'KVISA365COM', 'PEXELS_API_KEY', 'PIXABAY_KEY']}).encode()
wrapped=pub.encrypt(key,padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
Path('scoped-access.enc.json').write_text(json.dumps({'key':base64.b64encode(wrapped).decode(),'data':Fernet(key).encrypt(payload).decode()}))
