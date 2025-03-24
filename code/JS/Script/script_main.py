# main.py
from script_state import ScriptGenState
from script_generator import ScriptGenerator

def main():
    # 상태 초기화
    state = ScriptGenState()

    # 새로운 입력 추가
    state.input_text = "이 페이지에서는 AI의 기본 개념을 설명합니다."
    state.input_document = "이 문서는 AI의 역사와 개념을 설명하는 발표 자료입니다."
    state.previous_script = ["AI는 인간의 지능을 모방하는 기술입니다."]

    # 이미지 사용 여부 결정
    image_threshold = ScriptGenerator.image_area_ratio_exceeds_threshold(
        image_size=(500, 300),
        page_size=(1000, 800)
    )
    use_image = ScriptGenerator.decide_image_usage(
        state.input_document,
        state.previous_script,
        image_threshold
    )

    # 발표 대본 생성
    state.generated_script = ScriptGenerator.generate_presentation_script(
        state.input_text,
        state.input_document,
        state.previous_script,
        use_image
    )

    # 결과 출력
    print("=== 최종 발표 대본 ===")
    print(state.generated_script)

if __name__ == "__main__":
    main()
