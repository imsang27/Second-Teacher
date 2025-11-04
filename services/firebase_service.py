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
        return
    
    db.collection('questions').document('UID').collection(user_id).add(question)
