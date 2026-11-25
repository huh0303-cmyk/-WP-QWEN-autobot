# 한국어 필수 표현 100 — Threads 발행 절차 (@korean_sos1)

목록: /home/claude/korean100/expressions.json  (index 0 = 1번, [한국어, 로마자, 영어])
이미 발행됨: 1/100 안녕하세요 (2026-11-25). 이후 번호는 프로필의 최신 "N/100" 글에서 이어서 센다.

## 1회 실행 = 카드 3개 발행
1. Chrome 탭에서 https://www.threads.com/@korean_sos1 열고, 최신 글 중 "한국어 필수 표현 N/100" 중 가장 큰 N을 찾는다. 다음 번호 = N+1. (N=100이면 종료, 아무것도 올리지 않음)
2. 번호 N+1, N+2, N+3 각각 (100 초과 금지):
   a. 새 탭에서 Unsplash 검색(https://unsplash.com/s/photos/<영문 키워드>)으로 표현 주제에 맞는 "실제 한국" 무료 사진을 고른다.
      - Unsplash+ (자물쇠/유료) 사진 금지, 간판·글자에 부적절한 문구가 보이는 사진 금지, 사람 얼굴이 크게 나온 사진은 피한다.
      - 최근 10개 카드와 같은 사진 재사용 금지. 사진 ID(photo-xxxx)와 촬영자 이름(알 수 있으면 확인)을 기록.
      - 주제 키워드 예: 인사/예절=gyeongbokgung, 식당=korean-food-table, 쇼핑=seoul-market, 길찾기=seoul-subway, 감정=han-river, 날씨=seoul-autumn
   b. javascript로 카드 HTML을 만든다 (card.js의 card() 함수 사용; 뷰포트 전체가 카드). 이미지 로드(naturalWidth>0) 확인 후 screenshot(scale 1)으로 imageId를 얻는다.
      - 카드에는 발음(로마자)이 "🔊 따라 읽기 ×5" 줄로 5번 반복 표시된다(card.js의 .p). 긴 표현은 pf(글자 크기)를 18~20으로 줄여 푸터와 겹치지 않게 한다.
      - 긴 한국어는 fs(글자 크기)를 줄여 한 줄 또는 두 줄에 맞춘다. 커서가 안 보여야 함(cursor:none).
   c. Threads 탭에서 작성창 열고 본문 입력: "한국어 필수 표현 N/100 🇰🇷 "<한국어>" = <로마자> = <영어>. <한 줄 팁> #KoreanSOS #LearnKorean #TOPIK #한국어"
   d. find로 hidden file-input ref를 찾아 chrome_upload_image(imageId, ref)로 카드 첨부 → 미리보기 확인 → 게시.
   e. 프로필에서 새 글(이미지 포함)이 보이는지 확인. 실패하면 중복 게시 금지, 같은 번호를 다시 올리기 전에 프로필 확인.
3. 글 사이 최소 2~3분 간격. 쓰고 난 임시 탭은 모두 닫는다.
4. 로그인이 풀렸거나 Threads가 오류/제한을 보이면 중단하고 결과를 보고(비밀번호 입력 금지).
