from gradio_client import Client
from scipy.io.wavfile import write as write_wav
import numpy as np
import soundfile as sf  # for saving the audio
import numpy as np
# 1. Gradio 앱 URL (예: 로컬 또는 share URL)
client = Client("http://localhost:7860")  # 또는 "https://xxxx.gradio.live"

# 2. generate_audio에 맞게 입력값 설정
result = client.predict(
    "Zyphra/Zonos-v0.1-transformer",  # model_choice
    "안녕하세요. 반갑습니다. 오늘 수업할 내용을 말씀드리겠습니다.",            # text
    "ko",                          # language
    None,                             # speaker_audio (None = 사용 안 함)
    None,                             # prefix_audio (None = 사용 안 함)
    1.0, 0.05, 0.05, 0.05, 0.05, 0.05, 0.1, 0.2,  # emotion sliders
    0.78,                             # vq_single
    24000,                            # fmax
    45.0,                             # pitch_std
    15.0,                             # speaking_rate
    4.0,                              # dnsmos
    False,                            # speaker_noised
    2.0,                              # cfg_scale
    0,                              # top_p
    0,                                # top_k (min_k로 전달됨)
    0,                              # min_p
    0.5, 0.4, 0.0,                    # linear, confidence, quadratic
    42,                               # seed
    False,                            # randomize_seed
    ["emotion"],                     # unconditional_keys
    api_name="/generate_audio"              # 예: 함수가 자동 등록된 이름
)


import shutil

src = result[0]
dst = "test.wav"

shutil.copyfile(src, dst)
