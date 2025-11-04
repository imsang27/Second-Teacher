from firebase_admin import firestore
from datetime import datetime

class ExamHistoryRepository:
    def __init__(self):
        self.db = firestore.client()
    
    def save_exam_result(self, user_id, exam_data):
        """
        시험 결과 전체를 저장
        exam_data 구조:
        {
            'total_questions': int,
            'correct_count': int,
            'short_answer_total': int,
            'short_answer_correct': int,
            'multiple_choice_total': int,
            'multiple_choice_correct': int,
            'questions': list,  # 문제 정보
            'user_answers': list,  # 사용자 답안
            'results': list,  # 채점 결과
            'exam_date': datetime
        }
        """
        exam_data['created_at'] = firestore.SERVER_TIMESTAMP
        exam_data['exam_date'] = exam_data.get('exam_date', firestore.SERVER_TIMESTAMP)
        
        exam_ref = self.db.collection('users').document(user_id).collection('exam_history')
        exam_ref.add(exam_data)
    
    def get_user_exam_history(self, user_id, limit=None):
        """
        사용자의 모든 시험 기록 조회
        """
        exam_ref = self.db.collection('users').document(user_id).collection('exam_history')
        query = exam_ref.order_by('exam_date', direction=firestore.Query.DESCENDING)
        
        if limit:
            query = query.limit(limit)
        
        exams = []
        for doc in query.stream():
            exam_data = doc.to_dict()
            exam_data['id'] = doc.id
            exams.append(exam_data)
        
        return exams
    
    def get_exam_by_id(self, user_id, exam_id):
        """
        특정 시험 기록 조회
        """
        exam_doc = self.db.collection('users').document(user_id).collection('exam_history').document(exam_id).get()
        
        if exam_doc.exists:
            exam_data = exam_doc.to_dict()
            exam_data['id'] = exam_id
            return exam_data
        
        return None
    
    def get_exam_statistics(self, user_id):
        """
        사용자의 시험 통계 정보 조회
        """
        exams = self.get_user_exam_history(user_id)
        
        if not exams:
            return {
                'total_exams': 0,
                'average_score': 0,
                'best_score': 0,
                'latest_exam_date': None
            }
        
        total_score = 0
        best_score = 0
        latest_date = None
        
        for exam in exams:
            total_questions = exam.get('total_questions', 0)
            correct_count = exam.get('correct_count', 0)
            
            if total_questions > 0:
                score = (correct_count / total_questions) * 100
                total_score += score
                best_score = max(best_score, score)
            
            exam_date = exam.get('exam_date')
            if exam_date:
                if latest_date is None or exam_date > latest_date:
                    latest_date = exam_date
        
        return {
            'total_exams': len(exams),
            'average_score': round(total_score / len(exams), 2) if exams else 0,
            'best_score': round(best_score, 2),
            'latest_exam_date': latest_date
        }

