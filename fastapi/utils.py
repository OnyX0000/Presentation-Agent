from pathlib import Path
from fastapi import UploadFile
import base64
import fitz

PDF_DIR = Path(r"C:\wanted\Lang\Presentation-Agent\data\save_pdf")
txt_DIR = Path(r"C:\wanted\Lang\Presentation-Agent\data\save_txt")

def save_uploaded_file(file: UploadFile) -> str:
    '''고객이 업로드한 PDF파일을 저장'''
    file_path = PDF_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return str(file_path)

def save_text_to_file(text: str, filename: str = "user_input.txt") -> str:
    '''고객이 입력한 텍스트를 저장'''
    file_path = txt_DIR / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    return str(file_path)

def convert_image_to_base64(image_bytes):
    '''이미지를 base64로 변환'''
    return base64.b64encode(image_bytes).decode("utf-8")

def extract_image_bytes(doc, xref):
    '''이미지를 바이트로 추출'''
    pix = fitz.Pixmap(fitz.csRGB, doc.get_pixmap(xref))
    img_bytes = pix.tobytes()
    return img_bytes
