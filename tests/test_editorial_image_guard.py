from io import BytesIO
from PIL import Image
from scripts.editorial_image_guard import fingerprint,same_photo

def data(kind,fmt):
    im=Image.new('RGB',(120,80));p=im.load()
    for y in range(80):
        for x in range(120):p[x,y]=((x*2,y*3,(x+y)%255) if kind==1 else (y*3,255-x*2,(x*y)%255))
    out=BytesIO();im.save(out,format=fmt);return out.getvalue()

def test_reencoded_same_photo_blocked():
    assert same_photo(fingerprint(data(1,'PNG')),fingerprint(data(1,'JPEG')))

def test_different_image_allowed():
    assert not same_photo(fingerprint(data(1,'PNG')),fingerprint(data(2,'PNG')))
