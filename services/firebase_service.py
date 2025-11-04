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

def save_question(lecture_id, question):
    """
    문제를 Firebase에 저장
    """
    user_id = session.get('user', {}).get('uid')
    if not user_id:
        print("WARNING: save_question - user_id가 없습니다.")
        return
    
    # 디버깅: 저장할 데이터 확인
    print(f"DEBUG: save_question - 저장할 문제 데이터:")
    print(f"  - Keys: {list(question.keys())}")
    print(f"  - Type: {question.get('type')}")
    print(f"  - Question: {question.get('question', '')[:50]}...")
    print(f"  - Options 존재: {'options' in question}")
    print(f"  - Options 값: {question.get('options')}")
    print(f"  - Answer: {question.get('answer')}")
    
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
    except Exception as e:
        print(f"ERROR: 문제 저장 중 오류: {str(e)}")
        import traceback
        print(traceback.format_exc())

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
