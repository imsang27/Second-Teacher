from firebase_admin import firestore

class QuestionRepository:
    def __init__(self):
        self.db = firestore.client()
    
    def get_all_questions(self, user_id=None):
        """
        사용자의 저장된 모든 문제를 가져옴 (시험시에 사용)
        
        Args:
            user_id (str): 사용자 ID. 제공되면 해당 사용자의 문제만 가져옴
        """
        questions = []
        
        # 사용자별 저장된 문제 경로 (questions/UID/{user_id}/)
        if user_id:
            try:
                questions_ref = self.db.collection('questions').document('UID').collection(user_id).stream()
                for doc in questions_ref:
                    data = doc.to_dict()
                    
                    # 디버깅: 원본 데이터 확인
                    print(f"DEBUG: 원본 문제 데이터 - ID: {doc.id}, Keys: {list(data.keys())}")
                    print(f"DEBUG: type: {data.get('type')}, options 존재: {'options' in data}, options 값: {data.get('options')}")
                    
                    formatted_question = {
                        'id': doc.id,
                        'type': data.get('type', 'multiple'),
                        'text': data.get('question', '문제 내용 없음'),
                        'answer': data.get('answer', '')
                    }
                    
                    # 객관식 문제인 경우 options 추가 (type이 multiple이거나 options가 있으면)
                    question_type = data.get('type', 'multiple')
                    if question_type == 'multiple' or 'options' in data:
                        if 'options' in data:
                            formatted_question['options'] = data['options']
                        else:
                            # options가 없으면 빈 배열 추가 (에러 방지)
                            print(f"WARNING: 문제 {doc.id}에 options 필드가 없습니다. 빈 배열로 설정합니다.")
                            formatted_question['options'] = []
                    
                    # 디버깅: 포맷된 문제 데이터 확인
                    print(f"DEBUG: 포맷된 문제 - ID: {formatted_question.get('id')}, Type: {formatted_question.get('type')}, Options: {formatted_question.get('options')}")
                    
                    questions.append(formatted_question)
            except Exception as e:
                print(f"Error getting user questions: {str(e)}")
                import traceback
                print(traceback.format_exc())
        
        # 기존 lectures 경로에서도 문제 가져오기 (하위 호환성)
        try:
            lecture_refs = self.db.collection('lectures').stream()
            
            for lecture_ref in lecture_refs:
                lecture_id = lecture_ref.id
                
                question_refs = self.db.collection('lectures').document(lecture_id).collection('questions').stream()
                
                for question_ref in question_refs:
                    question_data = question_ref.to_dict()
                    question_data['id'] = question_ref.id
                    
                    formatted_question = {
                        'id': question_data['id'],
                        'type': question_data.get('type', 'short'),
                        'text': question_data.get('question', '문제 내용 없음'),
                        'answer': question_data.get('answer', '')
                    }
                    
                    if question_data.get('type') == 'multiple' and 'options' in question_data:
                        formatted_question['options'] = question_data['options']
                    
                    questions.append(formatted_question)
        except Exception as e:
            print(f"Error getting lecture questions: {str(e)}")
        
        return questions
    
    def get_questions_by_ids(self, question_ids, user_id=None):
        """
        특정 ID의 문제들을 가져옴 (채점시에 사용)
        
        Args:
            question_ids (list): 문제 ID 리스트
            user_id (str): 사용자 ID. 제공되면 해당 사용자의 문제만 검색
        """
        questions = []
        
        for question_id in question_ids:
            found = False
            
            # 사용자별 저장된 문제 경로에서 먼저 검색 (questions/UID/{user_id}/)
            if user_id:
                try:
                    question_doc = self.db.collection('questions').document('UID').collection(user_id).document(question_id).get()
                    
                    if question_doc.exists:
                        question_data = question_doc.to_dict()
                        formatted_question = {
                            'id': question_id,
                            'type': question_data.get('type', 'multiple'),
                            'text': question_data.get('question', '문제 내용 없음'),  # text 필드로 통일
                            'answer': question_data.get('answer', '')
                        }
                        
                        if question_data.get('type') == 'multiple' and 'options' in question_data:
                            formatted_question['options'] = question_data['options']
                        
                        questions.append(formatted_question)
                        found = True
                except Exception as e:
                    print(f"Error getting question from user questions: {str(e)}")
            
            # 기존 lectures 경로에서도 검색 (하위 호환성)
            if not found:
                try:
                    lecture_refs = self.db.collection('lectures').stream()
                    
                    for lecture_ref in lecture_refs:
                        lecture_id = lecture_ref.id
                        question_doc = self.db.collection('lectures').document(lecture_id).collection('questions').document(question_id).get()
                        
                        if question_doc.exists:
                            question_data = question_doc.to_dict()
                            formatted_question = {
                                'id': question_id,
                                'type': question_data.get('type', 'short'),
                                'text': question_data.get('question', '문제 내용 없음'),  # text 필드로 통일
                                'answer': question_data.get('answer', '')
                            }
                            
                            if question_data.get('type') == 'multiple' and 'options' in question_data:
                                formatted_question['options'] = question_data['options']
                            
                            questions.append(formatted_question)
                            found = True
                            break
                except Exception as e:
                    print(f"Error getting question from lectures: {str(e)}")
        
        return questions