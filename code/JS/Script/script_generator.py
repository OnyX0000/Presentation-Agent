from typing import List, Dict
import fitz
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
from state import PDFState

class ScriptGenerator:
    def __init__(self, state: PDFState):
        self.state = state
        self.llm = ChatOpenAI(model='gpt-4o', max_tokens=1024)
        self.llm_script = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
        
    def classify_image_type(self, image_bytes: bytes) -> bool:
        """GPT-4o를 사용하여 이미지가 그래프/도표인지 판별"""
        base64_image = self.state.convert_image_to_base64(image_bytes)
        
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
        
        response = self.llm.invoke(messages)
        label = response.content.strip()
        
        return label == "그래프/도표"

    def should_interpret_image(self, image_bytes: bytes, total_area_ratio: float) -> bool:
        """이미지 해석 여부를 결정하는 함수"""
        if total_area_ratio >= 0.5:
            return True
        return self.classify_image_type(image_bytes)

    def interpret_image(self, image_bytes: bytes) -> str:
        """이미지를 해석하는 함수"""
        base64_image = self.state.convert_image_to_base64(image_bytes)
        
        prompt = (
            "다음 이미지에 대해 상세히 설명해주세요:\n"
            "1. 이미지의 종류(그래프/도표 등)\n"
            "2. 주요 내용\n"
            "3. 핵심 메시지나 트렌드\n"
            "발표자가 이해하기 쉽게 설명해주세요."
        )
        
        messages = [
            SystemMessage(content="당신은 이미지 해석 전문 AI 에이전트입니다."),
            HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ])
        ]
        
        response = self.llm.invoke(messages)
        return response.content.strip()

    def generate_script(self, page_idx: int) -> str:
        """발표 대본 생성 메서드"""
        page_data = self.state.data[page_idx]
        text = page_data["text"]

        previous_script_text = "\n".join(self.state.scripts[-3:]) if self.state.scripts else "없음"

        template = """
        다음은 발표 자료에 대한 정보 입니다:
        - 현재 페이지 텍스트: {text}
        - 이전 페이지 발표 대본: {previous_script}

        위 정보를 바탕으로 발표자가 자연스럽게 발표할 수 있도록 대본을 작성해주세요.
        """
        prompt = PromptTemplate.from_template(template)
        script = self.llm_script.invoke(prompt.format(
            text=text, previous_script=previous_script_text
        ))

        self.state.scripts.append(script)
        return script 