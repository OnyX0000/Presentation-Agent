import streamlit as st
from state import PDFState
from initializer import PDFInitializer
from script_generator import ScriptGenerator
from dotenv import load_dotenv

load_dotenv("C:/wanted/Lang/Presentation-Agent/.env")

def main():
    st.title("PDF 발표 대본 생성기")
    
    # 상태 초기화
    if 'state' not in st.session_state:
        st.session_state.state = PDFState()
    if 'initializer' not in st.session_state:
        st.session_state.initializer = PDFInitializer(st.session_state.state)
    if 'generator' not in st.session_state:
        st.session_state.generator = ScriptGenerator(st.session_state.state)
    
    # PDF 파일 업로드
    uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type=['pdf'])
    
    if uploaded_file is not None:
        # PDF 초기화
        if not st.session_state.state.pdf_path:
            st.session_state.initializer.initialize(uploaded_file)
        
        # 페이지 선택
        page_number = st.number_input("페이지 선택", 1, st.session_state.state.total_pages, 1)
        
        # 현재 페이지 정보 표시
        if page_number <= len(st.session_state.state.data):
            page_data = st.session_state.state.data[page_number - 1]
            
            # 텍스트 표시
            st.subheader("페이지 텍스트")
            st.text(page_data["text"])
            
            # 이미지 표시
            if page_data["images"]:
                st.subheader("페이지 이미지")
                for img in page_data["images"]:
                    st.image(f"data:image/jpeg;base64,{img['image']}")
            
            # 발표 대본 생성 버튼
            if st.button("발표 대본 생성"):
                with st.spinner("발표 대본을 생성하는 중..."):
                    script = st.session_state.generator.generate_script(page_number - 1)
                    st.subheader("생성된 발표 대본")
                    st.write(script)
            
            # 이전 발표 대본 표시
            if st.session_state.state.scripts:
                st.subheader("이전 발표 대본")
                for i, script in enumerate(st.session_state.state.scripts):
                    st.write(f"페이지 {i+1} 대본:")
                    st.write(script)

if __name__ == "__main__":
    main()