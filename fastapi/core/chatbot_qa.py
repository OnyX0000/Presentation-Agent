from dotenv import load_dotenv
from langchain.storage import InMemoryStore
from langchain_community.document_loaders import TextLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.retrievers import ParentDocumentRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_openai import ChatOpenAI

# API 키 정보 로드
load_dotenv(r'C:\Users\user\Documents\GitHub\Presentation-Agent\.env')

# 텍스트 분할기 설정
parent_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, 
    chunk_overlap=250, 
    separators=['==================================================', '---.*?---', '===.*?===']
)
child_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500, 
    chunk_overlap=100
)

# 벡터 저장소 설정
vectorstore = Chroma(
    collection_name="split_knowledge", 
    embedding_function=OpenAIEmbeddings(),
    persist_directory=r"C:\Users\user\Documents\GitHub\Presentation-Agent\data\db\chromadb\split_knowledge"
)

# 부모 문서 저장소 설정
parent_store = InMemoryStore()

# 검색기 설정
retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    docstore=parent_store,
    child_splitter=child_splitter,
    parent_splitter=parent_splitter,
)

# LLM 설정
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 시스템 프롬프트 로드
with open("C:/Users/user/Documents/GitHub/Presentation-Agent/data/txt/pt_context.txt", encoding="utf-8") as f:
    system_context = f.read()

# 프롬프트 템플릿 설정
prompt_template = ChatPromptTemplate.from_messages([
    ("system", f"당신은 발표자료에 대한 내용을 질문받으면 그에 대한 답을 하는 AI 에이전트입니다.\n"
               f"다음은 발표자료에 대한 배경 정보입니다:\n\n{system_context}\n\n"
               f"답변은 간결하게 100토큰 이내로만 작성해주세요.\n"
               f"사용자가 처음 물어봐서 이전 대화 내용이 없어도 질문에 대한 대답을 하세요. \n"
               f"사용자가 이전 대화 내용에 대해 물어보면, 대화 기록을 확인하여 정확히 답변해주세요."), 
    ("human", "{question}"),
    ("human", "문서:\n{documents}"),
    ("human", "이전 대화 내용:\n{chat_history}")
])

# 대화 이력 저장소
chat_history_store = {}

def get_chat_history(session_id: str) -> BaseChatMessageHistory:
    """세션 ID에 해당하는 대화 이력 반환"""
    if session_id not in chat_history_store:
        chat_history_store[session_id] = ChatMessageHistory()
    return chat_history_store[session_id]

def format_chat_history(chat_history):
    """대화 이력을 문자열로 변환"""
    formatted_history = []
    for message in chat_history:
        if hasattr(message, 'content') and hasattr(message, 'type'):
            formatted_history.append(f"{message.type}: {message.content}")
    return "\n".join(formatted_history)

# RAG 체인 구성
rag_chain = (
    {
        "question": lambda x: x["question"],
        "documents": lambda x: retriever.invoke(x["question"]),
        "chat_history": lambda x: format_chat_history(x.get("chat_history", []))
    }
    | prompt_template
    | llm
    | StrOutputParser()
)

# RAG + 메모리 체인 구성
qa_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history=get_chat_history,
    input_messages_key="question",
    history_messages_key="chat_history"
)

async def process_qa_request(question: str, session_id: str) -> str:
    """질문에 대한 답변 생성"""
    try:
        response = qa_chain.invoke(
            {"question": question},
            config={"configurable": {"session_id": session_id}}
        )
        return response
    except Exception as e:
        return f"오류 발생: {str(e)}"