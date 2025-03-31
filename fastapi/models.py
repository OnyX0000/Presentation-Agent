from langchain.memory import ConversationSummaryMemory
from langchain.chains import ConversationChain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional, List
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from dotenv import load_dotenv
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from google.cloud import texttospeech_v1 as tts

import os

load_dotenv("../.env")

image_model_params = {
    "model": "gpt-4o-mini",
    "temperature": 0.3,
    "max_tokens": 1024,
    "timeout": 60,
}

page_script_model_params = {
    "model": "gpt-4o-mini",
    "temperature": 0.3,
    "timeout": 60,
}

chat_model_params = {
    "model": "gpt-4o-mini",
    "temperature": 0.0,
    # "max_tokens": 1024,
    "timeout": 60,
}

class GPTModel():
    """LLM 모델 생성 클래스"""
    def __init__(self, prompt_path, output_parser, model_params, use_memory=False):
        self.prompt_path = prompt_path
        self.llm = ChatOpenAI(**model_params)
        self.output_parser = output_parser
        self.use_memory = use_memory
        self.memory = None
        self.chain = self._make_chain()

    def _make_chain(self):
        if self.use_memory:
            self.memory = ConversationSummaryMemory(llm=self.llm, return_messages=True)
            return ConversationChain(llm=self.llm, memory=self.memory)
        else:
            return self.llm | self.output_parser

    def _get_template(self):
        prompt_abs_path = Path(__file__).parent / self.prompt_path
        with open(prompt_abs_path, "r", encoding="utf-8") as f:
            template = f.read()
        return template

    def _set_prompt(self, **inputs):
        # 자식 클래스에서 오버라이드
        pass

    def invoke(self, inputs):
        prompt = self._set_prompt(inputs)
        if self.use_memory:
            response = self.chain.run(prompt)
        else:
            response = self.chain.invoke(prompt)
        return response

class ImageDescriptAI(GPTModel):
    def __init__(self, prompt_path, output_parser, model_params, use_memory=False):
        super().__init__(prompt_path, output_parser, model_params, use_memory)

    def _set_prompt(self, inputs):
        inputs["format_instructions"] = self.output_parser.get_format_instructions()
        template = self._get_template().format(**inputs)

        prompt = [
            HumanMessage(
                content=[
                    {"type": "text", "text": template},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64, {inputs['image_base64']}"},
                    },
                ]
            )
        ]
        return prompt

class PageScriptAI(GPTModel):
    def __init__(self, prompt_paths: dict, output_parser, model_params, use_memory=True):
        self.prompt_paths = prompt_paths
        super().__init__(None, output_parser, model_params, use_memory)

    def _get_template(self, page_type="body"):
        path = Path(__file__).parent / self.prompt_paths[page_type]
        with open(path, "r", encoding="utf-8") as f:
            template = f.read()
        return template

    def _set_prompt(self, inputs):
        page_idx = inputs.get("page", 1)
        total_pages = inputs.get("total_pages", 1)

        if page_idx == 1:
            page_type = "head"
        elif page_idx == total_pages:
            page_type = "end"
        else:
            page_type = "body"

        prompt = self._get_template(page_type).format(**inputs)

        return prompt

class ImageCategory(BaseModel):
    is_chart: bool = Field(..., description="데이터 관련 이미지 여부 (True/False)")  
    description: str = Field("", description="이미지에 대한 설명")

class ChatRequest(BaseModel):
    question: str
    session_id: str

class ChatResponse(BaseModel):
    answer: str
    
class PresentationState(BaseModel):
    is_completed: bool = Field(default=False)
    chat_enabled: bool = Field(default=False)

class PageScript(BaseModel):
    page: int
    script: str

class QAEnableRequest(BaseModel):
    full_document: str
    script_data: list[PageScript]

class Chatbot:
    """챗봇 모델 생성 클래스"""
    def __init__(self, prompt_path, output_parser, model_params,db_path):
        self.prompt_path = prompt_path
        self.embeddings = OpenAIEmbeddings()
        self.output_parser = output_parser
        self.retriever = self._init_retriever(db_path)
        self.llm = ChatOpenAI(**model_params)
        self.chat_history_store = {}
        self.prompt_template: Optional[ChatPromptTemplate] = None
        self.chain = None

    def _init_retriever(self, db_path):
        db = Chroma(persist_directory=db_path, embedding_function=self.embeddings)
        return db.as_retriever(search_kwargs={"k": 3})

    def get_template(self, system_context: str) -> ChatPromptTemplate:
        """프롬프트 파일을 불러와 system message로 구성"""
        from string import Template
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            # 프롬프트 내부에 ${context}를 사용하는 Template 객체 생성
            system_prompt_template = Template(f.read())
            # 실제 context를 채워 넣은 system prompt 생성
            system_prompt = system_prompt_template.safe_substitute(context=system_context)

        # 'context'는 이미 치환되었으므로 입력 변수에서 제거
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}"),
            ("human", "문서:\n{documents}"),
            ("human", "이전 대화 내용:\n{chat_history}")
        ])

        self.prompt_template = prompt
        return prompt


    def _make_chain(self):
        """PromptTemplate + LLM + 출력 파서 연결"""
        self.chain = (
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
            self.chain,
            get_session_history=self.get_chat_history,
            input_messages_key="question",
            history_messages_key="chat_history"
        )

    def invoke(self, question: str, session_id: str) -> str:
        if not self.qa_chain:
            return "체인이 준비되지 않았습니다. system_context를 먼저 설정해주세요."

        try:
            return self.qa_chain.invoke(
                {"question": question},
                config={"configurable": {"session_id": session_id}}
            )
        except Exception as e:
            return f"오류 발생: {str(e)}"

    def get_chat_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.chat_history_store:
            self.chat_history_store[session_id] = ChatMessageHistory()
        return self.chat_history_store[session_id]

    def format_chat_history(self, chat_history):
        formatted = []
        for m in chat_history:
            if hasattr(m, "type") and hasattr(m, "content"):
                formatted.append(f"{m.type}: {m.content}")
        return "\n".join(formatted)

class TTS_LLM:
    def __init__(self, voice_name):

        self.client = tts.TextToSpeechClient()
        self.voice = tts.VoiceSelectionParams(
            language_code="ko-KR",
            name=voice_name
        )
        self.audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)
    
    def _response(self, text: str):
        response = self.client.synthesize_speech(
            input=tts.SynthesisInput(ssml=text),
            voice=self.voice,
            audio_config=self.audio_config
        )
        return response
    
MAN_TTS = TTS_LLM(voice_name="ko-KR-Wavenet-C")
WOMAN_TTS = TTS_LLM(voice_name="ko-KR-Wavenet-A")

VISION_LLM  = ImageDescriptAI(
    prompt_path="prompts/image_script.prompt",
    output_parser=PydanticOutputParser(pydantic_object=ImageCategory),
    model_params=image_model_params,
    use_memory=False
)

PAGE_SCRIPT_LLM = PageScriptAI(
    prompt_paths={
        "head": "prompts/head_script.prompt",
        "body": "prompts/body_script.prompt",
        "end": "prompts/end_script.prompt"
    },
    output_parser=StrOutputParser(),
    model_params=page_script_model_params,
    use_memory=True
)

CHATBOT_LLM = Chatbot(
    prompt_path="prompts/chatbot.prompt",
    output_parser=StrOutputParser(),
    model_params=chat_model_params,
    db_path=os.path.join(os.path.dirname(__file__), "../../data/db/chromadb/split_knowledge")
)