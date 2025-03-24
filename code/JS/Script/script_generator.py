from typing import List, Dict
import fitz
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
from state import PDFState

class ScriptGenerator:
    def __init__(self, state: PDFState):
        self.state = state
        self.llm = ChatOpenAI(model='gpt-4-vision-preview', max_tokens=1024)
        self.llm_script = ChatOpenAI(model="gpt-4", temperature=0.5)
        
    def extract_text_from_page(self, page: fitz.Page) -> str:
        """페이지에서 텍스트 추출"""
        text = page.get_text("text")
        # 불필요한 공백 제거 및 텍스트 정리
        text = " ".join(text.split())
        return text
        
    def generate_script(self, page_idx: int) -> str:
        """발표 대본 생성 메서드"""
        page = self.state.doc[page_idx]
        text = self.extract_text_from_page(page)
        
        # 이전 3페이지의 스크립트 가져오기
        previous_scripts = self.state.scripts[-3:] if self.state.scripts else []
        previous_script_text = "\n".join(previous_scripts) if previous_scripts else "없음"
        
        template = """
        다음은 발표 자료에 대한 정보 입니다:
        - 현재 페이지 텍스트: {text}
        - 이전 페이지 발표 대본: {previous_script}

        위 정보를 바탕으로 발표자가 자연스럽게 발표할 수 있도록 대본을 작성해주세요.
        대본은 다음 형식을 따르세요:
        1. 페이지의 주요 내용 요약
        2. 핵심 포인트 설명
        3. 다음 페이지로의 자연스러운 연결
        """
        
        prompt = PromptTemplate.from_template(template)
        script = self.llm_script.invoke(prompt.format(
            text=text, previous_script=previous_script_text
        ))
        
        return script.content.strip() 