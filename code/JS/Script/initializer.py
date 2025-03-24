import fitz
from typing import List, Dict
from state import PDFState

class PDFInitializer:
    def __init__(self, state: PDFState):
        self.state = state
        
    def extract_page(self) -> List[Dict]:
        """PDF에서 텍스트 및 이미지 정보를 추출"""
        total_pages = len(self.state.doc)
        pdf_data = []

        for page_num in range(total_pages):
            page = self.state.doc[page_num]
            text = page.get_text("text")
            images = page.get_images(full=True)
            image_data = []

            total_area_ratio = self.state.get_total_image_area_ratio(page, images)

            for img in images:
                xref = img[0]
                img_rects = page.get_image_rects(xref)
                
                if img_rects:
                    pix = fitz.Pixmap(self.state.doc, xref)
                    if pix.n > 4:  # CMYK를 RGB로 변환
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    img_bytes = pix.tobytes()
                    img_base64 = self.state.convert_image_to_base64(img_bytes)
                    
                    image_data.append({
                        "image": img_base64,
                        "image_bytes": img_bytes,
                        "total_area_ratio": total_area_ratio
                    })
                    
                    pix = None  # 메모리 해제

            pdf_data.append({
                "page": page_num + 1,
                "text": text,
                "images": image_data
            })

        return pdf_data
        
    def initialize(self, pdf_path: str):
        """PDF 초기화 및 데이터 추출"""
        self.state.initialize_pdf(pdf_path)
        self.state.data = self.extract_page() 