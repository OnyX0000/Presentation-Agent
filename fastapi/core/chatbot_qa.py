# API 키를 환경변수로 관리하기 위한 설정 파일
from dotenv import load_dotenv
# API 키 정보 로드
load_dotenv(r'C:\Users\user\Documents\GitHub\Presentation-Agent\.env')

from langchain.storage import InMemoryStore
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_openai import ChatOpenAI

# 시스템 프롬프트 로드
with open("C:/Users/user/Documents/GitHub/Presentation-Agent/data/txt/pt_context.txt", encoding="utf-8") as f:
    system_context = f.read()

class ChatbotQA:
    def __init__(self):
        # 텍스트 분할기 설정
        self.parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=250, 
            separators=['==================================================', '---.*?---', '===.*?===']
        )
        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, 
            chunk_overlap=100
        )
        
        # 임베딩 설정
        self.embeddings = OpenAIEmbeddings()
        
        # 벡터 저장소 설정
        self.db = Chroma(
            persist_directory=r"C:\Users\user\Documents\GitHub\Presentation-Agent\data\db\chromadb\split_knowledge", 
            embedding_function=self.embeddings
        )
        
        # 부모 문서 저장소 설정
        self.parent_store = InMemoryStore()
        
        # 검색기 설정
        self.retriever = self.db.as_retriever(search_kwargs={"k": 3})
        
        # LLM 설정
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # 대화 이력 저장소
        self.chat_history_store = {}
        
        # 프레젠테이션 상태
        self.presentation_state = {
            "is_completed": False,
            "chat_enabled": False
        }
        
        # 체인 설정
        self.setup_chains()

    def setup_chains(self):
        """체인 설정"""
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", f"당신은 발표자료에 대한 내용을 질문받으면 그에 대한 답을 하는 AI 에이전트입니다.\n"
                       f"다음은 발표자료에 대한 배경 정보입니다:\n\n{system_context}\n\n"
                       f"답변은 간결하게 100토큰 이내로만 작성해주세요.\n"
                       f"사용자가 처음 물어봐서 이전 대화 내용이 없어도 질문에 대한 대답을 하세요. \n"
                       f"사용자가 이전 대화 내용에 대해 물어보면, 대화 기록을 확인하여 정확히 답변해주세요."), 
            ("human", "{question}"),
            ("human", "문서:\n{documents}"),
            ("human", "이전 대화 내용:\n{chat_history}")
        ])
        
        self.rag_chain = (
            {
                "question": lambda x: x["question"],
                "documents": lambda x: self.retriever.invoke(x["question"]),
                "chat_history": lambda x: self.format_chat_history(x.get("chat_history", []))
            }
            | self.prompt_template
            | self.llm
            | StrOutputParser()
        )
        
        self.qa_chain = RunnableWithMessageHistory(
            self.rag_chain,
            get_session_history=self.get_chat_history,
            input_messages_key="question",
            history_messages_key="chat_history"
        )

    async def process_qa_request(self, question: str, session_id: str) -> str:
        """질문에 대한 답변 생성"""
        try:
            if not self.presentation_state["chat_enabled"]:
                return "프레젠테이션이 완료된 후에 질문해주세요."
                
            response = self.qa_chain.invoke(
                {"question": question},
                config={"configurable": {"session_id": session_id}}
            )
            return response
        except Exception as e:
            return f"오류 발생: {str(e)}"

    def set_presentation_complete(self):
        """프레젠테이션 완료 상태를 설정합니다."""
        self.presentation_state["is_completed"] = True
        self.presentation_state["chat_enabled"] = True

    def get_chat_status(self):
        """챗봇 활성화 상태를 확인합니다."""
        return self.presentation_state

    def get_chat_history(self, session_id: str) -> BaseChatMessageHistory:
        """세션 ID에 해당하는 대화 이력 반환"""
        if session_id not in self.chat_history_store:
            self.chat_history_store[session_id] = ChatMessageHistory()
        return self.chat_history_store[session_id]

    def format_chat_history(self, chat_history):
        """대화 이력을 문자열로 변환"""
        formatted_history = []
        for message in chat_history:
            if hasattr(message, 'content') and hasattr(message, 'type'):
                formatted_history.append(f"{message.type}: {message.content}")
        return "\n".join(formatted_history)

# 싱글톤 인스턴스 생성
chatbot_qa = ChatbotQA()