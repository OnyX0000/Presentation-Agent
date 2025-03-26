from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv
from pydantic import BaseModel
import os

load_dotenv("C:/wanted/Lang/Presentation-Agent/.env")

class PresentationState(BaseModel):
    """프레젠테이션 상태를 관리하는 모델"""
    is_completed: bool = False
    chat_enabled: bool = False

class ChatRequest(BaseModel):
    """챗봇 요청을 처리하는 모델"""
    question: str
    session_id: str

class ChatResponse(BaseModel):
    """챗봇 응답을 처리하는 모델"""
    answer: str
    status: str = "success"

def graph_classify_llm():
    '''그래프 분류'''
    llm = ChatOpenAI(model = 'gpt-4o-mini', temperature=0, max_tokens=64)
    return llm

def vision_llm():
    '''이미지 해석 모델'''
    llm = ChatOpenAI(model = 'gpt-4o-mini', temperature=0, max_tokens=1024)
    return llm

def script_llm():
    '''스크립트 생성 모델'''
    llm = ChatOpenAI(model = 'gpt-4o-mini', temperature=0.5, max_tokens=2048)
    return llm

def embedding_model():
    '''임베딩 모델'''
    embeddings = OpenAIEmbeddings()
    return embeddings

def QA_llm():
    '''질문 답변 모델'''
    llm = ChatOpenAI(model = 'gpt-4o-mini', temperature=0)
    return llm
