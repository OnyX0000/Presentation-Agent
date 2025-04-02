import streamlit as st
import requests
import fitz
from PIL import Image
import base64
from matplotlib import font_manager as fm
import os

API_URL = "http://localhost:8000"

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

def styled_container():
    st.markdown("""
        <style>
            .stApp {
                font-family: 'NanumGothic', sans-serif;
                background-color: rgba(247, 249, 251, 0.8);
                background-blend-mode: lighten;
            }
            .page-container {
                border: 2px solid #dee2e6;
                padding: 20px;
                margin: 30px 0;
                border-radius: 15px;
                background-color: white;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            }
            .page-title {
                font-size: 1.8em;
                font-weight: bold;
                margin-bottom: 20px;
                color: #2c3e50;
                border-bottom: 2px solid #ced4da;
                padding-bottom: 12px;
            }
            .script-container {
                background-color: #f1f3f5;
                padding: 15px;
                border-radius: 10px;
                margin-top: 15px;
            }
            .audio-container {
                background-color: #e9ecef;
                padding: 10px;
                border-radius: 10px;
                margin-top: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

def set_background(image_path):
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    background_style = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center;
    }}
    </style>
    """
    st.markdown(background_style, unsafe_allow_html=True)

def show_chat_interface():
    if st.session_state.app_page == "presentation" and st.session_state.current_page != 1:
        with st.sidebar:
            image_path = "assets/image4.png"  # 또는 방금 업로드한 파일 경로 사용
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode()

            st.markdown(f"""
                <div style="text-align: left; margin-bottom: 1.5rem;">
                    <img src="data:image/png;base64,{image_base64}" style="width: 60px; margin-bottom: 0.5rem;">
                    <div style="font-size: 1.4rem; font-weight: 700;">💬 AI 오인용</div>
                    <div style="font-size: 0.85rem; color: #adb5bd;">PPT에 관련 질문을 해주세요!</div>
                </div>
                <hr style="margin-top: 1rem; margin-bottom: 1rem;">
            """, unsafe_allow_html=True)

            # 이전 질문-답변 출력
            for chat in st.session_state.chat_history:
                st.markdown(f"**🙋 사용자:** {chat['question']}")
                st.markdown(f"**🤖 챗봇:** {chat['answer']}")

            # 질문 입력
            user_question = st.chat_input("질문을 입력하세요")
            if user_question:
                try:
                    response = requests.post(
                        f"{API_URL}/chat",
                        json={"question": user_question, "session_id": "streamlit_session"}
                    )
                    if response.status_code == 200:
                        st.session_state.chat_history.append({
                            "question": user_question,
                            "answer": response.json()["answer"]
                        })
                        st.rerun()
                    else:
                        st.error("답변 생성 중 오류가 발생했습니다.")
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")

def render_home_page():
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 10px;'>
        <img src='data:image/png;base64,{}' width='100'>
        <h1 style='margin: 0; font-size: 50px;'>발표하는 모델 : 오인용</h1>
    </div>
    """.format(base64.b64encode(open("assets/image4.png", "rb").read()).decode()), unsafe_allow_html=True)

    
    st.markdown(f"""
    <div style='margin-top: 2.5rem; font-weight: bold; font-size: 1.05rem;'>
        <h3>📝 <strong>사용 가이드</strong></h3>
        <ul>
            <li><strong>발표자료를 <span style="color:#d63384;"><strong>PDF파일</strong></span>로 업로드해주세요.</strong></li>
            <li><strong><span style="color:#0d6efd;">5문단</span> 이상의 <span style="color:#0d6efd;"><strong>프로젝트 스토리</strong></span>를 작성해주세요.</strong></li>
            <li><strong>입력하시는 <span style="color:#0d6efd;">프로젝트의 스토리가 구체적일수록</span> 대본의 퀄리티가 올라갑니다.</strong></li>
            <li><strong>강조하고 싶은 단어는 <span style="color:#dc3545;"><strong>쉼표(,)</strong></span>로 구분하여 입력해주세요.</strong></li>
            <li><strong><span style="color:#fd7e14;">내용이 없는 파티션 슬라이드</span>는 제거해주세요.</strong></li>
            <li><strong>스크립트 생성에는 발표자료의 길이에 따라 <span style="color:#198754;">다소 시간(수 분 가량)</span>이 소요될 수 있습니다.</strong></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    if st.button(":loudspeaker: 발표하러 가기"):
        st.session_state.app_page = "presentation"
        st.session_state.current_page = 1
        st.session_state.current_slide = 0
        st.rerun()

def render_presentation_workflow():
    font_path = get_korean_font()
    if font_path:
        styled_container()

    st.markdown("""
    <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;'>
        <img src='data:image/png;base64,{}' width='150'>
        <h1 style='margin: 0;'>발표 준비 단계</h1>
    </div>
    """.format(base64.b64encode(open("assets/image6.png", "rb").read()).decode()), unsafe_allow_html=True)


    if st.session_state.current_page == 1:
        st.subheader("1단계. 발표자료 및 정보 입력")

        with st.container():
            st.markdown("<div style='font-weight:bold; margin-bottom: 0.002px;'>🎙️ TTS 목소리 선택</div>", unsafe_allow_html=True)
            st.session_state.selected_voice = st.selectbox("", options=list(VOICE_OPTIONS.values()),
                                                           format_func=lambda x: [k for k, v in VOICE_OPTIONS.items() if v == x][0])
            
            st.markdown("<div style='font-weight:bold; margin-bottom: 0.002px;'>✔️ 강조할 키워드 (쉼표로 구분)</div>", unsafe_allow_html=True)
            keywords_input = st.text_input(
                "",
                value=", ".join(st.session_state.keywords),
                placeholder="인공지능, 발표, 기획, 자동화"
            )

            st.session_state.keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

            st.markdown("<div style='font-weight:bold; margin-bottom: 0.002px;'>📜 PDF 발표자료 업로드</div>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("", type=['pdf'])
            if uploaded_file:
                st.session_state.pdf_file = uploaded_file
                st.session_state.pdf_bytes = uploaded_file.read()
                doc = fitz.open(stream=st.session_state.pdf_bytes, filetype="pdf")
                st.session_state.total_pages = len(doc)
                st.success(f"👏🏻 PDF 업로드 완료 ({st.session_state.total_pages}페이지)")

            st.markdown("<div style='font-weight:bold; margin-bottom: 0.002px;'>📖 프로젝트 스토리 입력</div>", unsafe_allow_html=True)
            st.session_state.full_document = st.text_area(
            "",
            height=200,
            placeholder=(
                "1. 프로젝트 배경과 필요성\n"
                "발표에 대한 두려움과 어려움을 해결하고자 누구나 쉽게 발표할 수 있는 자동화 시스템의 필요성이 대두되었습니다.\n\n"
                "2. 프로젝트 개요와 시스템 구조\n"
                "PDF와 요약 텍스트를 입력하면 AI가 자동으로 대본을 생성하고 음성으로 변환하여 발표와 Q&A까지 지원하는 시스템을 개발했습니다.\n\n"
                "3. 기술 구성 및 핵심 기능\n"
                "GPT-4o-mini, LangChain, FastAPI 기반의 시스템은 대본 생성, TTS 발표, 실시간 챗봇 기능과 다양한 발표 최적화 기술을 포함합니다.\n\n"
                "4. 미래 확장성\n"
                "보안 강화, 캐릭터 도입, 실시간 인터랙션 등으로 다양한 발표 환경에 확장 가능한 구조를 지향합니다.\n\n"
                "5. 활용 계획\n"
                "교육, 기업, 고객 응대 등 다양한 분야에서 자동 발표 시스템으로 활용될 수 있습니다."
            )
        )

            if all([st.session_state.pdf_file, st.session_state.full_document, st.session_state.keywords]):
                if st.button(":arrow_right: 다음 단계로 이동"):
                    st.session_state.current_page = 2
                    st.rerun()
            else:
                st.info("❗ 모든 항목을 입력해야 다음 단계로 진행됩니다.")

    elif st.session_state.current_page == 2:
        st.subheader("2단계. 슬라이드별 스크립트 생성 및 확인")
        st.markdown("<script>window.scrollTo(0, 0);</script>", unsafe_allow_html=True)

        if not st.session_state.scripts:
            with st.spinner("스크립트와 음성 생성 중..."):
                try:
                    files = {"file": ("document.pdf", st.session_state.pdf_bytes, "application/pdf")}
                    data = {"full_document": st.session_state.full_document}
                    response = requests.post(f"{API_URL}/generate-script", files=files, data=data)
                    if response.status_code == 200:
                        st.session_state.scripts = response.json() 
                        
                        # 🎯 Q&A 활성화 요청
                        script_data = [{"page": i, "script": s if isinstance(s, str) else s.get("script", "")}
                                    for i, s in enumerate(st.session_state.scripts)]
                        enable_res = requests.post(f"{API_URL}/qa/enable", json={
                            "full_document": st.session_state.full_document,
                            "script_data": script_data
                        })

                        gender = st.session_state.selected_voice

                        audio_res = requests.post(f"{API_URL}/generate-audio", json={
                            "scripts": {str(i): s if isinstance(s, str) else s.get("script", "") for i, s in enumerate(st.session_state.scripts)},
                            "keywords": st.session_state.keywords,
                            "gender": gender  # 명시적으로 전달
                        })
                        if audio_res.status_code == 200:
                            st.session_state.tts_audios = audio_res.json()
                            st.markdown("""
                            <style>
                            .success-highlight {
                                background-color: #d1e7dd;
                                color: #0f5132;
                                padding: 1rem;
                                border-left: 6px solid #0f5132;
                                border-radius: 8px;
                                font-weight: bold;
                                font-size: 1.05rem;
                            }
                            </style>
                            """, unsafe_allow_html=True
                            )
                            st.markdown('<div class="success-highlight">✅ 전체 스크립트와 음성이 생성되었습니다!</div>', unsafe_allow_html=True)
                        else:
                            st.error(f"TTS 생성 오류: {audio_res.text}")
                    else:
                        st.error(f"API 오류: {response.text}")
                except Exception as e:
                    st.error(f"스크립트 생성 실패: {str(e)}")

        if st.session_state.scripts:
            page_num = st.session_state.current_slide
            st.markdown(f"<div class='page-container'><div class='page-title'><strong>슬라이드 {page_num + 1}</strong></div></div>", unsafe_allow_html=True)
            st.image(convert_pdf_page_to_image(st.session_state.pdf_bytes, page_num), use_container_width=True)

            current_script = st.session_state.scripts[page_num]
            if isinstance(current_script, dict):
                current_script = current_script.get("script", "")

            st.markdown("<div class='script-container'><h4>발표 스크립트</h4></div>", unsafe_allow_html=True)
            st.markdown("**여기서 생성된 대본을 수정할 수 있습니다. 수정된 대본에 맞게 음성도 재생성할 수 있습니다.**")
            edited_script = st.text_area(label="", value=current_script, height=150, key=f"script_{page_num}")
            if edited_script != current_script:
                st.session_state.scripts[page_num] = edited_script
                st.success("❗스크립트가 수정되었습니다!")

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

            # 마지막 슬라이드일 때만 표시되는 버튼
            if page_num == st.session_state.total_pages - 1:
                col1, col_spacer, col2, col_spacer2, col3 = st.columns([1.3, 0.5, 1.5, 0.5, 1.3])

                with col1:
                    if st.button("🔁 음성 재생성"):
                        try:
                            with st.spinner("음성 재생성 중..."):
                                response = requests.post(f"{API_URL}/generate-audio", json={
                                    "scripts": {
                                        str(i): s if isinstance(s, str) else s.get("script", "")
                                        for i, s in enumerate(st.session_state.scripts)
                                    },
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
                    if st.button("📦 발표자료 다운로드"):
                        try:
                            with st.spinner("ZIP 파일 생성 중..."):
                                files = {
                                    "file": ("presentation.pdf", st.session_state.pdf_bytes, "application/pdf")
                                }
                                data = {"wav_dir": "../data/audio"}
                                response = requests.post(f"{API_URL}/export-presentation", files=files, data=data)
                                if response.status_code == 200:
                                    st.download_button(
                                        "📥 다운로드 (ZIP)",
                                        data=response.content,
                                        file_name="presentation_bundle.zip",
                                        mime="application/zip"
                                    )
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

    st.markdown(f"""
        <div style='text-align:center; font-weight:bold; font-size: 1.2rem; margin-top: 10px;'>
            <strong>슬라이드 {page_num + 1} / {st.session_state.total_pages}</strong>
        </div>
    """, unsafe_allow_html=True)
    st.image(convert_pdf_page_to_image(st.session_state.pdf_bytes, page_num), use_container_width=True)

    audio_b64 = st.session_state.tts_audios.get(str(page_num)) if isinstance(st.session_state.tts_audios, dict) else None
    if audio_b64:
        st.audio(base64.b64decode(audio_b64), format="audio/wav")

    col1, spacer, col2 = st.columns([1.5, 4, 1.5])
    with col1:
        if page_num > 0 and st.button("이전 슬라이드 ⬅"):
            st.session_state.presentation_slide -= 1
            st.rerun()
    with col2:
        if page_num < st.session_state.total_pages - 1 and st.button("다음 슬라이드 ➡"):
            st.session_state.presentation_slide += 1
            st.rerun()

def main():
    initialize_session_state()
    set_background("assets/background.png")  # 배경 이미지
    if st.session_state.app_page == "presentation":
        render_presentation_workflow()
        show_chat_interface()
    elif st.session_state.app_page == "presentation_view":
        render_presentation_mode()
    else:
        render_home_page()

if __name__ == "__main__":
    main()