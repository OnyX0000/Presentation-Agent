from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
from fastapi.responses import JSONResponse
from core.script_generate import Generate_Script
from core.chatbot_qa import chatbot_qa
from models import PresentationState, ChatRequest, ChatResponse


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