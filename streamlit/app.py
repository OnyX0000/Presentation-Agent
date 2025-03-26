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
                .chat-container {{
                    border: 1px solid #ddd;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 10px;
                    background-color: #f8f9fa;
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
    if 'total_pages' not in st.session_state:
        st.session_state.total_pages = 0
    if 'pdf_bytes' not in st.session_state:
        st.session_state.pdf_bytes = None
    if 'presentation_completed' not in st.session_state:
        st.session_state.presentation_completed = False

    # 페이지 1: PDF 업로드 및 텍스트 입력
    if st.session_state.current_page == 1:
        st.header("1. PDF 파일 업로드 및 텍스트 입력")
        
        # PDF 업로드
        uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type=['pdf'])
        if uploaded_file:
            st.session_state.pdf_file = uploaded_file
            st.session_state.pdf_bytes = uploaded_file.read()
            doc = fitz.open(stream=st.session_state.pdf_bytes, filetype="pdf")
            st.session_state.total_pages = len(doc)
            st.success(f"PDF 파일이 업로드되었습니다. (총 {st.session_state.total_pages}페이지)")

        # 텍스트 입력
        full_document = st.text_area("전체 문서 요약을 입력하세요", height=200)
        if full_document:
            st.session_state.full_document = full_document

        # 다음 페이지로 이동 버튼
        if st.session_state.pdf_file and st.session_state.full_document:
            if st.button("다음 단계로 이동"):
                st.session_state.current_page = 2
                st.rerun()

    # 페이지 2: 전체 스크립트 생성 및 수정
    elif st.session_state.current_page == 2:
        st.header("2. 전체 스크립트 생성 및 수정")
        
        # 이전 페이지로 돌아가기 버튼과 새로운 스크립트 생성 버튼을 나란히 배치
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← 이전으로"):
                st.session_state.current_page = 1
                st.rerun()
        with col2:
            if not st.session_state.scripts:
                if st.button("전체 스크립트 생성"):
                    try:
                        with st.spinner("스크립트 생성 중..."):
                            files = {"file": ("document.pdf", st.session_state.pdf_bytes, "application/pdf")}
                            data = {"full_document": st.session_state.full_document}
                            response = requests.post(f"{API_URL}/generate-script", files=files, data=data)
                            
                            if response.status_code == 200:
                                result = response.json()
                                scripts = result.get("slides", [])
                                if scripts:
                                    st.session_state.scripts = scripts
                                    st.success("전체 스크립트가 생성되었습니다!")
                                else:
                                    st.error("스크립트 생성 중 오류가 발생했습니다.")
                            else:
                                st.error(f"API 오류: {response.text}")
                    except Exception as e:
                        st.error(f"오류 발생: {str(e)}")

        # 스크립트가 생성된 경우 페이지별로 표시
        if st.session_state.scripts:
            for page_num in range(st.session_state.total_pages):
                with st.container():
                    st.markdown(f"""
                        <div class="page-container">
                            <div class="page-title">슬라이드 {page_num + 1}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # PDF 페이지 표시
                    img = convert_pdf_page_to_image(st.session_state.pdf_bytes, page_num)
                    st.image(img, use_container_width=True)
                    
                    # 스크립트 표시 및 수정
                    st.markdown("""
                        <div class="script-container">
                            <h4>발표 스크립트</h4>
                        </div>
                    """, unsafe_allow_html=True)
                    
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
                    
                    st.markdown("<hr>", unsafe_allow_html=True)

                    # 마지막 페이지 확인
                    if page_num == st.session_state.total_pages - 1:
                        if not st.session_state.presentation_completed:
                            if st.button("프레젠테이션 완료"):
                                try:
                                    response = requests.post(f"{API_URL}/presentation/complete")
                                    if response.status_code == 200:
                                        st.session_state.presentation_completed = True
                                        st.success("프레젠테이션이 완료되었습니다!")
                                except Exception as e:
                                    st.error(f"오류 발생: {str(e)}")

    def show_chat_interface():
        """챗봇 인터페이스를 표시합니다."""
        if st.session_state.presentation_completed:
            st.markdown("""
                <div class="chat-container">
                    <h3>질문이 있으신가요?</h3>
                </div>
            """, unsafe_allow_html=True)
            
            # 챗봇 입력창
            user_question = st.chat_input("질문을 입력하세요")
            
            if user_question:
                try:
                    response = requests.post(
                        f"{API_URL}/chat",
                        json={"question": user_question, "session_id": "streamlit_session"}
                    )
                    if response.status_code == 200:
                        answer = response.json()["answer"]
                        st.write(f"Q: {user_question}")
                        st.write(f"A: {answer}")
                    else:
                        st.error("답변 생성 중 오류가 발생했습니다.")
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
    show_chat_interface()