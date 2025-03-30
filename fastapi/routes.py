from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from typing import List, Optional, Dict, Union
from fastapi.responses import JSONResponse, StreamingResponse
from core.script_generate import Generate_Script
from core.chatbot_qa import chatbot_qa
from models import PresentationState, ChatRequest, ChatResponse
from utils import export_pdf_with_audio_to_pptx, export_pptx_with_wavs_as_zip
from core.TTS_tunning import TTSEngine
from starlette.responses import Response
import io
import tempfile

router = APIRouter()  

@router.post("/generate-script")
async def generate_script(
    file: UploadFile = File(...),
    full_document: str = Form(...)
):
    try:
        generator = Generate_Script(pdf_file=file, full_document=full_document)
        chatbot_qa.update_context(full_document)
        generator.extract_page()
        generator.filter_important_images()
        structured = generator.generate_full_script()
        return JSONResponse({"slides": structured})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# @router.post("/chatpdf")
# async def chat_with_pdf(r):
#     # PDF 기반 Q&A
#     pass

# 프레젠테이션 관련 라우터
@router.post("/presentation/complete")
async def complete_presentation(full_document: str = Form(...)):
    """프레젠테이션 완료 상태를 저장하고 챗봇을 활성화합니다."""
    try:
        chatbot_qa.update_context("")  # 이전의 발표자료의 배경지식이 있을 수 있어 context 초기화
        chatbot_qa.update_context(full_document)  # ✅ 다시 초기화
        chatbot_qa.set_presentation_complete()
        return {"status": "success", "message": "프레젠테이션이 완료되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 챗봇 관련 라우터
@router.get("/chat/status")
async def get_chat_status():
    """챗봇 활성화 상태를 확인합니다."""
    try:
        status = chatbot_qa.get_chat_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """챗봇 질문에 대한 답변을 생성합니다."""
    try:
        answer = await chatbot_qa.process_qa_request(request.question, request.session_id)
        return ChatResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/generate-audio")
async def generate_audio(data: Dict[str, Union[Dict[str, str], List[str]]]):
    try:
        scripts = data["scripts"]
        keywords = data["keywords"]
        print("📥 /generate-audio 요청 도착")
        print(f"▶️ scripts: {len(scripts)}, keywords: {keywords}")

        tts_engine = TTSEngine()              # 인스턴스 생성
        tts_engine.clear_audio_dir()          # 기존 WAV 제거
        result = tts_engine.synthesize_pages(pages=scripts, keywords=keywords)  # 음성 생성
        print("✅ 음성 생성 완료")

        return result
    except Exception as e:
        print(f"❌ TTS 생성 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    
# @router.post("/export-to-pptx")
# async def export_to_pptx(file: UploadFile = File(...), audio_dir: str = Form(...)):
#     try:
#         from utils import export_pdf_with_audio_to_pptx
#         pdf_bytes = await file.read()
#         pptx_binary = export_pdf_with_audio_to_pptx(pdf_bytes, wav_dir=audio_dir)
#         return Response(content=pptx_binary, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/export-presentation")
async def export_presentation(
    file: UploadFile = File(...),
    wav_dir: str = Form(...)
):
    """
    PDF를 PPTX로 변환하고 오디오 삽입 후 PPTX + WAV ZIP 반환
    """
    try:
        pdf_bytes = await file.read()
        pptx_bytes = export_pdf_with_audio_to_pptx(pdf_bytes, wav_dir)
        zip_bytes = export_pptx_with_wavs_as_zip(pptx_bytes, wav_dir)

        return StreamingResponse(
            iter([zip_bytes]),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=presentation_bundle.zip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))