"""Build a fresh, private-review Seoul Journal Short about Kim Jong-in's Nov. 9 interview."""
import json, sys
from pathlib import Path
from seoul_journal_presentation import make

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts"/"seoul-journal-kimjongin-remake-20261109"
META={
    "headline":"김종인 발언\n비판 근거는?",
    "youtube_title":"김종인, 이재명 대통령 상황 인식 비판…2028 총선 경고의 근거는? #Shorts",
    "narration":(
        "김종인 전 국민의힘 비상대책위원장이 이재명 대통령의 발언과 국정 운영을 비판했습니다. "
        "YTN 라디오 인터뷰에서 김 전 위원장은 6월 지방선거의 서울 패배를 부동산·세금 정책과 연결했고, "
        "대통령의 주가 관련 발언도 투자자 혼란을 키울 수 있다고 주장했습니다. "
        "또 2028년 총선 준비와 민생 집중을 주문했습니다. "
        "이 대목은 김 전 위원의 평가와 전망입니다. 인용한 보도에는 대통령실이나 민주당의 직접 반론이 담기지 않았고, "
        "이 주장을 별도로 검증한 자료도 제시되지 않았습니다. "
        "김종인 전 위원의 비판에 동의하십니까? 동의 또는 비동의, 댓글로 투표해 주세요."
    ),
    "captions":[
        "김종인, 대통령 발언 비판",
        "쟁점은 상황 인식과 국정 운영",
        "서울 지방선거 패배를\n부동산·세금 정책과 연결",
        "주가 관련 발언도 문제 삼아",
        "2028 총선 준비와\n민생 집중 주문",
        "이 대목은 김 전 위원의 평가",
        "보도에 대통령실·민주당\n직접 반론은 담기지 않아",
        "김종인 비판에 동의?\n동의 vs 비동의\n댓글로 투표"
    ],
    "source_title":"김종인 전 국민의힘 비대위원장 YTN 라디오 인터뷰 (2026-11-09)",
    "source_url":"https://m.ytn.co.kr/news_view.amp.php?param=0101_202611090737480650",
    "source_date_kst":"2026-11-09T07:37:00+09:00",
    "source_note":"YTN 라디오 인터뷰 발언을 소개한다. 정치적 평가는 김종인 전 위원장의 주장으로 표시했다. 이 보도에는 대통령실 또는 민주당의 직접 반론이 포함되지 않는다.",
    "visual_subject":"김종인",
    "display_category":"정치·시사",
    "description":(
        "김종인 전 국민의힘 비상대책위원장이 이재명 대통령의 발언과 국정 운영을 비판하며 "
        "2028년 총선 준비와 민생 집중을 주문했습니다. 영상은 인터뷰에서 나온 평가와 전망을 구분해 전하며, "
        "해당 보도에 대통령실이나 민주당의 직접 반론은 담기지 않았다는 점도 밝혔습니다. "
        "김 전 위원의 비판에 동의하는지 투표로 의견을 남겨 주세요."
    ),
    "title_template_id":"claim_response",
    "title_template_note":"이름 + 발언/쟁점 + 근거 질문",
    "benchmark_refs":[
        "https://www.youtube.com/watch?v=9HUYi7z_R40",
        "https://www.youtube.com/watch?v=wYWdFa1eX3U",
        "https://www.youtube.com/watch?v=iTFLp8jieKU",
        "https://www.youtube.com/watch?v=c6JJOrju8C4",
        "https://www.youtube.com/watch?v=vtkYpDkni-c"
    ],
    "benchmark_note":"개별 500K+ 뉴스 쇼츠의 정보 배열과 후킹 원리만 참고; 문구·영상·로고 복제 없음. 조회수 보장 없음.",
    "poll_vote_enforced":"김종인 전 위원의 비판에 동의하십니까? 동의 또는 비동의, 댓글로 투표해 주세요."
}
if __name__=="__main__":
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"package.json").write_text(json.dumps(META,ensure_ascii=False,indent=2),encoding="utf-8")
    video,audit=make(dict(META),OUT)
    (OUT/"render_result.json").write_text(json.dumps({"video":str(video),"audit":audit},ensure_ascii=False,indent=2),encoding="utf-8")
