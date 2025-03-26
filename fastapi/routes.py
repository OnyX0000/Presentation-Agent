from fastapi import APIRouter, UploadFile, File, Form
from typing import List, Optional
from fastapi.responses import JSONResponse
from core.script_generate import Generate_Script

router = APIRouter()  



@router.post("/generate-script")
async def generate_script(
    file: UploadFile = File(...),
    full_document: str = Form(...)
):
    try:
        generator = Generate_Script(pdf_file=file, full_document=full_document)
        generator.extract_page()
        generator.filter_important_images()
        structured = generator.generate_full_script()
        return JSONResponse({"slides": structured})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/chatpdf")
async def chat_with_pdf(r):
    # PDF 기반 Q&A
    pass