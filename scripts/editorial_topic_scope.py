"""Do not turn unrelated global trends into Korean recruitment advice."""
import re
from urllib.parse import urlparse

KOREA_REQUIRED={'jobkoreaglobal.com','jobkorea365.com','jobinkorea365.com','k-visa365.com','k-trip365.com'}
def topic_fits(site_url, keyword):
    host=urlparse(site_url).hostname
    text=str(keyword).casefold()
    if host in KOREA_REQUIRED and not re.search(r'korea|한국|국내|서울|부산|제주|seoul|busan|jeju|\b(?:e-[12789]|d-[248]|f-[246])\b',text):
        return False
    if host=='jobkoreaglobal.com' and re.search(r'marine corps|national guard|해병대|주방위군',text):
        return False
    return True

def stock_query(subject, theme):
    """Map known instructional subjects to concrete illustrative photo searches."""
    text=(str(subject)+' '+str(theme)).casefold()
    if re.search(r'teacher|teaching|교사|교원',text):return 'classroom teacher'
    if re.search(r'professor|faculty|교수',text):return 'university lecture'
    if re.search(r'onboarding|인수인계',text):return 'office meeting'
    if re.search(r'recruit|hiring|job interview|채용|취업|면접',text):return 'job interview'
    if re.search(r'visa|비자',text):return 'passport'
    return str(subject)

def teacher_intent(title):
    text=title.casefold()
    if not re.search(r'teacher|teaching',text):return None
    if re.search(r'first.week|induction|handover|classroom access',text):return 'induction'
    if re.search(r'document|credential|qualification',text):return 'documents'
    if re.search(r'recruit|sponsor|hiring',text):return 'recruitment-and-sponsorship'
    return None
