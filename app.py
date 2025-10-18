# app.py

from flask import Flask, render_template, request, jsonify
from youtube_summarizer import summarize_youtube_video
import os

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # AJAX 요청으로 URL을 받습니다.
        youtube_url = request.form.get('url')
        if not youtube_url:
            return jsonify({'summary_html': "<h2>🚨 오류</h2><p>YouTube URL을 입력해 주세요.</p>"}), 400
        
        # 핵심 요약 함수 호출
        summary_html = summarize_youtube_video(youtube_url)
        
        # 생성된 HTML을 프론트엔드로 반환
        return jsonify({'summary_html': summary_html})

    # GET 요청 시, index.html 템플릿을 렌더링
    return render_template('index.html')

if __name__ == '__main__':
    # 보안을 위해 실제 환경에서는 디버그 모드를 끄고 HTTPS를 사용하세요.
    # 포트 5000에서 실행됩니다.
    app.run(debug=True, host='0.0.0.0', port=5000)
