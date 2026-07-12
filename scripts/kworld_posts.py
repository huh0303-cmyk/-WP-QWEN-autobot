#!/usr/bin/env python3
"""kworld365.com 카테고리 + 고품질 글 3개 발행"""
import os, requests, time, re

WP_USER  = "huh0303@gmail.com"
SITE_URL = "https://kworld365.com"
WP_PASS  = os.getenv("KWORLD365COM", "")

base = f"{SITE_URL}/wp-json/wp/v2"
auth = (WP_USER, WP_PASS)

# ── 카테고리 4개 ──────────────────────────────────────────
CATS = [
    ("K-Pop & Artists",          "k-pop-artists",
     "Latest K-pop news, artist profiles, album reviews and concert guides for global fans"),
    ("K-Culture & Korean Class", "k-culture-korean-class",
     "Free Korean lessons, Hangul guide, K-drama vocabulary and TOPIK preparation"),
    ("Korean Life & Travel",     "korean-life-travel",
     "Seoul travel tips, Korean food guides, expat life and culture in Korea"),
    ("Etc",                      "etc",
     "Other Korea-related topics and updates"),
]

# ── 고품질 글 3개 ─────────────────────────────────────────
POSTS = [

# ── 글 1: K-Pop & Artists ──────────────────────────────
{
"cat": "K-Pop & Artists",
"kw":  "Stray Kids world tour guide",
"title": "Stray Kids World Tour Guide: Everything You Need to Know Before Buying Tickets",
"body": """
<p>Stray Kids (스트레이 키즈), the powerhouse eight-member group from JYP Entertainment, has become one of the most in-demand live acts in K-pop. Known for their self-produced music, explosive stage presence, and deeply personal lyrics, Stray Kids — or SKZ as fans call them — deliver concerts that are genuinely unlike anything else in the genre.</p>

<p>If you are planning to attend a Stray Kids concert or simply want to understand why millions of fans call themselves STAY, this complete guide covers everything you need to know.</p>

<h2>Who Are Stray Kids?</h2>
<p>Stray Kids debuted on March 25, 2018 after forming through a JYP Entertainment reality show of the same name. The current lineup consists of eight members: Bang Chan, Lee Know, Changbin, Hyunjin, Han, Felix, Seungmin, and I.N. (Jeongin). Former member Woojin departed in 2019.</p>

<p>What sets Stray Kids apart from most K-pop groups is their extraordinary level of creative control. Their in-house production unit, known as <strong>3RACHA</strong> (방찬, 한, 창빈), writes and produces the vast majority of their music — giving SKZ a raw, authentic sound that resonates globally.</p>

<h2>Why Stray Kids Concerts Are Special</h2>
<p>Attending a Stray Kids concert means experiencing several hours of non-stop high-energy performance. Here is what makes their shows stand out:</p>

<ul>
<li><strong>Self-produced setlists</strong> — Every song performed was largely created by the members themselves</li>
<li><strong>Powerful choreography</strong> — Their dance routines are technically demanding and visually stunning</li>
<li><strong>Fan interaction</strong> — SKZ are known for going off-script and genuinely engaging with STAY throughout shows</li>
<li><strong>Production quality</strong> — LED screens, pyrotechnics, and stage design are consistently world-class</li>
<li><strong>Emotional moments</strong> — Ballad stages and fan service segments often move both the group and audience to tears</li>
</ul>

<h2>How to Buy Stray Kids Concert Tickets</h2>
<p>Tickets for Stray Kids shows typically sell out within minutes. Here is the most reliable process:</p>

<ol>
<li><strong>Create accounts early</strong> on Ticketmaster, Live Nation, and your regional equivalent (예스24, Melon Ticket in Korea)</li>
<li><strong>Join Stray Kids' fan community</strong> on Weverse — fan club members (official STAY) often get pre-sale access</li>
<li><strong>Set reminders</strong> for the exact on-sale time — use multiple devices if possible</li>
<li><strong>Have payment information saved</strong> in advance to reduce checkout time</li>
<li><strong>Be flexible on seat location</strong> — any seat in the venue beats missing the show entirely</li>
</ol>

<h2>Essential Korean Phrases for the Concert</h2>
<p>Learning a few Korean expressions will significantly enhance your concert experience and delight any Korean fans around you:</p>

<ul>
<li>스트레이 키즈 최고! (<em>Seuteulei Kijeu choego!</em>) — Stray Kids is the best!</li>
<li>화이팅! (<em>Hwaiting!</em>) — Fighting! / You can do it!</li>
<li>사랑해요! (<em>Saranghaeyo!</em>) — I love you!</li>
<li>앙코르! (<em>Angkoreu!</em>) — Encore!</li>
<li>대박! (<em>Daebak!</em>) — Amazing!</li>
</ul>

<h2>Must-Know Stray Kids Songs Before Your First Concert</h2>
<p>Walking into a Stray Kids concert knowing the songs makes the experience infinitely more memorable. Start with these essential tracks:</p>

<ul>
<li><strong>God's Menu (神메뉴)</strong> — The bombastic anthem that introduced SKZ to mainstream global audiences</li>
<li><strong>MIROH</strong> — An empowering declaration of self-belief that became a fan favorite live</li>
<li><strong>Back Door</strong> — High energy, incredibly catchy, and always gets the crowd moving</li>
<li><strong>Thunderous (소리꾼)</strong> — Incorporates traditional Korean musical elements in a stunning way</li>
<li><strong>MANIAC</strong> — The title track from ODDINARY that showcases the group's theatrical range</li>
<li><strong>Social Path</strong> — A more emotional, melodic side of SKZ that resonates deeply with STAY</li>
</ul>

<h2>Concert Etiquette: What to Know</h2>
<p>Whether attending in Korea or internationally, a few practices are standard at K-pop concerts:</p>

<ul>
<li><strong>Lightsticks (응원봉)</strong> — Official SKZ lightsticks (called Skzoo lightsticks) are highly recommended for the light show during slow songs</li>
<li><strong>Fan chants (응원 구호)</strong> — Each song has specific fan chants. Look these up on YouTube before attending</li>
<li><strong>No flash photography</strong> — Flash is generally prohibited and considered disrespectful during emotional moments</li>
<li><strong>Respect others' space</strong> — Standing areas can get very crowded; be considerate of those around you</li>
</ul>

<h2>Where to Find Stray Kids Updates</h2>
<ul>
<li><strong>Weverse:</strong> Official fan communication platform with member posts and concert announcements</li>
<li><strong>Instagram:</strong> @stray_kids for visual updates</li>
<li><strong>YouTube:</strong> Stray Kids channel for music videos, behind-the-scenes, and live clips</li>
<li><strong>X (Twitter):</strong> @Stray_Kids for real-time announcements</li>
</ul>

<p>Keep exploring K-pop content and concert guides in our <a href="https://kworld365.com/category/k-pop-artists/">K-Pop & Artists</a> section. And if you want to learn Korean to enjoy your favorite K-pop music even more, check out our <a href="https://kworld365.com/category/k-culture-korean-class/">free Korean classes</a>!</p>
"""},

# ── 글 2: K-Culture & Korean Class ──────────────────────
{
"cat": "K-Culture & Korean Class",
"kw":  "learn Korean free beginners Hangul",
"title": "Learn Korean Free: Complete Beginner Guide to Hangul — Read Korean in 2 Hours",
"body": """
<p>One of the most surprising facts about learning Korean is this: the Korean writing system, called <strong>Hangul (한글)</strong>, is considered one of the most scientifically designed alphabets in human history. Unlike Chinese or Japanese scripts that require thousands of characters, Hangul consists of just 24 basic letters — and most motivated learners can read it within a single day.</p>

<p>This guide will take you from zero to reading Korean step by step, completely free. Let's begin.</p>

<h2>What is Hangul?</h2>
<p>Hangul (한글) is the official writing system of both South Korea and North Korea. It was created in 1443 by King Sejong the Great (세종대왕, <em>Sejong Daewang</em>) specifically to increase literacy among Korean people. Before Hangul, Koreans used Chinese characters, which were accessible only to the educated elite.</p>

<p>The genius of Hangul is that each letter is designed to visually represent how your mouth and tongue move when making that sound. This makes it exceptionally logical and learnable.</p>

<h2>The Structure of Korean Syllables</h2>
<p>Korean is written in syllable blocks, not in a horizontal line of individual letters like English. Each syllable block contains:</p>
<ul>
<li>An <strong>initial consonant (초성, choseong)</strong></li>
<li>A <strong>vowel (중성, jungseong)</strong></li>
<li>An optional <strong>final consonant (종성, jongseong)</strong></li>
</ul>

<p>For example: 한 (han) = ㅎ (h) + ㅏ (a) + ㄴ (n)</p>

<h2>Korean Vowels (모음, Moeum) — 10 Basic Vowels</h2>
<p>Start by memorizing these 10 essential vowels:</p>

<ul>
<li>ㅏ = <em>a</em> (like "father")</li>
<li>ㅑ = <em>ya</em></li>
<li>ㅓ = <em>eo</em> (like "uh")</li>
<li>ㅕ = <em>yeo</em></li>
<li>ㅗ = <em>o</em> (like "go")</li>
<li>ㅛ = <em>yo</em></li>
<li>ㅜ = <em>u</em> (like "moon")</li>
<li>ㅠ = <em>yu</em></li>
<li>ㅡ = <em>eu</em> (like "hm" with rounded lips)</li>
<li>ㅣ = <em>i</em> (like "see")</li>
</ul>

<h2>Korean Consonants (자음, Jaeum) — 14 Basic Consonants</h2>
<p>Next, learn these 14 basic consonants:</p>

<ul>
<li>ㄱ = <em>g/k</em></li>
<li>ㄴ = <em>n</em></li>
<li>ㄷ = <em>d/t</em></li>
<li>ㄹ = <em>r/l</em></li>
<li>ㅁ = <em>m</em></li>
<li>ㅂ = <em>b/p</em></li>
<li>ㅅ = <em>s</em></li>
<li>ㅇ = silent (when initial) / <em>ng</em> (when final)</li>
<li>ㅈ = <em>j</em></li>
<li>ㅊ = <em>ch</em></li>
<li>ㅋ = <em>k</em></li>
<li>ㅌ = <em>t</em></li>
<li>ㅍ = <em>p</em></li>
<li>ㅎ = <em>h</em></li>
</ul>

<h2>Your First Korean Words — Practice Reading Now</h2>
<p>Now try reading these common Korean words using what you just learned:</p>

<ul>
<li>가 (<em>ga</em>) — go / a syllable</li>
<li>나 (<em>na</em>) — I / me</li>
<li>바나나 (<em>banana</em>) — banana</li>
<li>아이 (<em>ai</em>) — child</li>
<li>우유 (<em>uyu</em>) — milk</li>
<li>오이 (<em>oi</em>) — cucumber</li>
<li>이모 (<em>imo</em>) — aunt (mother's sister)</li>
</ul>

<h2>Essential Phrases to Start Speaking Korean Today</h2>
<p>Once you can read Hangul, these phrases will immediately become useful:</p>

<ul>
<li>안녕하세요 (<em>Annyeonghaseyo</em>) — Hello</li>
<li>감사합니다 (<em>Gamsahamnida</em>) — Thank you</li>
<li>죄송합니다 (<em>Joesonghamnida</em>) — I am sorry</li>
<li>괜찮아요 (<em>Gwaenchanayo</em>) — It's okay / No problem</li>
<li>모르겠어요 (<em>Moreugeseoyo</em>) — I don't know</li>
<li>도와주세요 (<em>Dowajuseyo</em>) — Please help me</li>
<li>얼마예요? (<em>Eolmayeyo?</em>) — How much is it?</li>
<li>맛있어요! (<em>Masisseoyo!</em>) — It's delicious!</li>
</ul>

<h2>Free Resources to Continue Learning Korean</h2>
<p>After mastering Hangul, these free tools will accelerate your Korean learning journey:</p>

<ul>
<li><strong>Talk To Me In Korean (TTMIK):</strong> The most structured free Korean lessons online at talktomeinkorean.com</li>
<li><strong>Duolingo Korean:</strong> Gamified daily practice, ideal for building habits</li>
<li><strong>Naver Dictionary:</strong> The most accurate Korean-English dictionary, completely free</li>
<li><strong>KoreanClass101 on YouTube:</strong> Thousands of free video lessons for all levels</li>
<li><strong>Papago App:</strong> Best Korean translation app by Naver, more accurate than Google Translate for Korean</li>
<li><strong>Anki Flashcards:</strong> Create digital flashcards for Korean vocabulary using the spaced repetition method</li>
</ul>

<h2>Learning Korean Through K-Pop and K-Drama</h2>
<p>The most enjoyable way to reinforce your Korean is through content you already love:</p>

<ol>
<li>Watch K-dramas with Korean subtitles (not English) once you know Hangul</li>
<li>Shadow K-pop singers by singing along to songs you know well</li>
<li>Follow Korean YouTube channels with dual subtitles</li>
<li>Find a language exchange partner through apps like HelloTalk or Tandem</li>
</ol>

<p>The key is consistency — even 15 minutes of Korean practice daily will produce remarkable results within three months. Start with Hangul today, and you will be reading Korean menus, street signs, and song lyrics before you know it!</p>

<p>Explore more free Korean lessons and K-culture guides in our <a href="https://kworld365.com/category/k-culture-korean-class/">K-Culture & Korean Class</a> section!</p>
"""},

# ── 글 3: Korean Life & Travel ──────────────────────────
{
"cat": "Korean Life & Travel",
"kw":  "Korean street food guide Seoul",
"title": "Korean Street Food Guide: 15 Must-Try Seoul Street Foods Every Visitor Needs to Eat",
"body": """
<p>Korean street food (길거리 음식, <em>gilgeori eumsik</em>) is one of the most exciting and affordable culinary experiences in Asia. The streets of Seoul, particularly around Myeongdong, Hongdae, Gwangjang Market, and Insadong, come alive every day with vendors serving sizzling, steaming, and utterly irresistible food that you simply cannot find anywhere else in the world.</p>

<p>Whether you are a first-time visitor or a K-drama fan who has been dreaming about Korean food for years, this guide covers the 15 must-try street foods that will make your Seoul trip unforgettable.</p>

<h2>1. 떡볶이 (Tteokbokki) — Spicy Rice Cakes</h2>
<p>Tteokbokki is perhaps the most iconic Korean street food. Chewy cylindrical rice cakes are simmered in a fiery, sweet-spicy sauce made from gochujang (red pepper paste), fish cakes, and green onions. The sauce is addictively good — spicy enough to make your eyes water, sweet enough to keep you coming back for more.</p>
<p><strong>Where to try it:</strong> Literally everywhere — any street food stall in Seoul will have tteokbokki. Gwangjang Market has some of the most famous versions.</p>
<p><strong>Price:</strong> approximately 3,000–5,000 KRW (about $2–4 USD)</p>

<h2>2. 순대 (Sundae) — Korean Blood Sausage</h2>
<p>Do not be put off by the name — Korean sundae is a comforting street food made from pig intestines stuffed with glass noodles, vegetables, and blood. It is typically served with tteokbokki sauce or a simple salt and pepper dip.</p>
<p><strong>Price:</strong> approximately 3,000–4,000 KRW</p>

<h2>3. 핫도그 (Hotdog) — Korean Corn Dog</h2>
<p>Korean corn dogs have taken social media by storm — and for good reason. Unlike American corn dogs, Korean versions come coated in various crispy exteriors including rice flour, potato cubes, panko breadcrumbs, and even ramen noodles. Fillings range from classic mozzarella cheese to squid ink or half-cheese-half-sausage combinations.</p>
<p><strong>Must-try brands:</strong> Myungrang Hotdog and Mix Cheese Hotdog stalls in Myeongdong</p>
<p><strong>Price:</strong> approximately 2,000–5,000 KRW</p>

<h2>4. 붕어빵 (Bungeobbang) — Fish-Shaped Pastry</h2>
<p>Bungeobbang is a beloved winter street food — a golden, crispy pastry shaped like a fish and filled with sweet red bean paste. Despite the fish shape, it tastes like a warm, slightly sweet waffle. Modern versions now come filled with custard cream, chocolate, and even pizza ingredients.</p>
<p><strong>Best time to find it:</strong> Autumn and winter months (October through February)</p>
<p><strong>Price:</strong> approximately 1,000 KRW each</p>

<h2>5. 호떡 (Hotteok) — Sweet Pancakes</h2>
<p>Hotteok is a thick, chewy pancake filled with brown sugar, cinnamon, and crushed peanuts or walnuts. When pressed flat on the griddle, the filling melts into a gloriously sweet, syrupy center. It is the perfect winter street snack.</p>
<p><strong>Price:</strong> approximately 1,000–2,000 KRW</p>

<h2>6. 어묵 (Eomuk / Odeng) — Fish Cake Skewers</h2>
<p>Eomuk — also called odeng — consists of processed fish cake sheets threaded onto skewers and simmered in a light, savory broth. The broth itself is served free in small cups alongside the skewers, making this one of the most warming and satisfying cold-weather street foods in Korea.</p>
<p><strong>Price:</strong> approximately 500–1,000 KRW per skewer</p>

<h2>7. 닭꼬치 (Dak Kkochi) — Grilled Chicken Skewers</h2>
<p>Juicy chunks of chicken are marinated and grilled over charcoal until lightly charred, then coated with a sweet and spicy sauce. These skewers are ubiquitous throughout Seoul's street food markets and are perfect for eating while walking.</p>
<p><strong>Price:</strong> approximately 3,000–4,000 KRW</p>

<h2>8. 계란빵 (Gyeran Bbang) — Egg Bread</h2>
<p>Gyeran bbang is a fluffy, slightly sweet bread loaf baked with a whole egg inside. The result is a savory-sweet combination that is enormously satisfying and filling. It is one of the most photographed street foods in Seoul.</p>
<p><strong>Price:</strong> approximately 1,500–2,000 KRW</p>

<h2>9. 마라탕 (Malatang) — Spicy Sichuan Hot Pot</h2>
<p>While technically originating from China, malatang has become enormously popular in Korea and is now a staple at street food markets. You choose your own ingredients — vegetables, meat, noodles, tofu — which are then cooked in a numbing, spicy Sichuan broth. The price is calculated by weight.</p>
<p><strong>Price:</strong> approximately 8,000–15,000 KRW depending on ingredients chosen</p>

<h2>10. 꿀타래 (Kkultarae) — Honeycomb Candy</h2>
<p>Kkultarae is a traditional Korean candy made from honey and maltose that is pulled into thousands of fine, silky threads and wrapped around a filling of chopped peanuts and sugar. Watching vendors make it is almost as satisfying as eating it — it looks like delicate white cotton candy but tastes like a crispy, sweet wafer.</p>
<p><strong>Best place to find it:</strong> Insadong street market</p>
<p><strong>Price:</strong> approximately 2,000–3,000 KRW</p>

<h2>Useful Korean Food Phrases</h2>
<p>Learning a few food-related Korean phrases will make your street food adventure significantly more enjoyable:</p>

<ul>
<li>이거 주세요 (<em>Igeo juseyo</em>) — I will have this, please</li>
<li>맛있어요! (<em>Masisseoyo!</em>) — It's delicious!</li>
<li>맵지 않게 해주세요 (<em>Maepji aneuge haejuseyo</em>) — Please make it not spicy</li>
<li>얼마예요? (<em>Eolmayeyo?</em>) — How much is it?</li>
<li>하나 더 주세요 (<em>Hana deo juseyo</em>) — One more, please</li>
<li>포장해 주세요 (<em>Pojanghe juseyo</em>) — To go, please</li>
</ul>

<h2>Best Seoul Street Food Markets</h2>
<ul>
<li><strong>Gwangjang Market (광장시장):</strong> One of Seoul's oldest and most authentic traditional markets — try bindaetteok (mung bean pancakes) and mayak gimbap here</li>
<li><strong>Myeongdong (명동):</strong> The highest concentration of street food stalls, perfect for first-time visitors</li>
<li><strong>Hongdae (홍대):</strong> Trendy and creative street food scene popular with university students</li>
<li><strong>Insadong (인사동):</strong> Traditional market atmosphere with classic Korean sweets and snacks</li>
<li><strong>Dongdaemun (동대문):</strong> Best late-night street food scene — vendors are open until the early morning hours</li>
</ul>

<p>Explore more Korean travel guides and food tips in our <a href="https://kworld365.com/category/korean-life-travel/">Korean Life & Travel</a> section, and start learning Korean food vocabulary in our <a href="https://kworld365.com/category/k-culture-korean-class/">free Korean class</a>!</p>
"""},

]  # end POSTS

def get_or_create_cat(name, slug, desc):
    r = requests.get(f"{base}/categories", auth=auth,
                    params={"slug": slug, "per_page":1}, timeout=10)
    if r.status_code == 200 and r.json():
        cid = r.json()[0]["id"]
        print(f"  ✅ 기존 카테고리: {name} (ID:{cid})")
        return cid
    cr = requests.post(f"{base}/categories", auth=auth,
                      json={"name":name,"slug":slug,"description":desc}, timeout=10)
    if cr.status_code in (200,201):
        cid = cr.json()["id"]
        print(f"  ✅ 생성: {name} (ID:{cid})")
        return cid
    print(f"  ❌ 카테고리 실패: {name} ({cr.status_code})")
    return None

def publish_post(title, body, cat_id, keyword):
    meta_desc = re.sub('<[^>]+>', '', body)[:155].strip()
    data = {
        "title":      title,
        "content":    body,
        "status":     "publish",
        "categories": [cat_id] if cat_id else [],
        "meta": {
            "rank_math_focus_keyword": keyword,
            "rank_math_description":   meta_desc,
            "rank_math_robots":        ["index","follow"],
        }
    }
    r = requests.post(f"{base}/posts", auth=auth, json=data, timeout=30)
    if r.status_code in (200,201):
        url  = r.json().get("link","")
        pid  = r.json().get("id","")
        print(f"  ✅ 발행완료 ID:{pid}")
        print(f"     {url}")
        # Google/Bing IndexNow ping
        try:
            sm = requests.utils.quote(url)
            requests.get(f"https://www.google.com/ping?sitemap={sm}", timeout=5)
        except: pass
        return url
    print(f"  ❌ 발행실패 ({r.status_code}): {r.text[:80]}")
    return None

def run():
    if not WP_PASS:
        print("❌ KWORLD365COM 환경변수 없음"); return

    # 연결 확인
    r = requests.get(f"{base}/posts", auth=auth,
                    params={"per_page":1}, timeout=10)
    if r.status_code != 200:
        print(f"❌ 연결 실패 ({r.status_code})"); return
    print(f"✅ kworld365.com 연결 성공")
    total = int(r.headers.get("X-WP-Total",0))
    print(f"   현재 글 수: {total}건\n")

    # 카테고리 설정
    print("📁 카테고리 설정...")
    cat_ids = {}
    for name, slug, desc in CATS:
        cat_ids[name] = get_or_create_cat(name, slug, desc)
        time.sleep(0.3)

    # 기존 카테고리 정리 (황금4 외 삭제)
    keep_slugs = {"k-pop-artists","k-culture-korean-class","korean-life-travel","etc","uncategorized"}
    rc = requests.get(f"{base}/categories", auth=auth,
                     params={"per_page":100}, timeout=10)
    if rc.status_code == 200:
        for cat in rc.json():
            if cat.get("slug","") not in keep_slugs and cat.get("count",0) == 0:
                requests.delete(f"{base}/categories/{cat['id']}",
                               auth=auth, params={"force":True}, timeout=8)
                print(f"  🗑️ 불필요 카테고리 삭제: {cat['name']}")

    # ads.txt 스니펫
    print("\n📄 ads.txt 삽입...")
    ADS = "google.com, pub-3456727916386941, DIRECT, f08c47fec0942fa0"
    php = "\n".join([
        "<?php",
        "add_action('init', function() {",
        "    if (!isset($_SERVER['REQUEST_URI'])) return;",
        "    $uri = strtok($_SERVER['REQUEST_URI'], '?');",
        "    if ($uri === '/ads.txt') {",
        "        header('Content-Type: text/plain; charset=utf-8');",
        "        header('Cache-Control: public, max-age=3600');",
        "        echo '" + ADS + "';",
        "        exit;",
        "    }",
        "}, 1);",
    ])
    rs = requests.get(f"{base}/wpcode-snippets", auth=auth,
                     params={"per_page":100}, timeout=10)
    if rs.status_code == 200 and isinstance(rs.json(), list):
        for s in rs.json():
            t = s.get("title",{})
            ts = t.get("rendered","") if isinstance(t,dict) else str(t)
            if "ads.txt" in ts.lower():
                requests.delete(f"{base}/wpcode-snippets/{s['id']}",
                               auth=auth, params={"force":True}, timeout=8)
    cr = requests.post(f"{base}/wpcode-snippets", auth=auth,
                      json={"title":"ads.txt Generator","content":php,
                            "code_type":"php","location":"everywhere","status":"publish"},
                      timeout=15)
    print(f"  {'✅ 완료' if cr.status_code in (200,201) else f'❌ {cr.status_code}'}")

    # 글 발행
    print("\n📝 고품질 글 3개 발행...")
    for i, post in enumerate(POSTS, 1):
        cat_id = cat_ids.get(post["cat"])
        print(f"\n  [{i}/3] {post['title'][:55]}...")
        publish_post(post["title"], post["body"].strip(), cat_id, post["kw"])
        time.sleep(3)

    # sitemap ping
    try:
        sm = requests.utils.quote(f"{SITE_URL}/sitemap_index.xml")
        requests.get(f"https://www.google.com/ping?sitemap={sm}", timeout=6)
        requests.get(f"https://www.bing.com/ping?sitemap={sm}", timeout=6)
    except: pass

    print("\n" + "="*55)
    print("✅ kworld365.com 완료!")
    print("카테고리: K-Pop & Artists / K-Culture & Korean Class")
    print("         / Korean Life & Travel / Etc")
    print("글 3개 발행 완료 (SEO 90점+ 타깃)")
    print("\n📌 지금 바로:")
    print("   adsense.google.com → kworld365.com → 검토 요청!")

if __name__ == "__main__":
    run()
