import streamlit as st
import requests
import fitz
import io
from PIL import Image
import base64
from matplotlib import font_manager as fm

# FastAPI 서버 설정
API_URL = "http://localhost:8000"

def get_korean_font():
    font_candidates = ["NanumGothic", "Malgun Gothic", "AppleGothic", "Droid Sans Fallback"]
    for font_name in font_candidates:
        font_path = fm.findSystemFonts(fontpaths=None, fontext='ttf')
        for path in font_path:
            if font_name in path:
                return path
    return None

def convert_pdf_page_to_image(pdf_bytes, page_num):
    """PDF 페이지를 이미지로 변환"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def main():
    st.set_page_config(layout="wide", page_title="발표하는 모델 : 오인용")
    
    # 한글 폰트 설정
    font_path = get_korean_font()
    if font_path:
        st.markdown(f"""
            <style>
                .stApp {{
                    font-family: 'NanumGothic', sans-serif;
                }}
                .page-container {{
                    border: 1px solid #ddd;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 10px;
                    background-color: white;
                }}
                .page-title {{
                    font-size: 1.5em;
                    font-weight: bold;
                    margin-bottom: 15px;
                    color: #333;
                    border-bottom: 2px solid #eee;
                    padding-bottom: 10px;
                }}
                .script-container {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin-top: 15px;
                }}
                .audio-container {{
                    background-color: #e9ecef;
                    padding: 10px;
                    border-radius: 5px;
                    margin-top: 10px;
                }}
            </style>
        """, unsafe_allow_html=True)

    st.title("발표하는 모델 : 오인용")

    # 세션 상태 초기화
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'pdf_file' not in st.session_state:
        st.session_state.pdf_file = None
    if 'full_document' not in st.session_state:
        st.session_state.full_document = ""
    if 'scripts' not in st.session_state:
        st.session_state.scripts = []
    if 'tts_audios' not in st.session_state:
        st.session_state.tts_audios = []
    if 'total_pages' not in st.session_state:
        st.session_state.total_pages = 0
    if 'pdf_bytes' not in st.session_state:
        st.session_state.pdf_bytes = None
    if 'presentation_completed' not in st.session_state:
        st.session_state.presentation_completed = False
    if 'team_name' not in st.session_state:
        st.session_state.team_name = ""
    if 'project_name' not in st.session_state:
        st.session_state.project_name = ""
    if 'members' not in st.session_state:
        st.session_state.members = ""
    if 'keywords' not in st.session_state:
        st.session_state.keywords = []

    # 페이지 1
    if st.session_state.current_page == 1:
        st.header("1. PDF 파일 업로드 및 정보 입력")

        st.session_state.team_name = st.text_input("팀명", value=st.session_state.team_name)
        st.session_state.project_name = st.text_input("프로젝트명", value=st.session_state.project_name)
        st.session_state.members = st.text_input("구성원", value=st.session_state.members)

        keywords_input = st.text_input("강조할 키워드 (쉼표로 구분)", value=", ".join(st.session_state.keywords))
        st.session_state.keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

        uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type=['pdf'])
        if uploaded_file:
            st.session_state.pdf_file = uploaded_file
            st.session_state.pdf_bytes = uploaded_file.read()
            doc = fitz.open(stream=st.session_state.pdf_bytes, filetype="pdf")
            st.session_state.total_pages = len(doc)
            st.success(f"PDF 업로드 완료 (총 {st.session_state.total_pages}페이지)")

        st.session_state.full_document = st.text_area("전체 문서 요약을 입력하세요", height=200)

        if all([st.session_state.team_name, st.session_state.project_name, st.session_state.members,
                st.session_state.pdf_file, st.session_state.full_document, st.session_state.keywords]):
            if st.button("다음 단계로 이동"):
                st.session_state.current_page = 2
                st.rerun()
        else:
            st.info("모든 항목을 입력해야 다음 단계로 이동할 수 있습니다.")

    # 페이지 2: 스크립트 및 음성 자동 생성
    elif st.session_state.current_page == 2:
        st.header("2. 전체 스크립트 생성 및 수정")

        # 👉 자동 스크립트/음성 생성 (초기 진입 시 1회만)
        if not st.session_state.scripts:
            try:
                with st.spinner("스크립트 생성 중..."):
                    files = {"file": ("document.pdf", st.session_state.pdf_bytes, "application/pdf")}
                    data = {"full_document": st.session_state.full_document}
                    response = requests.post(f"{API_URL}/generate-script", files=files, data=data)

                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.scripts = result.get("slides", [])

                        audio_res = requests.post(f"{API_URL}/generate-audio", json={
                            "scripts": {str(i): s for i, s in enumerate(st.session_state.scripts)},
                            "keywords": st.session_state.keywords
                        })
                        if audio_res.status_code == 200:
                            st.session_state.tts_audios = audio_res.json()
                            st.success("전체 스크립트와 음성이 생성되었습니다!")
                        else:
                            st.error(f"TTS 생성 오류 (Status {audio_res.status_code}): {audio_res.text}")
                    else:
                        st.error(f"API 오류: {response.text}")
            except Exception as e:
                st.error(f"오류 발생: {str(e)}")

        # ✅ 페이지별 스크립트 & 오디오 표시
        if st.session_state.scripts:
            for page_num in range(st.session_state.total_pages):
                with st.container():
                    st.markdown(f"""
                        <div class="page-container">
                            <div class="page-title">슬라이드 {page_num + 1}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    img = convert_pdf_page_to_image(st.session_state.pdf_bytes, page_num)
                    st.image(img, use_container_width=True)

                    st.markdown("""<div class="script-container"><h4>발표 스크립트</h4></div>""", unsafe_allow_html=True)
                    current_script = st.session_state.scripts[page_num]
                    edited_script = st.text_area(
                        "스크립트 수정",
                        value=current_script,
                        height=150,
                        key=f"script_{page_num}"
                    )
                    if edited_script != current_script:
                        st.session_state.scripts[page_num] = edited_script
                        st.success("스크립트가 수정되었습니다!")

                    # 오디오 출력
                    if "tts_audios" in st.session_state:
                        audio_data = st.session_state.tts_audios
                        audio_b64 = None
                        if isinstance(audio_data, dict):
                            audio_b64 = audio_data.get(str(page_num))
                        elif isinstance(audio_data, list) and len(audio_data) > page_num:
                            audio_b64 = audio_data[page_num]
                        if audio_b64:
                            audio_bytes = base64.b64decode(audio_b64)
                            st.markdown("""<div class="audio-container"></div>""", unsafe_allow_html=True)
                            st.audio(audio_bytes, format="audio/wav")

                    if page_num == st.session_state.total_pages - 1:
                        if not st.session_state.presentation_completed:
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("챗봇과 Q&A"):
                                    response = requests.post(f"{API_URL}/presentation/complete", data={"full_document": st.session_state.full_document})
                                    if response.status_code == 200:
                                        st.session_state.presentation_completed = True
                                        st.success("프레젠테이션이 완료되었습니다!")
                            with col2:
                                if st.button("📦 프레젠테이션 자료 다운로드"):
                                    try:
                                        with st.spinner("파일 생성 중..."):
                                            files = {"file": ("presentation.pdf", st.session_state.pdf_bytes, "application/pdf")}
                                            data = {"wav_dir": "../data/audio"}
                                            response = requests.post(f"{API_URL}/export-presentation", files=files, data=data)
                                            if response.status_code == 200:
                                                st.download_button(
                                                    label="📥 다운로드 (ZIP)",
                                                    data=response.content,
                                                    file_name="presentation_bundle.zip",
                                                    mime="application/zip"
                                                )
                                            else:
                                                st.error(f"API 오류: {response.text}")
                                    except Exception as e:
                                        st.error(f"다운로드 실패: {str(e)}")

            # 🔁 음성 재생성
            if st.button("🔁 수정된 스크립트로 음성 다시 생성"):
                try:
                    with st.spinner("음성 재생성 중..."):
                        new_audio_res = requests.post(f"{API_URL}/generate-audio", json={
                            "scripts": {str(i): s for i, s in enumerate(st.session_state.scripts)},
                            "keywords": st.session_state.keywords
                        })
                        if new_audio_res.status_code == 200:
                            st.session_state.tts_audios = new_audio_res.json()
                            st.success("수정된 스크립트 기반으로 음성이 다시 생성되었습니다.")
                            st.rerun()
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")

    def show_chat_interface():
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        if st.session_state.presentation_completed:
            st.markdown("""<div class="chat-container"><h3>질문이 있으신가요?</h3></div>""", unsafe_allow_html=True)
            for chat in st.session_state.chat_history:
                st.markdown(f"**🙋 사용자:** {chat['question']}")
                st.markdown(f"**🤖 오인용:** {chat['answer']}")

            user_question = st.chat_input("질문을 입력하세요")
            if user_question:
                try:
                    response = requests.post(f"{API_URL}/chat", json={"question": user_question, "session_id": "streamlit_session"})
                    if response.status_code == 200:
                        answer = response.json()["answer"]
                        st.session_state.chat_history.append({"question": user_question, "answer": answer})
                        st.rerun()
                    else:
                        st.error("답변 생성 중 오류가 발생했습니다.")
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")

    if st.session_state.presentation_completed:
        show_chat_interface()

if __name__ == "__main__":
    main()