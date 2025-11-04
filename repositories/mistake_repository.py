from firebase_admin import firestore
from datetime import datetime

class MistakeRepository:
    def __init__(self):
        self.db = firestore.client()
    
    def save_mistake(self, user_id, mistake_data):
        """
        오답 노트에 오답 문제 저장
        mistake_data 구조:
        {
            'question_id': str,
            'lecture_id': str,
            'question_type': str,  # 'short' or 'multiple'
            'question_text': str,
            'user_answer': str,
            'correct_answer': str,
            'options': list (optional),
            'exam_date': datetime
        }
        """
        mistake_data['created_at'] = firestore.SERVER_TIMESTAMP
        mistake_data['exam_date'] = mistake_data.get('exam_date', firestore.SERVER_TIMESTAMP)
        
        mistake_ref = self.db.collection('users').document(user_id).collection('mistakes')
        mistake_ref.add(mistake_data)
    
    def get_user_mistakes(self, user_id, limit=None):
        """
        사용자의 모든 오답 노트 조회
        """
        mistakes_ref = self.db.collection('users').document(user_id).collection('mistakes')
        query = mistakes_ref.order_by('exam_date', direction=firestore.Query.DESCENDING)
        
        if limit:
            query = query.limit(limit)
        
        mistakes = []
        for doc in query.stream():
            mistake_data = doc.to_dict()
            mistake_data['id'] = doc.id
            mistakes.append(mistake_data)
        
        return mistakes
    
    def get_mistake_by_question(self, user_id, question_id):
        """
        특정 문제에 대한 사용자의 오답 기록 조회
        """
        mistakes_ref = self.db.collection('users').document(user_id).collection('mistakes')
        query = mistakes_ref.where('question_id', '==', question_id).order_by('exam_date', direction=firestore.Query.DESCENDING)
        
        mistakes = []
        for doc in query.stream():
            mistake_data = doc.to_dict()
            mistake_data['id'] = doc.id
            mistakes.append(mistake_data)
        
        return mistakes
    
    def get_mistake_statistics(self, user_id):
        """
        사용자의 오답 통계 정보 조회
        """
        mistakes = self.get_user_mistakes(user_id)
        
        if not mistakes:
            return {
                'total_mistakes': 0,
                'by_type': {'short': 0, 'multiple': 0},
                'by_lecture': {},
                'most_mistaken_questions': []
            }
        
        stats = {
            'total_mistakes': len(mistakes),
            'by_type': {'short': 0, 'multiple': 0},
            'by_lecture': {},
            'question_mistake_count': {}
        }
        
        for mistake in mistakes:
            # 유형별 통계
            question_type = mistake.get('question_type', 'short')
            stats['by_type'][question_type] = stats['by_type'].get(question_type, 0) + 1
            
            # 강의별 통계
            lecture_id = mistake.get('lecture_id', 'unknown')
            stats['by_lecture'][lecture_id] = stats['by_lecture'].get(lecture_id, 0) + 1
            
            # 문제별 오답 횟수
            question_id = mistake.get('question_id')
            if question_id:
                stats['question_mistake_count'][question_id] = stats['question_mistake_count'].get(question_id, 0) + 1
        
        # 가장 많이 틀린 문제 상위 5개
        sorted_mistakes = sorted(
            stats['question_mistake_count'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        stats['most_mistaken_questions'] = [
            {'question_id': qid, 'mistake_count': count}
            for qid, count in sorted_mistakes
        ]
        
        return stats

