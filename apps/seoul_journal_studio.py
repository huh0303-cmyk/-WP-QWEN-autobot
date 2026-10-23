#!/usr/bin/env python3
# Seoul Journal Shorts Studio: separate UI over the existing London Project pipeline.
import os, sys, json, subprocess, time
from pathlib import Path
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import seoul_journal_shorts_pipeline as p
OUT=ROOT/"artifacts"/"seoul-journal-studio"; OUT.mkdir(parents=True,exist_ok=True)
st.set_page_config(page_title="서울저널 쇼츠 제작실",page_icon="🎬",layout="wide")
st.title("서울저널 쇼츠 제작실")
st.caption("런던프로젝트 제작 엔진 재사용 · 업로드는 명시적 확인 후 비공개만")
st.warning("AI 대본·음성 생성에는 API 비용이 발생할 수 있습니다. 출처와 사실관계를 검토하세요.")
if "logs" not in st.session_state: st.session_state.logs=[]
if "article" not in st.session_state: st.session_state.article={}
if "pkg" not in st.session_state: st.session_state.pkg={}
if "video" not in st.session_state: st.session_state.video=""
if "stage" not in st.session_state: st.session_state.stage="준비"
def log(s):
 st.session_state.logs.append(time.strftime("%H:%M:%S")+" "+str(s)); st.session_state.logs=st.session_state.logs[-100:]
with st.sidebar:
 st.subheader("환경 변수 확인")
 for k in ["OPENAI_API_KEY","ELEVENLABS_API_KEY","SEOUL_JOURNAL_VOICE_ID","YOUTUBE_OAUTH_CLIENT_ID","YOUTUBE_OAUTH_CLIENT_SECRET","SEOUL_JOURNAL_YOUTUBE_OAUTH_REFRESH_TOKEN","SEOUL_JOURNAL_YOUTUBE_CHANNEL_ID"]:
  st.write(("🟢 " if os.getenv(k) else "🔴 ")+k)
 st.caption("키/토큰은 화면에 입력하지 말고 서버 환경변수에만 저장하세요.")
 st.metric("현재 단계",st.session_state.stage)
t1,t2,t3=st.tabs(["① 기사·대본","② 음성·영상","③ 비공개 업로드"])
with t1:
 url=st.text_input("네이버 뉴스 기사 URL",value=st.session_state.article.get("url",""),placeholder="https://n.news.naver.com/...")
 c1,c2=st.columns(2)
 if c1.button("기사 내용 가져오기",use_container_width=True):
  try:
   title,body,img=p.extract(url.strip()); st.session_state.article={"url":url.strip(),"title":title,"body":body,"image":img}; st.session_state.pkg={}; st.session_state.video=""; st.session_state.stage="기사 확인"; log("기사 본문 수집: "+title); st.success("본문 수집 완료. 아래 내용을 확인하세요.")
  except Exception as e: st.session_state.stage="오류"; log("기사 수집 실패: "+str(e)); st.error(str(e))
 if c2.button("정치면 기사 후보 선택",use_container_width=True):
  try:
   chosen,hint,method=p.choose_naver_article(); st.info("후보 URL을 확인한 뒤 기사 내용 가져오기를 누르세요. 이는 조회수 순위 인증이 아닙니다."); st.code(chosen)
  except Exception as e: st.error(str(e)); log("후보 선택 실패: "+str(e))
 if st.session_state.article.get("body"):
  st.markdown("**"+st.session_state.article["title"]+"**")
  with st.expander("기사 본문 확인"): st.write(st.session_state.article["body"][:12000])
  if st.button("쇼츠 대본 생성",type="primary"):
   try:
    pkg=p.draft(st.session_state.article["title"],st.session_state.article["body"])
    pkg["source_title"]=st.session_state.article["title"]; pkg["source_url"]=st.session_state.article["url"]
    pkg["narration"]=pkg["narration"].rstrip()+"\n\n서울저널이 알려드립니다. 여러분은 어떻게 생각하십니까? 1번 찬성, 2번 반대, 3번 더 지켜봐야 한다. 댓글로 번호를 남겨주세요."
    st.session_state.pkg=pkg; st.session_state.stage="대본 준비 완료"
    (OUT/"package.json").write_text(json.dumps(pkg,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"narration.txt").write_text(pkg["narration"],encoding="utf-8"); log("대본 생성 완료"); st.success("대본 생성 완료. 사실관계·표현을 검토하세요.")
   except Exception as e: st.session_state.stage="오류"; log("대본 생성 실패: "+str(e)); st.error(str(e))
 if st.session_state.pkg:
  pkg=st.session_state.pkg
  title=st.text_input("유튜브 제목",value=pkg.get("youtube_title",""),key="edit_title")
  narration=st.text_area("내레이션 수정",value=pkg.get("narration",""),height=250,key="edit_narration")
  desc=st.text_area("설명 수정",value=pkg.get("description",""),height=100,key="edit_desc")
  if st.button("수정 내용 저장"):
   pkg.update({"youtube_title":title,"narration":narration,"description":desc}); st.session_state.pkg=pkg
   (OUT/"package.json").write_text(json.dumps(pkg,ensure_ascii=False,indent=2),encoding="utf-8"); (OUT/"narration.txt").write_text(narration,encoding="utf-8"); log("대본 수정 저장"); st.success("저장했습니다.")
with t2:
 if not st.session_state.pkg: st.info("먼저 기사·대본 탭에서 대본을 생성하세요.")
 else:
  st.caption("세로형 영상 · 음성 속도 1.2배. 자동 자막 타이밍은 추정치이므로 반드시 검수하세요.")
  if st.button("음성·자막·영상 만들기",type="primary"):
   try:
    pkg=st.session_state.pkg; st.session_state.stage="영상 제작 중"
    with st.spinner("음성 생성과 렌더링 중…"):
     audio=p.tts(pkg["narration"]); photo=p.fetch_photo(st.session_state.article.get("image",""))
     base=p.render(pkg.get("headline",pkg.get("youtube_title","서울저널 정치뉴스")),photo,audio)
     import re
     sents=[x.strip() for x in re.split(r'(?<=[.!?。！？])\s*|\n+',pkg["narration"]) if x.strip()] or [pkg["narration"]]
     duration=max(1,sum(map(len,sents))/5.5/1.2); total=sum(map(len,sents)); cur=0; rows=[]
     def stamp(t):
      ms=int((t-int(t))*1000); return f"{int(t//3600):02}:{int(t//60)%60:02}:{int(t)%60:02},{ms:03}"
     for i,s in enumerate(sents,1):
      end=cur+duration*len(s)/total; rows.append(f"{i}\n{stamp(cur)} --> {stamp(end)}\n{s}\n"); cur=end
     srt=OUT/"captions.srt"; srt.write_text("\n".join(rows),encoding="utf-8")
     video=OUT/"seoul-journal-captioned.mp4"; ffmpeg=os.getenv("FFMPEG_BINARY","ffmpeg")
     cmd=[ffmpeg,"-y","-i",str(base),"-vf",f"subtitles={srt.as_posix()}:force_style='FontName=Noto Sans CJK KR,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Alignment=2,MarginV=180'","-c:v","libx264","-preset","veryfast","-c:a","copy","-movflags","+faststart",str(video)]
     rr=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
     if rr.returncode: raise RuntimeError("자막 렌더링 실패. FFmpeg libass/fonts 설치 확인: "+rr.stderr[-700:])
     if not video.exists() or video.stat().st_size<100000: raise RuntimeError("영상 파일 검증 실패")
    st.session_state.video=str(video); st.session_state.stage="영상 미리보기 준비 완료"; log("영상 렌더링 완료"); st.success("영상 제작 완료. 미리보기를 확인하세요.")
   except Exception as e: st.session_state.stage="오류"; log("영상 제작 실패: "+str(e)); st.error(str(e))
  if st.session_state.video and Path(st.session_state.video).exists():
   st.video(st.session_state.video)
   with open(st.session_state.video,"rb") as f: st.download_button("MP4 다운로드",f,file_name="seoul-journal-short.mp4",mime="video/mp4")
with t3:
 st.warning("업로드는 채널 ID를 검증한 뒤 비공개로만 진행합니다. 공개 발행은 구현하지 않았습니다.")
 if not st.session_state.video or not Path(st.session_state.video).exists(): st.info("먼저 영상을 만들고 미리보기를 확인하세요.")
 else:
  st.video(st.session_state.video)
  ok=st.checkbox("기사 출처·대본·자막·영상 확인 완료. 비공개 업로드에 동의합니다.")
  if st.button("유튜브 비공개 업로드",type="primary",disabled=not ok):
   try:
    st.session_state.stage="채널 확인·업로드 중"
    receipt=p.upload_private(Path(st.session_state.video),st.session_state.pkg,st.session_state.article["url"])
    receipt["response_received_at"]=time.strftime("%Y-%m-%d %H:%M:%S")
    (OUT/"upload_receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    st.session_state.stage="비공개 업로드 API 응답 확인"; log("업로드 응답 수신: "+receipt.get("video_id","")); st.success("업로드 API 응답을 받았습니다."); st.link_button("YouTube Studio에서 확인",receipt["url"]); st.json(receipt)
   except Exception as e: st.session_state.stage="오류"; log("업로드 실패/중단: "+str(e)); st.error(str(e))
with st.expander("실행 로그"):
 st.code("\n".join(st.session_state.logs) if st.session_state.logs else "아직 실행 기록이 없습니다.")
 st.caption("로그는 현재 브라우저 세션에만 보관됩니다. 중앙 영구 로그/대기열은 후속 연결 대상입니다.")
