"""Reviewed first public Seoul Journal package. No credentials in source."""
import json,sys
from pathlib import Path
from seoul_journal_presentation import make
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts"/"seoul-journal-release-20261109"
META={
"headline":"이재명 지명\n대장동 공방, 왜?",
"youtube_title":"이재명이 지명한 이용철…왜 대장동 공방에 섰나? #Shorts",
"narration":"이재명 대통령이 지명한 법무부 장관 후보자, 왜 대장동 공방에 섰을까요? 핵심은 이용철 후보자의 과거 경력입니다. 한겨레의 11월 8일 보도에 따르면, 국민의힘은 이 후보자가 유동규 씨의 성남시 시설관리공단 본부장 임용 때 추천위원이었다는 점을 들어 의혹을 제기했습니다. 하지만 이 후보자의 반박은 시점과 업무가 다르다는 겁니다. 추천위원 활동은 2010년이었고, 도시개발공사로 바뀌어 대장동 사업을 한 것은 2014년이라는 설명입니다. 또 유 씨가 도시개발공사에 다시 들어갈 때는 추천위원이 아니었다고 밝혔습니다. 민주당은 정치 공세 대신 사실과 자료로 검증하라고 맞섰습니다. 현재 확인되는 것은 의혹 제기와 당사자의 반박입니다. 의혹 자체가 입증된 사실은 아닙니다. 인사청문회에서는 어떤 자료가 제시될까요? 서울저널입니다.",
"captions":["법무장관 후보 지명 이후\n왜 대장동 공방인가?","쟁점은 이용철 후보자의\n과거 추천위원 경력","국민의힘의 의혹 제기\n당사자는 시점·업무 차이로 반박","2010년 추천위원 활동\n2014년 대장동 사업이라는 설명","재임용 때는 추천위원이\n아니었다는 후보자 반박","민주당: 사실과 자료로 검증","의혹 제기와 반박을 구분\n의혹이 곧 입증은 아닙니다","인사청문회에서\n어떤 자료가 나올까요?"],
"source_url":"https://n.news.naver.com/mnews/article/028/0002831263",
"source_date_kst":"2026-11-08T21:16:09+09:00",
"description":"이재명 대통령의 이용철 법무부 장관 후보 지명 이후 불거진 대장동 관련 공방. 국민의힘의 의혹 제기, 이용철 후보자의 시점·업무 관련 반박, 민주당의 입장을 구분해 정리합니다. 의혹을 입증된 사실로 단정하지 않습니다.\n\n보도 출처: https://n.news.naver.com/mnews/article/028/0002831263\n자료사진: 이재명, 2025-08-25 / The White House, Emily J. Higgins / Public domain. 현재 사건 현장 사진이 아닙니다.\nhttps://commons.wikimedia.org/wiki/File:Lee_Jae-myung_(2025)_(cropped).jpg\n편집: 서울저널 / 음성: AI 내레이션, 1.2배속.\n#서울저널 #정치뉴스 #이재명 #이용철 #Shorts"
}
if __name__=="__main__":
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"package.json").write_text(json.dumps(META,ensure_ascii=False,indent=2),encoding="utf-8")
    make(META,OUT)
