# # upload_app.py
# import streamlit as st
# import time

# st.title("발표 자료를 업로드하세요")

# # 파일 업로드 버튼
# uploaded_file = st.file_uploader("파일 업로드", type=["pdf", "pptx", "docx"])

# if uploaded_file:
#     st.write("파일이 업로드되었습니다. 처리 중...")
#     with st.spinner("Loading..."):
#         time.sleep(3)  # 파일 처리 시뮬레이션
#     st.success("파일 업로드 완료!")

# visualization_app.py
import streamlit as st
from PIL import Image

st.title("발표 자료 처리 완료")

# 예제 이미지 표시
image = Image.open("../../data/0.jpg")  # 적절한 이미지 파일로 변경 필요
st.image(image, caption="프로젝트 설계", use_container_width=True)

st.markdown("### 2. 프로젝트 설계")
st.markdown("지금부터 프로젝트 설계에 대해 설명하겠습니다.")
st.markdown("---")

# 오디오/비디오 시뮬레이션 (실제 파일이 있다면 변경 가능)
st.audio("../../data/1000.wav")  # 적절한 오디오 파일로 변경 필요

## download_app.py
# import streamlit as st

# st.title("처리된 자료 다운로드")

# # 공백 추가하여 버튼을 아래로 이동
# st.write("\n" * 10)  # 개행(줄바꿈)으로 간격 추가

# # 다운로드 버튼
# st.download_button(
#     label="📥 파일 다운로드",
#     data="이 파일은 예제 데이터입니다.",  # 실제 파일 데이터를 넣어야 함
#     file_name="processed_presentation.pdf",
#     mime="application/pdf"
# )

# # 추가적인 공백으로 버튼을 더욱 아래로 배치 가능
# st.write("\n" * 5)