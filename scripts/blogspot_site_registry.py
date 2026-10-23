"""Registry of the 33 Blogspot (Blogger) properties, mirroring site_registry.py's
shape for scripts/audit_gsc_post_index.py so the GSC audit logic can be reused
as-is. Each row is (public_url, blogger_blog_id, lifecycle).

public_url is the blog's live public address (custom domain when one is mapped,
otherwise the *.blogspot.com address) - this is also the value passed to Google
Search Console's property matching, so it must match whatever property was
verified there. blogger_blog_id is the internal Blogger blog ID, used to read
the public post feed without needing OAuth.

Generated 2026-09-09 from config/automation_rooms.json's blogger rooms; keep in
sync if a Blogspot site's custom-domain mapping or blog ID changes.
"""

BLOGSPOT_SITES = [
    ("https://k-health365.blogspot.com", "8294304371132383961", "active"),  # blogger_khealth365
    ("https://koreamedicaltour365.blogspot.com", "270775542645307723", "active"),  # blogger_koreamedicaltour365
    ("https://koreainvest365.blogspot.com", "4890361213499831195", "active"),  # blogger_koreainvest365
    ("https://ki-korea.blogspot.com", "2490110552890683078", "active"),  # blogger_kikorea
    ("https://koreainsurance365.blogspot.com", "8888982369193041814", "active"),  # blogger_koreainsurance365
    ("https://kfinance365.blogspot.com", "1687098888954822322", "active"),  # blogger_kfinance365
    ("https://koreataxnlaw.blogspot.com", "8654603097966481527", "active"),  # blogger_koreataxnlaw
    ("https://koreacrypto365.blogspot.com", "3406327845659558883", "active"),  # blogger_koreacrypto365
    ("https://krealestate365.blogspot.com", "6980941479069687285", "active"),  # blogger_krealestate365
    ("https://ktech365.blogspot.com", "6878877615041749185", "active"),  # blogger_ktech365
    ("https://skin.k-health365.com", "7354545101201355815", "active"),  # blogger_kskin365 (custom domain)
    ("https://oliveyoungkorea.blogspot.com", "473506254375374117", "active"),  # blogger_oliveyoungkorea
    ("https://kworld365seoul.blogspot.com", "5061870975921599649", "active"),  # blogger_kworld365
    ("https://k-trip365.blogspot.com", "5345010194652095946", "active"),  # blogger_ktrip365
    ("https://k-visa365.blogspot.com", "8661782623130728248", "active"),  # blogger_kvisa365
    ("https://koreawedding365.blogspot.com", "2674139059432343378", "active"),  # blogger_koreawedding365
    ("https://kstudy365.blogspot.com", "1529526209955625690", "active"),  # blogger_kstudy365
    ("https://studyinkorea365.blogspot.com", "2107448954473357757", "active"),  # blogger_studyinkorea365
    ("https://kieca-korea.blogspot.com", "3364333636330259319", "active"),  # blogger_kieca
    ("https://ksa-korea.blogspot.com", "4432103895513840706", "active"),  # blogger_ksa
    ("https://sis-korea.blogspot.com", "6436826795706658249", "active"),  # blogger_sis
    ("https://jobkorea365.blogspot.com", "9124051754121584517", "active"),  # blogger_jobkorea365
    ("https://jobinkorea365.blogspot.com", "3560791242887862780", "active"),  # blogger_jobinkorea365
    ("https://jobkoreaglobal.blogspot.com", "5264943720375052759", "active"),  # blogger_jobkoreaglobal
    ("https://korea365guide.blogspot.com", "242870255610398021", "active"),  # blogger_korea365
    ("https://koreanews365daily.blogspot.com", "7521251102691129954", "active"),  # blogger_koreanews365
    ("https://theseouljournal.blogspot.com", "6946912888985634794", "active"),  # blogger_theseouljournal
    ("https://glow.k-health365.com", "4456888951628869767", "active"),  # blogger_kwellness_lab (custom domain)
    ("https://k-health365-edu.blogspot.com", "3205814823967421343", "active"),  # blogger_kmedical_job_center
    ("https://korea-life-support365.blogspot.com", "2531035487222435079", "active"),  # blogger_korea_life_support365
    ("https://koreamedicaltour1.blogspot.com", "2234527810530371008", "active"),  # blogger_koreamedicaltour1
    ("https://kworld365.blogspot.com", "3683978748331752523", "active"),  # blogger_kworld365_kpop
    ("https://seoulintlschoolguide.blogspot.com", "8077962392257357260", "active"),  # blogger_seoul_intl_school_guide
]

ACTIVE_BLOGSPOT_SITES = [row for row in BLOGSPOT_SITES if row[2] != "retired"]
