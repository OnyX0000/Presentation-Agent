import fitz
from typing import List, Dict
from state import PDFState

class PDFInitializer:
    def __init__(self, state: PDFState):
        self.state = state
        
    def initialize(self, uploaded_file):
        """PDF 초기화"""
        self.state.initialize_pdf(uploaded_file) 