import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import compress_image_to_jpeg, convert_image_to_base64, compress_full_document 
from models import graph_classify_llm, vision_llm, script_llm
from fastapi import UploadFile
from PIL import Image
from langchain.schema import SystemMessage, HumanMessage
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from typing import List
import fitz
import re
import base64

class PDFProcessor:
    def __init__(self, pdf_file: UploadFile):
        self.pdf_file = pdf_file
        self.pdf_data = []
        self.doc = fitz.open(stream=pdf_file.file.read(), filetype="pdf")

    def get_total_image_area_ratio(self,page, images):
        """페이지에서 감지된 모든 이미지의 총 면적 비율을 계산."""
        total_ratio = 0
        for img in images:
            xref = img[0]
            img_rects = page.get_image_rects(xref)
            if img_rects:
                x0, y0, x1, y1 = img_rects[0]
                img_width = x1 - x0
                img_height = y1 - y0
                img_area = img_width * img_height
                
                page_width, page_height = page.rect.width, page.rect.height
                page_area = page_width * page_height
                
                total_ratio += img_area / page_area
        
        return total_ratio

    def classify_image_type(self, image_bytes):
        """이미지가 도표/그래프 분류"""
        llm = graph_classify_llm()

        # ✅ 압축해서 base64 용량 줄이기
        compressed_bytes = compress_image_to_jpeg(image_bytes, quality=50)
        base64_image = convert_image_to_base64(compressed_bytes)

        prompt = (
            "다음 이미지를 아래 두 가지 중 하나로 분류하세요:\n"
            "1. 그래프/도표\n"
            "2. 그외\n"
            "반드시 위 중 하나의 항목만 정확히 출력하세요."
        )

        messages = [
            SystemMessage(content="당신은 이미지 분류 전문 AI 에이전트입니다."),
            HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ])
        ]

        response = llm.invoke(messages)
        label = response.content.strip()
        return label == "그래프/도표"
    
    def should_interpret_image(self,image_bytes, total_area_ratio):
        """이미지 해석 여부를 결정하는 함수."""
        # 먼저 면적 비율 확인
        if total_area_ratio >= 0.5:
            return True
        
        # 면적 비율이 0.5 미만인 경우에만 LLM으로 그래프/도표 여부 확인
        is_graph_or_chart = self.classify_image_type(image_bytes)
        return is_graph_or_chart    
    
    def extract_page(self):
        """PDF에서 텍스트 및 이미지 정보를 추출."""
        doc = self.doc
        total_pages = len(doc)
        pdf_data = []

        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text("text")
            images = page.get_images(full=True)
            image_data = []

            # 페이지의 총 이미지 면적 비율 계산
            total_area_ratio = self.get_total_image_area_ratio(page, images)

            for img in images:
                xref = img[0]
                img_rects = page.get_image_rects(xref)
                
                if img_rects:
                    # 이미지 추출
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n > 4:  # CMYK를 RGB로 변환
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    # 이미지를 바이트로 변환
                    img_bytes = pix.tobytes()
                    img_base64 = convert_image_to_base64(img_bytes)
                    
                    # 이미지 해석 여부 결정 (면적 비율 먼저 확인 후 필요시 LLM 사용)
                    should_interpret = self.should_interpret_image(img_bytes, total_area_ratio)
                    
                    image_data.append({
                        "image": img_base64,
                        "image_type": should_interpret
                    })
                    
                    pix = None  # 메모리 해제

            pdf_data.append({
                "page": page_num + 1,
                "text": text,
                "images": image_data
            })
        self.pdf_data = pdf_data
        return pdf_data
    
    def filter_important_images(self):
        """
        PDF 데이터에서 해석이 필요한 이미지(image_type이 True)만 필터링하여 반환
        페이지는 모두 유지하고 이미지만 필터링합니다.
        """
        filtered_data = []
        
        for page_info in self.pdf_data:
            # image_type이 True인 이미지만 필터링
            important_images = [img for img in page_info['images'] if img['image_type']]
            
            # 모든 페이지를 포함하되, 필터링된 이미지만 포함
            filtered_data.append({
                "page": page_info['page'],
                "text": page_info['text'],
                "images": important_images  # 빈 리스트가 될 수도 있음
            })
        
        self.pdf_data = filtered_data
        return self.pdf_data
    
class Generate_Script(PDFProcessor):
    def __init__(self, pdf_file: UploadFile, full_document: str):
        super().__init__(pdf_file)
        self.full_document = compress_full_document(full_document)
        self.llm = script_llm()
        self.vision_llm = vision_llm()
        self.previous_script: List[str] = []

        # Buffer memory 적용
        self.memory = ConversationBufferMemory(return_messages=True)
        self.conversation = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            verbose=False
        )

        self.system_msg = SystemMessage(
            content=(
                "당신은 발표 대본 작성 전문가입니다. 발표자는 여러 장의 슬라이드를 기반으로 전문적이고 자연스러운 발표를 합니다.\n"
                "- 오직 첫 번째 페이지에서만 인사를 합니다.\n"
                "- 각 페이지는 이전 발표와 이어지는 흐름의 일부로 작성해야 합니다.\n"
                "- 현재 페이지의 텍스트를 가장 중요하게 반영해야 하며, 핵심 내용을 강조하십시오.\n"
                "- 전체 문서 내용과 이전 페이지 대본은 참고용입니다.\n"
                "- 슬라이드가 마지막이 아니면 '마지막으로', '끝으로' 등의 표현도 사용하지 마세요.\n"
                "- 반드시 [슬라이드 n] 형식으로 각 슬라이드 시작을 명시하고, 슬라이드 수에 맞게 정확히 작성하세요."
            )
        )

    def image_analysis(self, page_idx: int) -> str:
        page_data = self.pdf_data[page_idx]
        images = page_data["images"]
        image_descriptions = []

        for image in images:
            if image["image_type"]:
                # ✅ 이미지 base64를 다시 디코딩해서 압축 처리
                image_bytes = base64.b64decode(image["image"])
                compressed_bytes = compress_image_to_jpeg(image_bytes, quality=50)
                compressed_base64 = convert_image_to_base64(compressed_bytes)

                template = """
                다음은 발표 자료에 대한 정보입니다:
                - 전체 문서 요약: {full_document}
                - 현재 페이지 텍스트: {page_text}
                - 이미지(base64): {image}

                위 정보를 참고하여 이 이미지를 발표자가 어떻게 설명할지 서술형으로 작성해주세요.
                """
                prompt = PromptTemplate.from_template(template)
                image_desc = self.vision_llm.invoke(prompt.format(
                    full_document=self.full_document,
                    page_text=page_data["text"],
                    image=compressed_base64
                ))
                image_descriptions.append(image_desc.content.strip())  # ✅ 핵심 수정

        return '\n'.join(image_descriptions) if image_descriptions else ""

    def generate_script(self, page_idx: int) -> str:
        page_data = self.pdf_data[page_idx]
        text = page_data["text"]
        image_descriptions = self.image_analysis(page_idx)
        previous_script_text = "\n".join(self.previous_script[-2:]) if self.previous_script else "없음"

        prompt_text = f"""
    [슬라이드 {page_idx + 1}]

    다음은 발표 자료에 대한 정보입니다:
    - 전체 문서 요약 (참고용): {self.full_document}
    - 현재 슬라이드 텍스트: {text}
    - 이미지 설명: {image_descriptions}
    - 직전 발표 내용 (참고용): {previous_script_text}

    발표자는 현재 슬라이드를 **혼자서 설명**하는 상황입니다.

    ❗ 반드시 현재 슬라이드 텍스트를 중심으로 설명하세요.
    ❗ 다음 슬라이드에 나올 내용을 미리 설명하지 마세요.
    ❗ 발표 흐름을 자연스럽게 이어가되, **미리 결론 내리지 마세요.**
    ❗ 대본은 3~5문장 정도로 간결하고, 명확하게 작성하세요.

    이 정보를 바탕으로 자연스럽고 명확한 발표 대본을 작성해주세요.
    """

        input_text = f"{self.system_msg.content}\n\n{prompt_text}"
        response = self.conversation.predict(input=input_text)
        script = response.strip()

        self.previous_script.append(script)
        return script

    def generate_full_script(self, chunk_size: int = 5) -> List[str]:
        all_scripts = []
        total_pages = len(self.pdf_data)
        chunks = [self.pdf_data[i:i + chunk_size] for i in range(0, total_pages, chunk_size)]

        for chunk_idx, chunk_pages in enumerate(chunks):
            pages_text = []
            is_last_chunk = (chunk_idx == len(chunks) - 1)

            for page in chunk_pages:
                page_number = page["page"]
                text = page["text"].strip()
                image_summaries = []

                for img in page["images"]:
                    if img["image_type"]:
                        image_prompt = PromptTemplate.from_template("""
                        아래 슬라이드 내용을 참고하여, 발표자가 이미지에 대해 설명할 수 있는 문장을 작성하세요.
                        - 슬라이드 텍스트: {page_text}
                        """)
                        image_desc = self.vision_llm.invoke(image_prompt.format(page_text=text)).content.strip()
                        image_summaries.append(image_desc)

                combined = f"[슬라이드 {page_number} / 총 {total_pages} 슬라이드 중]\n- 텍스트: {text}\n- 이미지 설명: {' / '.join(image_summaries)}"
                pages_text.append(combined)

            combined_text = "\n\n".join(pages_text)

            system_msg_content = (
                "당신은 발표 대본 작성 전문가입니다. 아래는 여러 슬라이드 내용입니다.\n"
                "- 각 페이지마다 '[슬라이드 번호]' 형식으로 슬라이드 구분을 명확히 하여 작성해주세요.\n"
                "- 슬라이드는 총 {total_pages}개입니다. 정확히 {total_pages}개의 슬라이드만 작성해야 합니다.\n"
                "- 첫 번째 페이지만 인사를 포함하세요.\n"
                "- 발표 흐름이 자연스럽게 이어지도록 작성하세요.\n"
                "- 이 chunk는 전체 발표의 일부입니다. 이 chunk에서 발표를 마치지 마세요.\n"
                "- '이상으로 발표를 마칩니다', '감사합니다' 등의 마무리 멘트를 하지 마세요.\n"
                "- 슬라이드가 마지막이 아니면 '마지막으로', '끝으로' 등의 표현도 사용하지 마세요.\n"
            ).format(total_pages=total_pages)

            if is_last_chunk:
                system_msg_content += (
                    "- 이번 chunk는 마지막 발표 부분이므로, 여기서만 마무리 멘트를 포함해도 됩니다.\n"
                )

            prompt_text = f"""
            다음은 발표 자료 일부입니다. 각 페이지는 슬라이드 하나에 해당하며, 번호는 순서입니다.

            {combined_text}

            각 슬라이드에 대해 '[슬라이드 n]' 형식으로 대본을 구분하여 작성해주세요.
            """

            input_text = f"{system_msg_content}\n\n{prompt_text}"
            response = self.conversation.predict(input=input_text)

            scripts = re.split(r"\[슬라이드 \d+\]", response.strip())
            scripts = [s.strip() for s in scripts if s.strip()]

            if len(scripts) != len(chunk_pages):
                print(f" 경고: 슬라이드 수({len(chunk_pages)})와 생성된 대본 수({len(scripts)})가 일치하지 않습니다.")

            all_scripts.extend(scripts)

        return all_scripts
    

# import os
# from fastapi import UploadFile
# import io

# # 테스트용 PDF 파일 경로 설정
# TEST_PDF_PATH = r"C:\wanted\Lang\Presentation-Agent\data\save_pdf\O3.pdf"  # 실제 경로에 맞게 수정하세요.

# def simulate_upload_file(file_path: str) -> UploadFile:
#     """로컬 PDF 파일을 UploadFile처럼 시뮬레이션"""
#     filename = os.path.basename(file_path)
#     with open(file_path, "rb") as f:
#         contents = f.read()
#     file_like = io.BytesIO(contents)
#     upload_file = UploadFile(filename=filename, file=file_like)
#     return upload_file

# def main():
#     print("✅ PDF 파일 준비 중...")
#     fake_upload = simulate_upload_file(TEST_PDF_PATH)

#     # 전체 문서 요약을 간단히 제공
#     with open(r"C:\wanted\Lang\Presentation-Agent\data\txt\presentation_agent.txt", "r", encoding="utf-8") as f:
#         full_doc_summary = f.read()

#     print("✅ Generate_Script 인스턴스 생성 중...")
#     generator = Generate_Script(pdf_file=fake_upload, full_document=full_doc_summary)

#     print("📄 PDF 페이지에서 텍스트 및 이미지 추출 중...")
#     pdf_data = generator.extract_page()
#     print(f"📄 총 {len(pdf_data)}페이지 분석 완료")

#     for i, page in enumerate(pdf_data):
#         print(f"  - 페이지 {i+1}: 텍스트 길이 {len(page['text'])} / 이미지 수: {len(page['images'])}")

#     print("🔍 중요한 이미지 필터링 중...")
#     filtered_data = generator.filter_important_images()
#     for i, page in enumerate(filtered_data):
#         print(f"  - 페이지 {i+1}: 해석이 필요한 이미지 수: {len(page['images'])}")

#     print("🧠 페이지별 발표 대본 생성 테스트 중...")
#     for idx in range(min(4, len(filtered_data))):
#         print(f"\n📢 [슬라이드 {idx+1}] 대본 생성 중...")
#         script = generator.generate_script(idx)
#         print(f"🎙️ 생성된 대본:\n{script}")

#     print("\n📚 전체 문서 기반 대본 생성 중...")
#     full_scripts = generator.generate_full_script(chunk_size=3)
#     for idx, s in enumerate(full_scripts):
#         print(f"\n[슬라이드 {idx+1}]\n{s}")

# if __name__ == "__main__":
#     main()