import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from models import CHATBOT_LLM, PresentationState, ChatRequest, ChatResponse


class ChatbotService:
    def __init__(self):
        self.chatbot = CHATBOT_LLM
        self.state = PresentationState(is_completed=False, chat_enabled=False)
        self.context_loaded = False

    def update_context(self, context_text: str):
        """system_prompt용 context 설정 및 체인 생성"""
        self.chatbot.get_template(system_context=context_text)
        self.chatbot._make_chain()
        self.context_loaded = True
        print("✅ system_context 및 체인 설정 완료")

    def set_presentation_complete(self):
        """프레젠테이션 완료 상태"""
        self.state.is_completed = True
        self.state.chat_enabled = True
        print("✅ 프레젠테이션 완료, 챗봇 활성화")

    def get_status(self) -> dict:
        """현재 챗봇 상태 반환"""
        return self.state.dict()

    async def process_qa_request(self, question: str, session_id: str) -> str:
        """질문에 대한 답변 생성"""
        if not self.state.chat_enabled:
            return "프레젠테이션이 완료된 후에 질문해주세요."

        if not self.context_loaded:
            return "챗봇이 아직 초기화되지 않았습니다. 배경 정보를 먼저 등록해주세요."

        return self.chatbot.invoke(question, session_id)

    def get_chat_history(self, session_id: str) -> BaseChatMessageHistory:
        """세션별 대화 기록 조회"""
        return self.chatbot.get_chat_history(session_id)