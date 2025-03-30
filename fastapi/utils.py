from pathlib import Path
from fastapi import UploadFile
from langchain.schema import SystemMessage, HumanMessage
from models import script_llm
from PIL import Image
import re
from typing import List, Dict, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from google.cloud import texttospeech_v1 as tts
from pptx import Presentation
from pptx.util import Inches
from typing import Optional
import tempfile, zipfile
import base64
import fitz
import io
import os
import uuid

PDF_DIR = Path(r"..\data\save_pdf")
txt_DIR = Path(r"..\data\save_txt")
IMAGE_DIR = Path(r"..\data\temp_images")
AUDIO_DIR = Path("../data/audio")

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

def clear_audio_dir(audio_dir: Path):
    """기존 음성 파일 모두 삭제"""
    for file in audio_dir.glob("*.wav"):
        file.unlink()

def export_pdf_with_audio_to_pptx(pdf_bytes: bytes, wav_dir: str) -> bytes:
    """
    PDF 파일을 PPTX로 변환하고, 각 페이지에 대응되는 오디오(WAV)를 삽입하여 반환.

    Parameters:
    - pdf_bytes: Streamlit에서 업로드한 PDF의 byte stream
    - wav_dir: 페이지별 WAV 파일이 저장된 디렉터리 (파일명: page_0.wav, page_1.wav, ...)

    Returns:
    - PPTX byte stream (다운로드용)
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    ppt = Presentation()

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)

        # 📷 PDF 페이지 → 이미지로 렌더링
        image_path = os.path.join(tempfile.gettempdir(), f"slide_{page_index}.png")
        page.get_pixmap(matrix=fitz.Matrix(2, 2)).save(image_path)

        # 🎞️ 새 슬라이드 추가 + 이미지 삽입
        slide = ppt.slides.add_slide(ppt.slide_layouts[6])
        slide.shapes.add_picture(image_path, Inches(0), Inches(0), width=Inches(10), height=Inches(7.5))

        # 🔈 오디오 삽입
        audio_path = os.path.join(wav_dir, f"page_{page_index}.wav")
        if os.path.exists(audio_path):
            try:
                slide.shapes.add_movie(
                    audio_path,
                    left=Inches(0.5), top=Inches(0.5),
                    width=Inches(1), height=Inches(1),
                    mime_type='audio/wav'
                )
                print(f"✅ Slide {page_index+1}: 오디오 삽입 완료")
            except Exception as e:
                print(f"⚠️ Slide {page_index+1}: 오디오 삽입 실패 → {e}")
        else:
            print(f"⚠️ Slide {page_index+1}: WAV 파일 없음 → {audio_path}")

    # 💾 결과 임시 파일로 저장 후 byte 반환
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        ppt.save(tmp.name)
        tmp.seek(0)
        return tmp.read()
    
def export_pptx_with_wavs_as_zip(pptx_bytes: bytes, wav_dir: str) -> bytes:
    """PPTX 파일과 WAV 파일들을 하나의 ZIP으로 묶어 반환"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
        with zipfile.ZipFile(tmp_zip.name, 'w') as zipf:
            # PPTX 파일 추가
            zipf.writestr("presentation.pptx", pptx_bytes)
            
            # WAV 파일들 추가
            for filename in os.listdir(wav_dir):
                if filename.endswith(".wav"):
                    filepath = os.path.join(wav_dir, filename)
                    zipf.write(filepath, arcname=os.path.join("audio", filename))

        tmp_zip.seek(0)
        return tmp_zip.read()