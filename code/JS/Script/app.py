import streamlit as st
from state import PDFState
from initializer import PDFInitializer
from script_generator import ScriptGenerator
from dotenv import load_dotenv

load_dotenv(r"C:\wanted\Lang\Presentation-Agent\.env")

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
        
        # 모든 페이지의 스크립트 생성 버튼
        if st.button("모든 페이지 발표 대본 생성"):
            with st.spinner("발표 대본을 생성하는 중..."):
                for page_idx in range(st.session_state.state.total_pages):
                    script = st.session_state.generator.generate_script(page_idx)
                    st.session_state.state.scripts.append(script)
                st.success("모든 페이지의 발표 대본이 생성되었습니다!")
        
        # 모든 페이지의 이미지와 스크립트 표시
        for page_idx in range(st.session_state.state.total_pages):
            st.markdown(f"### 페이지 {page_idx + 1}")
            
            # 페이지 PDF 이미지 표시
            st.image(f"data:image/png;base64,{st.session_state.state.page_images[page_idx]}", 
                    use_column_width=True)
            
            # 해당 페이지의 발표 대본 표시
            if len(st.session_state.state.scripts) > page_idx:
                st.markdown("#### 발표 대본")
                st.write(st.session_state.state.scripts[page_idx])
            else:
                st.info("이 페이지의 발표 대본이 아직 생성되지 않았습니다.")
            
            st.markdown("---")  # 구분선 추가

if __name__ == "__main__":
    main()