from services.gemini_service import GeminiService
import traceback

def generate_question(text, existing_questions=None):
    """
    Gemini API를 사용하여 주어진 텍스트로부터 문제를 생성
    
    Args:
        text (str): 문제를 생성할 텍스트
        existing_questions (list): 기존 문제 목록 (중복 방지용)
        
    Returns:
        dict: 생성된 문제 정보
    """
    try:
        # 텍스트가 비어있는지 확인
        if not text or len(text.strip()) == 0:
            print("ERROR: 텍스트가 비어있습니다.")
            return None
            
        print(f"DEBUG: 문제 생성 시작 - 텍스트 길이: {len(text)}")
        if existing_questions:
            print(f"DEBUG: 기존 문제 {len(existing_questions)}개를 참고하여 새로운 문제 생성")
        
        # Gemini 서비스 초기화
        try:
            gemini_service = GeminiService()
            print("DEBUG: Gemini 서비스 초기화 성공")
        except Exception as e:
            print(f"ERROR: Gemini 서비스 초기화 실패: {str(e)}")
            print(traceback.format_exc())
            return None
        
        # Gemini API를 사용하여 문제 생성
        print("DEBUG: Gemini API 호출 시작")
        questions = gemini_service.generate_question(text, existing_questions=existing_questions)
        
        if not questions:
            print("ERROR: Gemini API가 None을 반환했습니다.")
            return None
        
        print(f"DEBUG: 문제 생성 성공 - question: {questions.get('question', 'N/A')[:50]}...")
        # 생성된 문제 반환
        return questions
            
    except Exception as e:
        print(f"ERROR: 문제 생성 중 예외 발생: {str(e)}")
        print(traceback.format_exc())
        return None
