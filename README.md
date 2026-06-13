# 🤖 WordPress AI Auto-Posting Robot Network (-WP-autobot)

GitHub Actions와 최신 LLM 인프라를 결합한 워드프레스 다중 사이트 자동 포스팅 및 영/한 뉴스 네트워크 자동화 솔루션입니다.

모바일 가독성 극대화 매커니즘과 고도화된 SEO 스코어링 시스템이 탑재되어 있습니다.

---

## 📁 Repository Directory Structure

| 파일/폴더명 | 설명 |
| :--- | :--- |
| **`.github/workflows/`** | GitHub Actions 정기 실행 워크플로우 정의 파일 보관 |
| **`autopost_mega.py`** | 23개 프리미엄 사이트 대상 멀티스레딩 메가 자동 포스팅 봇 |
| **`autopost_khealth.py`** | `k-health365.com` 전용 고도화 헬스케어 포스팅 봇 |
| **`newsbot_korea.py`** | `koreanews365.com` 실시간 RSS 수집 기반 한국어 신문 뉴스봇 |
| **`newsbot_seoul.py`** | `theseouljournal.com` 실시간 RSS 수집 기반 영자 신문 뉴스봇 |
| **`sites_config.py`** | 대상 워드프레스 사이트 URL 및 핵심 메타데이터 정의 구성 파일 |
| **`keywords_all.py`** | 23개 사이트 카테고리별 핵심 타겟 SEO 키워드 맵 데이터 |
| **`kw_health.txt` / `_ko.txt`** | 건강 부문 타겟 영문/국문 세부 키워드 시드 자산 |

---

## 🚀 Key Core Features

### 1. High-Performance LLM Architecture
- 기존 인프라를 **Qwen API (qwen-2.5-72b-instruct)** 기반으로 전면 전환하여 대규모 처리 안정성을 확보했습니다.
- 높은 컨텍스트 이해도를 바탕으로 깊이 있는 전문 기사 및 칼럼을 생성합니다.

### 2. Severe Mobile Readability Optimization
- 스마트폰 스크롤 환경에 맞추어 모든 문장을 매우 짧고 호흡이 팽팽하게 끊어치도록 프롬프트를 설계했습니다.
- 출력단에서 모든 문장 단위 사이에 무조건 빈 줄 공백(Blank Line)을 주입하여 가독성을 극대화했습니다.

### 3. Systematic SEO Scoring Engine
- 발행 전 타이틀 길이, 메타 디스크립션 충족도, H2/H3 태그 구조, 1개 이상의 데이터 비교 테이블 포함 여부를 자동 검증합니다.
- 내/외부 링크(Target Blank 속성 포함) 개수 및 이미지 ALT 속성 매칭 상태를 계측하여 품질 점수가 80점 미만일 경우 자동으로 품질 리비전(Regeneration) 알고리즘을 수행합니다.

### 4. Hub-and-Spoke Backlink Network
- 영자 신문(`theseouljournal.com`) 및 뉴스봇 계열에서 생성된 트래픽과 도메인 파워가 메인 자산인 헬스케어 플랫폼(`k-health365.com` 등)으로 자연스럽게 흐르도록 유기적인 앵커 텍스트 아웃바운드 링크 구조를 생성합니다.

---

## 🛠️ Installation & Setup

### 1. 필수 의존성 패키지 설치
```bash
pip install requests requests-toolbelt
