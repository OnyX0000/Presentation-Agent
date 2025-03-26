from pathlib import Path
from fastapi import UploadFile
from langchain.schema import SystemMessage, HumanMessage
from models import script_llm
from PIL import Image
import base64
import fitz
import io
import os
import uuid

PDF_DIR = Path(r"..\data\save_pdf")
txt_DIR = Path(r"..\data\save_txt")
IMAGE_DIR = Path(r"..\data\temp_images")

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

def compress_image_to_jpeg(img_bytes: bytes, quality: int = 50) -> bytes:
    """이미지 바이트를 JPEG 형식으로 압축"""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    return output.getvalue()

def convert_image_to_base64(image_bytes):
    '''이미지를 base64로 변환'''
    return base64.b64encode(image_bytes).decode("utf-8")

def extract_image_bytes(doc, xref):
    '''이미지를 바이트로 추출'''
    pix = fitz.Pixmap(fitz.csRGB, doc.get_pixmap(xref))
    img_bytes = pix.tobytes()
    return img_bytes

def compress_full_document(full_doc: str, max_len: int = 300) -> str:
    """전체 문서를 300자 이내로 요약"""
    if len(full_doc) <= max_len:
        return full_doc  # 이미 충분히 짧으면 그대로 사용

    llm = script_llm()  # gpt-4o-mini 기반 요약기 사용

    messages = [
        SystemMessage(content="당신은 전문 요약 AI입니다."),
        HumanMessage(content=(
            f"다음 문서를 300자 이내로 간결하고 핵심적으로 요약해주세요:\n\n{full_doc}"
        ))
    ]

    summary = llm.invoke(messages)
    return summary.content.strip()