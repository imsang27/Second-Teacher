from firebase_admin import firestore

class QuestionRepository:
    def __init__(self):
        self.db = firestore.client()
    
    def get_all_questions(self):
        """
        lectures/{lecture_id}/questions/ 경로에서 모든 문제를 가져옴 시험시에 사용 
        """
        questions = []
        
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
        
        return questions
    
    def get_questions_by_ids(self, question_ids):
        """
        lectures/{lecture_id}/questions/{question_id} 경로에서 특정 ID의 문제들을 가져옴 채점시에 사용 
        """
        questions = []
        
        for question_id in question_ids:
            found = False
            lecture_refs = self.db.collection('lectures').stream()
            
            for lecture_ref in lecture_refs:
                lecture_id = lecture_ref.id
                question_doc = self.db.collection('lectures').document(lecture_id).collection('questions').document(question_id).get()
                
                if question_doc.exists:
                    question_data = question_doc.to_dict()
                    question_data['id'] = question_id
                    
                    formatted_question = {
                        'id': question_data['id'],
                        'type': question_data.get('type', 'short'),
                        'question': question_data.get('question', '문제 내용 없음'),
                        'answer': question_data.get('answer', '')
                    }
                    
                    if question_data.get('type') == 'multiple' and 'options' in question_data:
                        formatted_question['options'] = question_data['options']
                    
                    formatted_question['lecture_id'] = lecture_id
                    questions.append(formatted_question)
                    found = True
                    break
        
        return questions
    
    def get_question_with_lecture(self, question_id):
        """
        문제 ID로 문제와 강의 정보를 함께 가져옴
        """
        lecture_refs = self.db.collection('lectures').stream()
        
        for lecture_ref in lecture_refs:
            lecture_id = lecture_ref.id
            question_doc = self.db.collection('lectures').document(lecture_id).collection('questions').document(question_id).get()
            
            if question_doc.exists:
                question_data = question_doc.to_dict()
                question_data['id'] = question_id
                question_data['lecture_id'] = lecture_id
                return question_data
        
        return None