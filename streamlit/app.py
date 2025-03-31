import streamlit as st
import requests
import fitz
from PIL import Image
import base64
from matplotlib import font_manager as fm

API_URL = "http://localhost:8000"

# 사용할 GCP TTS 목소리 목록
VOICE_OPTIONS = {
    "♀️ 여성 모델": "WOMAN",
    "♂️ 남성 모델": "MAN",
}

def get_korean_font():
    font_candidates = ["NanumGothic", "Malgun Gothic", "AppleGothic", "Droid Sans Fallback"]
    for font_name in font_candidates:
        font_path = fm.findSystemFonts(fontpaths=None, fontext='ttf')
        for path in font_path:
            if font_name in path:
                return path
    return None

def convert_pdf_page_to_image(pdf_bytes, page_num):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def initialize_session_state():
    defaults = {
        "app_page": "home",
        "current_page": 1,
        "current_slide": 0,
        "presentation_slide": 0,
        "pdf_file": None,
        "pdf_bytes": None,
        "full_document": "",
        "scripts": [],
        "tts_audios": [],
        "total_pages": 0,
        "presentation_completed": False,
        "keywords": [],
        "chat_history": [],
        "selected_voice": "ko-KR-Wavenet-E",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def render_home_page():
    st.title("Welcome to 발표하는 모델 : 오인용")
    st.markdown("""
    ### 📝 가이드라인
    - 발표를 원하는 발표자료(**PDF 파일**)를 넣어주세요.  
    - 발표 자료에는 없지만 발표 대본에 들어갈 프로젝트 스토리를 작성해주세요.
    - 프로젝트 스토리는 **5문단**으로 작성하는 것을 권장합니다.  
    - 발표 중 대본에서 강조하고 싶은 단어를 **쉼표(,)** 로 나누어 입력해주세요.  
    - 발표자료에는 발표 순서를 보여주기 위해 존재하는 **아무 내용이 없는 파티션 페이지는 넣지 말아주세요.**  
    - 대본 생성 시 시간이 발표 자료의 길이에 따라 몇 분 가량 걸릴 수 있습니다.  
    """, unsafe_allow_html=True)

    st.divider()
    if st.button("📢 발표하러 가기"):
        st.session_state.app_page = "presentation"
        st.session_state.current_page = 1
        st.session_state.current_slide = 0
        st.rerun()

def render_presentation_workflow():
    font_path = get_korean_font()
    if font_path:
        st.markdown(f"""
            <style>
                .stApp {{ font-family: 'NanumGothic', sans-serif; }}
                .page-container {{ border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 10px; background-color: white; }}
                .page-title {{ font-size: 1.5em; font-weight: bold; margin-bottom: 15px; color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                .script-container {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 15px; }}
                .audio-container {{ background-color: #e9ecef; padding: 10px; border-radius: 5px; margin-top: 10px; }}
            </style>
        """, unsafe_allow_html=True)

    st.title("발표하는 모델 : 오인용")

    if st.session_state.current_page == 1:
        st.header("1. PDF 파일 업로드 및 정보 입력")

        st.session_state.selected_voice = st.selectbox("TTS 목소리 선택", options=list(VOICE_OPTIONS.values()),
                                                       format_func=lambda x: [k for k, v in VOICE_OPTIONS.items() if v == x][0])

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

        if all([st.session_state.pdf_file, st.session_state.full_document, st.session_state.keywords]):
            if st.button("다음 단계로 이동"):
                st.session_state.current_page = 2
                st.rerun()
        else:
            st.info("모든 항목을 입력해야 다음 단계로 이동할 수 있습니다.")

    elif st.session_state.current_page == 2:
        st.header("2. 전체 스크립트 생성 및 수정")
        st.markdown("<script>window.scrollTo(0, 0);</script>", unsafe_allow_html=True)

        if not st.session_state.scripts:
            with st.spinner("스크립트 생성 중..."):
                try:
                    files = {"file": ("document.pdf", st.session_state.pdf_bytes, "application/pdf")}
                    data = {"full_document": st.session_state.full_document}
                    response = requests.post(f"{API_URL}/generate-script", files=files, data=data)
                    if response.status_code == 200:
                        st.session_state.scripts = response.json() 
                        
                        requests.post(f"{API_URL}/qa/enable", data={"full_document": st.session_state.full_document})

                        gender = st.session_state.selected_voice

                        audio_res = requests.post(f"{API_URL}/generate-audio", json={
                            "scripts": {str(i): s if isinstance(s, str) else s.get("script", "") for i, s in enumerate(st.session_state.scripts)},
                            "keywords": st.session_state.keywords,
                            "gender": gender  # 명시적으로 전달
                        })
                        if audio_res.status_code == 200:
                            st.session_state.tts_audios = audio_res.json()
                            st.success("전체 스크립트와 음성이 생성되었습니다!")
                        else:
                            st.error(f"TTS 생성 오류: {audio_res.text}")
                    else:
                        st.error(f"API 오류: {response.text}")
                except Exception as e:
                    st.error(f"스크립트 생성 실패: {str(e)}")

        if st.session_state.scripts:
            page_num = st.session_state.current_slide
            st.markdown(f"<div class='page-container'><div class='page-title'>슬라이드 {page_num + 1}</div></div>", unsafe_allow_html=True)
            st.image(convert_pdf_page_to_image(st.session_state.pdf_bytes, page_num), use_container_width=True)

            current_script = st.session_state.scripts[page_num]
            if isinstance(current_script, dict):
                current_script = current_script.get("script", "")

            st.markdown("<div class='script-container'><h4>발표 스크립트</h4></div>", unsafe_allow_html=True)
            edited_script = st.text_area("스크립트 수정", value=current_script, height=150, key=f"script_{page_num}")
            if edited_script != current_script:
                st.session_state.scripts[page_num] = edited_script
                st.success("스크립트가 수정되었습니다!")

            audio_b64 = st.session_state.tts_audios.get(str(page_num)) if isinstance(st.session_state.tts_audios, dict) else None
            if audio_b64:
                st.audio(base64.b64decode(audio_b64), format="audio/wav")

            col1, col2, col3 = st.columns([1.5, 4, 1.5])
            with col1:
                if page_num > 0 and st.button("이전 슬라이드 ⬅"):
                    st.session_state.current_slide -= 1
                    st.rerun()
            with col2:
                st.markdown(f"<div style='text-align:center;font-weight:bold;'>슬라이드 {page_num + 1} / {st.session_state.total_pages}</div>", unsafe_allow_html=True)
            with col3:
                if page_num < st.session_state.total_pages - 1 and st.button("다음 슬라이드 ➡"):
                    st.session_state.current_slide += 1
                    st.rerun()

            if page_num == st.session_state.total_pages - 1:
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    if st.button("🔁 수정된 스크립트로 음성 다시 생성"):
                        try:
                            with st.spinner("음성 재생성 중..."):
                                response = requests.post(f"{API_URL}/generate-audio", json={
                                    "scripts": {str(i): s if isinstance(s, str) else s.get("script", "") for i, s in enumerate(st.session_state.scripts)},
                                    "keywords": st.session_state.keywords,
                                    "gender": st.session_state.selected_voice
                                })
                                if response.status_code == 200:
                                    st.session_state.tts_audios = response.json()
                                    st.success("수정된 음성이 생성되었습니다.")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"오류 발생: {str(e)}")
                with col2:
                    if st.button("📦 프레젠테이션 자료 다운로드"):
                        try:
                            with st.spinner("파일 생성 중..."):
                                files = {"file": ("presentation.pdf", st.session_state.pdf_bytes, "application/pdf")}
                                data = {"wav_dir": "../data/audio"}
                                response = requests.post(f"{API_URL}/export-presentation", files=files, data=data)
                                if response.status_code == 200:
                                    st.download_button("📥 다운로드 (ZIP)", data=response.content, file_name="presentation_bundle.zip", mime="application/zip")
                                else:
                                    st.error(f"API 오류: {response.text}")
                        except Exception as e:
                            st.error(f"다운로드 실패: {str(e)}")
                with col3:
                    if st.button("🎤 발표 시작하기"):
                        st.session_state.app_page = "presentation_view"
                        st.session_state.presentation_slide = 0
                        st.rerun()

def render_presentation_mode():
    st.title("🎤 발표 모드")
    page_num = st.session_state.presentation_slide

    st.markdown(f"<div class='page-container'><div class='page-title'>슬라이드 {page_num + 1}</div></div>", unsafe_allow_html=True)
    st.image(convert_pdf_page_to_image(st.session_state.pdf_bytes, page_num), use_container_width=True)

    audio_b64 = st.session_state.tts_audios.get(str(page_num)) if isinstance(st.session_state.tts_audios, dict) else None
    if audio_b64:
        st.audio(base64.b64decode(audio_b64), format="audio/wav")

    col1, col2, col3 = st.columns([1.5, 4, 1.5])
    with col1:
        if page_num > 0 and st.button("이전 슬라이드 ⬅"):
            st.session_state.presentation_slide -= 1
            st.rerun()
    with col2:
        st.markdown(f"<div style='text-align:center;font-weight:bold;'>슬라이드 {page_num + 1} / {st.session_state.total_pages}</div>", unsafe_allow_html=True)
    with col3:
        if page_num < st.session_state.total_pages - 1 and st.button("다음 슬라이드 ➡"):
            st.session_state.presentation_slide += 1
            st.rerun()

def show_chat_interface():
    if st.session_state.scripts:
        with st.sidebar:
            st.markdown("<h3>🤖 질문이 있으신가요?</h3>", unsafe_allow_html=True)
            for chat in st.session_state.chat_history:
                st.markdown(f"**🙋 사용자:** {chat['question']}")
                st.markdown(f"**🤖 오인용:** {chat['answer']}")
            user_question = st.chat_input("질문을 입력하세요")
            if user_question:
                try:
                    response = requests.post(f"{API_URL}/chat", json={"question": user_question, "session_id": "streamlit_session"})
                    if response.status_code == 200:
                        st.session_state.chat_history.append({"question": user_question, "answer": response.json()["answer"]})
                        st.rerun()
                    else:
                        st.error("답변 생성 중 오류가 발생했습니다.")
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")

def main():
    initialize_session_state()
    if st.session_state.app_page == "presentation":
        render_presentation_workflow()
        show_chat_interface()
    elif st.session_state.app_page == "presentation_view":
        render_presentation_mode()
    else:
        render_home_page()

if __name__ == "__main__":
    main()