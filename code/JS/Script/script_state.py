# script_state.py
from dataclasses import dataclass, field
from typing import List
from langchain.schema import Document

@dataclass
class ScriptGenState:
    """발표 대본 생성 시스템의 상태를 관리하는 데이터 클래스"""
    input_text: str = ""  # 현재 페이지의 텍스트
    input_document: str = ""  # PPT 전체 문서 정보
    previous_script: List[str] = field(default_factory=list)  # 이전 발표 대본
    reasoning: str = ""  # 모델이 고려한 사항
    documents: List[Document] = field(default_factory=list)  # OCR 데이터 등 추가 정보
    generated_script: str = ""  # 최종 생성된 발표 대본
    mode: str = "text_only"  # 동작 모드 ("text_only", "image_included", "structured")