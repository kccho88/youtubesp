# youtube_summarizer.py

import os
import re
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi
from typing import Optional, Dict, List, Tuple

# Gemini API 클라이언트 초기화
# 환경 변수에서 API 키를 자동으로 로드합니다. (os.environ['GEMINI_API_KEY'])
try:
    client = genai.Client()
except Exception as e:
    print(f"Gemini 클라이언트 초기화 오류: {e}")
    # 실제 운영 시에는 여기서 오류 처리를 해줘야 합니다.

def extract_video_id(url: str) -> Optional[str]:
    """YouTube URL에서 비디오 ID를 추출합니다."""
    # 표준 URL, 단축 URL, 임베드 URL 등에서 ID 추출
    match = re.search(r"(?<=v=)[\w-]+|(?<=youtu\.be\/)[\w-]+", url)
    return match.group(0) if match else None

def get_timestamped_transcript(video_id: str) -> Optional[str]:
    """비디오 ID를 사용하여 타임스탬프가 포함된 자막을 가져옵니다."""
    try:
        # 영어('en') 자막을 기본으로 요청하고, 없으면 생성된 자막(auto-generated)을 시도합니다.
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['ko', 'en']) # 한국어 우선, 없으면 영어
        
        # 스크립트 데이터를 가져와 타임스탬프와 텍스트를 결합
        transcript_data = transcript.fetch()
        
        # HH:MM:SS 포맷으로 변환하는 도우미 함수
        def format_time(seconds):
            minutes, seconds = divmod(int(seconds), 60)
            hours, minutes = divmod(minutes, 60)
            # MM:SS 포맷으로 출력 (2시간 미만 동영상 가정)
            return f"{minutes:02d}:{seconds:02d}"

        # 타임스탬프와 텍스트를 결합하여 Gemini에 전달할 형태로 만듭니다.
        formatted_script = ""
        for entry in transcript_data:
            start_time = format_time(entry['start'])
            text = entry['text'].replace('\n', ' ') # 줄바꿈 제거
            formatted_script += f"[{start_time}] {text}\n"

        return formatted_script

    except Exception as e:
        print(f"자막 추출 오류: {e}")
        return None

def generate_summary(transcript_text: str) -> str:
    """Gemini API를 호출하여 요약을 생성하고 HTML 형식으로 반환합니다."""
    
    # 요청하신 프롬프트 템플릿
    prompt_template = f"""
당신은 전문가 동영상 요약 및 챕터 구분 전문가입니다.
사용자가 제공한 YouTube 동영상 내용(또는 자막/스크립트)을 분석하고, 다음의 형식과 규칙에 따라 **먼저 전체 요약을 진행하고 그다음에 시간 단위별 핵심 요약 및 챕터 정리**를 생성해 주세요.

**입력 데이터:** ---
{transcript_text}
---
**출력 형식:** 반드시 HTML 형식으로만 응답해야 합니다.

### 형식 규칙:
1.  **전체 요약:** 동영상의 주제와 가장 중요한 핵심 내용을 3줄 이내로 간결하게 요약합니다. <p> 태그를 사용하세요.
2.  **시간 단위별 챕터/핵심 요약:** 동영상의 주요 내용이 전환되는 지점(챕터)을 기준으로 `[시작시간-종료시간]` 형식의 **타임스탬프**와 함께 해당 구간의 핵심 내용을 간결하게 설명합니다. 이 타임스탬프는 동영상의 **주요 주제 변화**를 기준으로 잡아야 합니다.
3.  **타임스탬프 형식:** `[MM:SS-MM:SS]`. 초 단위까지 명확히 표시합니다. 타임스탬프는 <a href="#" data-time="SS">타임스탬프</a> 형식으로 랩핑하여, 프론트엔드에서 클릭 시 이동할 수 있도록 준비해 주세요.
4.  전체 요약과 시간 단위별 요약은 <h2> 태그로 구분합니다. 시간 단위별 요약은 <ul>과 <li> 태그를 사용합니다.

---

### 최종 출력 예시 (HTML 형식):

<h2>🎬 동영상 핵심 요약</h2>
<p>이 동영상은 A라는 기술의 기본 원리를 설명하고, 실제 웹 서비스에 적용하는 방법을 단계별로 보여줍니다. 특히, B 함수를 사용하여 성능을 최적화하는 팁을 제공합니다. 개발자들이 A 기술을 빠르게 습득하는 데 도움이 됩니다.</p>

<h2>⏱️ 시간 단위별 챕터/핵심 요약</h2>
<ul>
    <li><a href="#" data-time="0">00:00-00:25</a> <strong>도입:</strong> 동영상의 목표 소개 및 A 기술의 등장 배경 설명</li>
    <li><a href="#" data-time="100">01:40-03:15</a> <strong>개발 환경 설정:</strong> Python과 필요한 라이브러리 설치 및 초기 코드 구조화</li>
</ul>
"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', # 빠르고 비용 효율적인 모델 사용
            contents=prompt_template,
        )
        # Gemini는 정확히 HTML 포맷으로만 응답하도록 지시했으므로, 그대로 반환합니다.
        return response.text
    
    except Exception as e:
        error_message = f"Gemini API 호출 오류가 발생했습니다: {e}"
        print(error_message)
        # HTML 오류 메시지를 반환하여 웹페이지에 표시되도록 합니다.
        return f"<h2>🚨 오류 발생</h2><p>{error_message}</p>"

def summarize_youtube_video(youtube_url: str) -> str:
    """전체 요약 프로세스를 실행하는 메인 함수."""
    video_id = extract_video_id(youtube_url)
    
    if not video_id:
        return "<h2>🚨 오류</h2><p>유효하지 않은 YouTube URL 형식입니다.</p>"

    transcript_text = get_timestamped_transcript(video_id)
    
    if not transcript_text:
        return f"<h2>🚨 오류</h2><p>해당 동영상(ID: {video_id})에서 자막을 찾을 수 없거나 추출할 수 없습니다. 비공개이거나 자막이 없는 동영상일 수 있습니다.</p>"

    # 성공적으로 스크립트를 가져왔다면 Gemini에게 요약을 요청합니다.
    summary_html = generate_summary(transcript_text)
    
    return summary_html

# 디버깅을 위한 간단한 테스트 코드 (실제 배포 시에는 제거)
if __name__ == '__main__':
    test_url = "유효한 유튜브 URL을 여기에 넣으세요 (자막이 있는 동영상)"
    # print(summarize_youtube_video(test_url))
    pass
