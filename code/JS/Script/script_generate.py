# script_generator.py
import openai

class ScriptGenerator:
    """발표 대본 생성 관련 기능을 제공하는 클래스"""

    @staticmethod
    def image_area_ratio_exceeds_threshold(image_size: tuple, page_size: tuple, threshold: float = 0.5) -> bool:
        """
        이미지 크기와 페이지 크기를 비교하여 특정 임계치를 초과하는지 확인
        """
        image_area = image_size[0] * image_size[1]
        page_area = page_size[0] * page_size[1]
        
        if page_area == 0:
            return False  # 페이지 크기가 0이면 오류 방지
        
        image_ratio = image_area / page_area
        return image_ratio >= threshold

    @staticmethod
    def decide_image_usage(input_document: str, previous_script: list, image_threshold: bool) -> bool:
        """
        GPT-4V를 사용하여 발표 대본에 이미지 사용 여부를 결정
        """
        prompt = f"""
        다음은 발표 자료에 대한 정보입니다:
        - PPT 관련 문서: {input_document}
        - 이전 발표 대본: {previous_script}
        - 이미지 비율이 임계치를 초과하는가?: {'Yes' if image_threshold else 'No'}
        
        발표 대본을 생성할 때, 시각적 자료(이미지)가 필수적인지 판단해주세요. 
        이미지가 필요하면 'True', 필요하지 않으면 'False'를 반환하세요.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {"role": "system", "content": "당신은 발표 자료 최적화를 돕는 AI입니다."},
                {"role": "user", "content": prompt}
            ]
        )
        
        result = response["choices"][0]["message"]["content"].strip()
        return result.lower() == "true"

    @staticmethod
    def generate_presentation_script(input_text: str, input_document: str, previous_script: list, use_image: bool) -> str:
        """
        GPT-4를 사용하여 페이지별 발표 대본을 생성하는 메서드
        """
        prompt = f"""
        다음은 발표 자료에 대한 정보입니다:
        - 현재 페이지 텍스트: {input_text}
        - 전체 문서 정보: {input_document}
        - 이전 발표 대본: {previous_script}
        - 이미지 사용 여부: {'Yes' if use_image else 'No'}
        
        위 정보를 바탕으로 발표자가 자연스럽게 발표할 수 있도록 대본을 작성해주세요.
        발표 대본은 논리적인 흐름을 유지하고, 강조해야 할 핵심 내용을 포함해야 합니다.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 발표 대본을 작성하는 AI입니다."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response["choices"][0]["message"]["content"].strip()
