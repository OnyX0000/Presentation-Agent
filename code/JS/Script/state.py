from typing import List, Dict, Optional
import fitz
import base64
import tempfile
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
import streamlit as st

class PDFState:
    def __init__(self):
        self.pdf_path: Optional[str] = None
        self.doc: Optional[fitz.Document] = None
        self.data: List[Dict] = []
        self.current_page: int = 0
        self.total_pages: int = 0
        self.scripts: List[str] = []
        self.temp_file: Optional[str] = None
        
    def initialize_pdf(self, uploaded_file):
        """PDF 파일 초기화"""
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            self.temp_file = tmp_file.name
            
        self.pdf_path = self.temp_file
        self.doc = fitz.open(self.pdf_path)
        self.total_pages = len(self.doc)
        self.current_page = 0
        self.data = []
        self.scripts = []
        
    def cleanup(self):
        """임시 파일 정리"""
        if self.temp_file and os.path.exists(self.temp_file):
            os.unlink(self.temp_file)
            self.temp_file = None
            
    def convert_image_to_base64(self, image_bytes: bytes) -> str:
        """이미지 바이트를 base64 문자열로 변환"""
        return base64.b64encode(image_bytes).decode('utf-8')
        
    def get_total_image_area_ratio(self, page, images) -> float:
        """페이지에서 감지된 모든 이미지의 총 면적 비율을 계산"""
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