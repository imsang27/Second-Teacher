import firebase_admin
from firebase_admin import credentials, firestore, auth
from flask import current_app, session

# Firebase 앱이 이미 초기화되어 있는지 확인
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("firebase-auth.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def verify_token(token):
    """Firebase ID 토큰을 검증합니다."""
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        current_app.logger.error(f"Token verification failed: {str(e)}")
        return None

def get_lectures():
    """
    저장된 모든 강의 목록을 조회
    """
    lectures = []
    lectures_ref = db.collection('lectures').stream()
    
    for doc in lectures_ref:
        data = doc.to_dict()
        lectures.append({
            'id': doc.id,
            'title': data.get('title', '제목 없음'),
            'description': data.get('description', '설명 없음')
        })
    
    return lectures

def get_materials(lecture_id, material_type):
    """
    특정 강의의 자료 목록을 조회
    material_type: 'pdf' 또는 'stt'
    """
    materials = []
    user_id = session.get('user', {}).get('uid')
    
    if not user_id:
        return materials
    
    # PDF 요약 자료 조회
    if material_type == 'pdf':
        summaries_ref = db.collection('pdf').document('UID').collection(user_id).stream()
        for doc in summaries_ref:
            data = doc.to_dict()
            materials.append({
                'id': doc.id,
                'title': data.get('title', data.get('file_name', '제목 없음')),  # title이 없으면 file_name 사용
                'description': data.get('summary', '내용 없음'),
                'type': 'pdf'
            })
    
    # STT 변환 자료 조회
    elif material_type == 'stt':
        stt_ref = db.collection('stt').document('UID').collection(user_id).stream()
        for doc in stt_ref:
            data = doc.to_dict()
            materials.append({
                'id': doc.id,
                'title': data.get('title', data.get('file_name', '제목 없음')),  # title이 없으면 file_name 사용
                'description': data.get('summary', '내용 없음'),  # summary 필드 사용
                'type': 'stt'
            })
    
    return materials

def get_material_content(material_id, material_type):
    """
    Firebase에서 특정 자료의 내용을 가져옴
    
    Args:
        material_id (str): 자료 ID
        material_type (str): 자료 유형 ('pdf' 또는 'stt')
        
    Returns:
        str: 자료 내용
    """
    try:
        user_id = session.get('user', {}).get('uid')
        print(f"Getting material content - ID: {material_id}, Type: {material_type}, User: {user_id}")
        
        if not user_id:
            print("No user ID found in session")
            return None
            
        if material_type == 'pdf':
            doc_ref = db.collection('pdf').document('UID').collection(user_id).document(material_id)
            doc = doc_ref.get()
            print(f"PDF document exists: {doc.exists}")
            if doc.exists:
                content = doc.to_dict().get('summary', '')
                print(f"PDF content length: {len(content)}")
                return content
        else:  # stt
            doc_ref = db.collection('stt').document('UID').collection(user_id).document(material_id)
            doc = doc_ref.get()
            print(f"STT document exists: {doc.exists}")
            if doc.exists:
                content = doc.to_dict().get('summary', '')  # summary 필드 사용
                print(f"STT content length: {len(content)}")
                return content
                
        print("Document not found or no content")
        return None
        
    except Exception as e:
        print(f"Error getting material content: {str(e)}")
        return None

def check_duplicate_question(question, user_id):
    """
    기존 문제와 중복 여부를 확인 (문제 + 보기 기준)
    
    Args:
        question (dict): 확인할 문제 데이터
        user_id (str): 사용자 ID
        
    Returns:
        tuple: (is_duplicate: bool, duplicate_question_id: str or None)
    """
    try:
        new_question_text = question.get('question', '').strip()
        new_options = question.get('options', [])
        
        if not new_question_text:
            return False, None
        
        # 기존 문제들 가져오기
        questions_ref = db.collection('questions').document('UID').collection(user_id).stream()
        
        for doc in questions_ref:
            data = doc.to_dict()
            existing_question_text = data.get('question', '').strip()
            existing_options = data.get('options', [])
            
            if not existing_question_text:
                continue
            
            # 1. 문제 텍스트가 정확히 동일한지 확인
            if new_question_text == existing_question_text:
                print(f"DEBUG: 중복 문제 발견 (문제 텍스트 동일) - 기존 문제 ID: {doc.id}")
                return True, doc.id
            
            # 2. 문제 텍스트 유사도 체크
            question_similarity = _calculate_similarity(new_question_text, existing_question_text)
            if question_similarity >= 0.8:  # 문제가 80% 이상 유사하면
                # 보기도 확인
                if new_options and existing_options:
                    # 보기들이 거의 동일한지 확인 (순서 무관)
                    new_options_set = set([str(opt).strip().lower() for opt in new_options])
                    existing_options_set = set([str(opt).strip().lower() for opt in existing_options])
                    
                    # 보기가 3개 이상 동일하면 중복으로 간주
                    common_options = new_options_set.intersection(existing_options_set)
                    if len(common_options) >= 3:
                        print(f"DEBUG: 중복 문제 발견 (문제 유사도: {question_similarity:.2f}, 보기 {len(common_options)}개 동일) - 기존 문제 ID: {doc.id}")
                        return True, doc.id
                else:
                    # 보기가 없으면 문제만으로 판단
                    print(f"DEBUG: 유사한 문제 발견 (유사도: {question_similarity:.2f}) - 기존 문제 ID: {doc.id}")
                    return True, doc.id
        
        return False, None
    except Exception as e:
        print(f"ERROR: 중복 체크 중 오류: {str(e)}")
        return False, None

def _calculate_similarity(text1, text2):
    """
    두 텍스트의 유사도를 계산 (개선된 방식)
    
    Args:
        text1 (str): 첫 번째 텍스트
        text2 (str): 두 번째 텍스트
        
    Returns:
        float: 유사도 (0.0 ~ 1.0)
    """
    if not text1 or not text2:
        return 0.0
    
    # 공백 제거 및 소문자 변환
    text1_normalized = text1.lower().strip()
    text2_normalized = text2.lower().strip()
    
    # 정확히 동일한 경우
    if text1_normalized == text2_normalized:
        return 1.0
    
    # 짧은 텍스트는 비교하지 않음 (너무 짧으면 유사도가 부정확)
    if len(text1_normalized) < 10 or len(text2_normalized) < 10:
        return 0.0
    
    # 긴 텍스트를 기준으로
    longer = text1_normalized if len(text1_normalized) > len(text2_normalized) else text2_normalized
    shorter = text2_normalized if len(text1_normalized) > len(text2_normalized) else text1_normalized
    
    # 공통 부분 문자열 찾기 (최소 3글자 이상)
    common_length = 0
    for i in range(len(shorter) - 2):
        substring = shorter[i:i+3]
        if substring in longer:
            common_length += 3
    
    # 유사도 계산 (공통 부분의 비율)
    if len(longer) == 0:
        return 1.0
    
    similarity = common_length / len(longer)
    
    # 정확히 동일한 단어가 많이 포함되어 있는지 확인
    words1 = set(text1_normalized.split())
    words2 = set(text2_normalized.split())
    
    if len(words1) > 0 and len(words2) > 0:
        common_words = words1.intersection(words2)
        word_similarity = len(common_words) / max(len(words1), len(words2))
        # 문자 유사도와 단어 유사도의 평균
        similarity = (similarity + word_similarity) / 2
    
    return similarity

def save_question(lecture_id, question):
    """
    문제를 Firebase에 저장 (중복 체크 포함)
    
    Returns:
        dict: {'success': bool, 'message': str, 'is_duplicate': bool}
    """
    user_id = session.get('user', {}).get('uid')
    if not user_id:
        print("WARNING: save_question - user_id가 없습니다.")
        return {'success': False, 'message': '사용자 인증이 필요합니다.', 'is_duplicate': False}
    
    # 디버깅: 저장할 데이터 확인
    print(f"DEBUG: save_question - 저장할 문제 데이터:")
    print(f"  - Keys: {list(question.keys())}")
    print(f"  - Type: {question.get('type')}")
    print(f"  - Question: {question.get('question', '')[:50]}...")
    print(f"  - Options 존재: {'options' in question}")
    print(f"  - Options 값: {question.get('options')}")
    print(f"  - Answer: {question.get('answer')}")
    
    # 중복 체크
    is_duplicate, duplicate_id = check_duplicate_question(question, user_id)
    if is_duplicate:
        print(f"WARNING: 중복 문제 발견 - 저장하지 않습니다.")
        return {
            'success': False,
            'message': '이미 존재하는 문제와 동일하거나 유사한 문제입니다.',
            'is_duplicate': True,
            'duplicate_id': duplicate_id
        }
    
    # 생성 시간 추가
    from firebase_admin import firestore
    question_with_timestamp = {
        **question,
        'created_at': firestore.SERVER_TIMESTAMP
    }
    
    # 저장
    try:
        # Firestore의 add()는 문서 참조를 반환
        doc_ref = db.collection('questions').document('UID').collection(user_id).add(question_with_timestamp)
        doc_id = doc_ref[1].id  # add()는 (timestamp, document_reference) 튜플 반환
        
        print(f"DEBUG: 문제 저장 완료 - 문서 ID: {doc_id}")
        
        # 저장된 데이터 확인
        saved_doc = db.collection('questions').document('UID').collection(user_id).document(doc_id).get()
        if saved_doc.exists:
            saved_data = saved_doc.to_dict()
            print(f"DEBUG: 저장된 데이터 확인:")
            print(f"  - Keys: {list(saved_data.keys())}")
            print(f"  - Type: {saved_data.get('type')}")
            print(f"  - Options 존재: {'options' in saved_data}")
            print(f"  - Options 값: {saved_data.get('options')}")
        else:
            print(f"WARNING: 저장된 문서를 찾을 수 없습니다. ID: {doc_id}")
        
        return {
            'success': True,
            'message': '문제가 저장되었습니다.',
            'is_duplicate': False,
            'question_id': doc_id
        }
    except Exception as e:
        print(f"ERROR: 문제 저장 중 오류: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'success': False,
            'message': f'문제 저장 중 오류가 발생했습니다: {str(e)}',
            'is_duplicate': False
        }

def get_questions():
    """
    사용자의 저장된 모든 문제 목록을 조회
    """
    questions = []
    user_id = session.get('user', {}).get('uid')
    
    if not user_id:
        return questions
    
    try:
        questions_ref = db.collection('questions').document('UID').collection(user_id).stream()
        for doc in questions_ref:
            data = doc.to_dict()
            question_data = {
                'id': doc.id,
                'question': data.get('question', '문제 내용 없음'),
                'type': data.get('type', 'multiple'),
                'answer': data.get('answer', ''),
                'created_at': data.get('created_at', None)
            }
            
            # 객관식 문제인 경우 보기 추가
            if 'options' in data:
                question_data['options'] = data['options']
            
            questions.append(question_data)
        
        # 생성일시 기준으로 정렬 (최신순)
        questions.sort(key=lambda x: x.get('created_at') or '', reverse=True)
        
    except Exception as e:
        print(f"Error getting questions: {str(e)}")
    
    return questions
