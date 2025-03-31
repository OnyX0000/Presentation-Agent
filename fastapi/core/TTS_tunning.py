from pathlib import Path
from models import embedding_model
from sklearn.metrics.pairwise import cosine_similarity
from google.cloud import texttospeech_v1 as tts
import re
import base64
import os

class TTSEngine:
    def __init__(self, audio_dir: str = "../data/audio", voice_name: str = "ko-KR-Standard-B"):
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        self.client = tts.TextToSpeechClient()
        self.voice = tts.VoiceSelectionParams(
            language_code="ko-KR",
            name=voice_name
        )
        self.audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)
        self.embedder = embedding_model()

    def get_top_keywords(self, script: str, input_keywords: list[str], top_k: int = 10) -> list[str]:
        words = sorted(set(re.findall(r'\w+', script)))
        word_embeddings = self.embedder.embed_documents(words)
        keyword_embeddings = [self.embedder.embed_query(k) for k in input_keywords]

        word_sims = {
            word: max([cosine_similarity([w_emb], [k_emb])[0][0] for k_emb in keyword_embeddings])
            for word, w_emb in zip(words, word_embeddings)
        }
        top_words = sorted(word_sims.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [word for word, _ in top_words]

    def apply_ssml_transformations(self, word: str, emphasized_words: list[str], special_tokens: list[str]) -> str:
        # 대문자 단어 처리 (예: API, HTML)
        if word in special_tokens:
            return f'<say-as interpret-as="characters">{word}</say-as>'
        # 강조 키워드 처리
        elif word in emphasized_words:
            return f'<break time="300ms"/><prosody pitch="+15%" rate="-5%" volume="+3dB"><emphasis level="moderate">{word}</emphasis></prosody>'
        return word

    def build_ssml(self, text: str, emphasized_words: list[str]) -> str:
        # 대문자 단어 자동 탐지 (2자 이상)
        special_tokens = sorted(set(re.findall(r'\b[A-Z]{2,}\b', text)))
        print(f"🔎 철자 읽기 대상 대문자 단어: {special_tokens}")

        words = re.split(r'(\W+)', text)  # 단어 + 구두점 분리
        processed = [
            self.apply_ssml_transformations(w, emphasized_words, special_tokens)
            for w in words
        ]
        return f"<speak>{''.join(processed).strip()}</speak>"

    def synthesize_pages(self, pages: dict[str, str], keywords: list[str]) -> dict[str, str]:
        print("🛠️ synthesize_speech_from_pages 시작")
        full_text = " ".join(pages.values())
        emphasized = self.get_top_keywords(full_text, keywords)

        results = {}
        for page, script in pages.items():
            print(f"🎙️ 페이지 {page} 음성 생성 시작")
            try:
                ssml = self.build_ssml(script, emphasized)
                response = self.client.synthesize_speech(
                    input=tts.SynthesisInput(ssml=ssml),
                    voice=self.voice,
                    audio_config=self.audio_config
                )
                wav_path = self.audio_dir / f"page_{page}.wav"
                with open(wav_path, "wb") as f:
                    f.write(response.audio_content)

                results[page] = base64.b64encode(response.audio_content).decode("utf-8")
                print(f"✅ 페이지 {page} 음성 생성 완료")
            except Exception as e:
                print(f"❌ TTS 생성 중 예외 발생: {e}")
        return results

    def clear_audio_dir(self):
        """이전 WAV 파일 제거"""
        for f in self.audio_dir.glob("*.wav"):
            f.unlink()
        print("🧹 기존 오디오 파일 제거 완료")