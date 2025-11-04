from repositories.question_repository import QuestionRepository
from repositories.mistake_repository import MistakeRepository
from firebase_admin import firestore
from datetime import datetime
import random

class ExamService:
    def __init__(self):
        self.question_repo = QuestionRepository()
        self.mistake_repo = MistakeRepository()
        self.db = firestore.client()
    
    def get_random_questions(self, short_answer_count, multiple_choice_count):
        """
        지정된 유형별 개수에 맞춰 문제를 랜덤하게 가져옴
        """
        all_questions = self.question_repo.get_all_questions()
        
        short_questions = [q for q in all_questions if q['type'] == 'short']
        multiple_questions = [q for q in all_questions if q['type'] == 'multiple']
        
        selected_short = random.sample(short_questions, min(short_answer_count, len(short_questions)))
        selected_multiple = random.sample(multiple_questions, min(multiple_choice_count, len(multiple_questions)))
        
        # 부족한 문제는 빈칸 문제로 채우기
        while len(selected_short) < short_answer_count:
            selected_short.append(self._create_blank_question('short', len(selected_short)))
            
        while len(selected_multiple) < multiple_choice_count:
            selected_multiple.append(self._create_blank_question('multiple', len(selected_multiple)))
        
        selected_questions = selected_short + selected_multiple
        
        random.shuffle(selected_questions)
        
        return selected_questions
    
    def grade_exam(self, user_id, question_ids, answers):
        """
        시험 답안을 채점하고 오답 노트에 저장
        """
        results = []
        questions = self.question_repo.get_questions_by_ids(question_ids)
        
        question_dict = {q['id']: q for q in questions}
        mistakes = []  # 오답만 저장할 리스트
        
        for i, (answer, question_id) in enumerate(zip(answers, question_ids)):
            question = question_dict.get(question_id)
            
            if not question:
                results.append({
                    'question_id': question_id,
                    'is_correct': False,
                    'message': '문제를 찾을 수 없습니다.'
                })
                continue
            
             # 명확한 채점 결과 생성
            if question['type'] == 'short':
                     is_correct = self._grade_short_answer(answer, question['answer'])
            elif question['type'] == 'multiple':
            # 정수 변환을 통한 일관된 비교
                 try:
                     user_int = int(answer) if answer is not None else None
                     correct_int = int(question['answer']) if question['answer'] is not None else None
                     is_correct = user_int == correct_int
                 except:
                     is_correct = answer == question['answer']
            else:
                is_correct = False
            
            results.append({
                 'question_id': question_id,
                 'is_correct': bool(is_correct),
                 'correct_answer': question['answer']
            })
            
            # 오답인 경우 오답 노트에 저장
            if not is_correct:
                # question 필드명이 일관되지 않을 수 있으므로 둘 다 확인
                question_text = question.get('question') or question.get('text', '문제 내용 없음')
                
                mistake_data = {
                    'question_id': question_id,
                    'lecture_id': question.get('lecture_id', 'unknown'),
                    'question_type': question.get('type', 'short'),
                    'question_text': question_text,
                    'user_answer': str(answer) if answer is not None else '',
                    'correct_answer': str(question['answer']) if question['answer'] is not None else '',
                    'exam_date': datetime.now()
                }
                
                # 객관식 문제인 경우 선택지도 저장
                if question.get('type') == 'multiple' and 'options' in question:
                    mistake_data['options'] = question['options']
                
                mistakes.append(mistake_data)
        
        # 오답 노트에 저장
        for mistake in mistakes:
            self.mistake_repo.save_mistake(user_id, mistake)
        
        return results
    
    def _grade_short_answer(self, user_answer, correct_answer):
        """
        서술형 문제 채점 로직 - 키워드 일치도 검사
        """
        if not user_answer or not correct_answer:
            return False
        
        user_answer = user_answer.lower().strip()
        correct_answer = correct_answer.lower().strip()
        
        keywords = correct_answer.split()
        matched_keywords = 0
        
        for keyword in keywords:
            if len(keyword) > 3 and keyword in user_answer:
                matched_keywords += 1
        
        return matched_keywords >= len(keywords) * 0.5
    
    def _grade_multiple_choice(self, user_answer, correct_answer):
        """
        선택형 문제 채점 로직
        """
        try:
             user_int = int(user_answer) if user_answer is not None else None
             correct_int = int(correct_answer) if correct_answer is not None else None
             return user_int == correct_int
        except:
             return user_answer == correct_answer
    
    def _create_blank_question(self, question_type, index):
        """
        빈칸 문제 생성 - 문제가 부족한 경우 사용
        """
        if question_type == 'short':
            return {
                'id': f'blank_short_{index}',
                'type': 'short',
                'text': '빈칸 문제입니다.',
                'answer': ''
            }
        else:
            return {
                'id': f'blank_multiple_{index}',
                'type': 'multiple',
                'text': '빈칸 문제입니다.',
                'options': [
                    '선택지 1',
                    '선택지 2',
                    '선택지 3',
                    '선택지 4'
                ],
                'answer': 0
            }
    
    def get_weakness_analysis(self, user_id):
        """
        사용자의 약점 분석 데이터 반환
        """
        stats = self.mistake_repo.get_mistake_statistics(user_id)
        
        # 추가 분석 데이터
        analysis = {
            'total_mistakes': stats['total_mistakes'],
            'weakness_by_type': stats['by_type'],
            'weakness_by_lecture': stats['by_lecture'],
            'most_mistaken_questions': stats['most_mistaken_questions'],
            'recommendations': []
        }
        
        # 추천 사항 생성
        if stats['total_mistakes'] > 0:
            # 가장 많이 틀린 유형
            type_items = [(k, v) for k, v in stats['by_type'].items() if v > 0]
            if type_items:
                max_type = max(type_items, key=lambda x: x[1])
                type_name = '서술형' if max_type[0] == 'short' else '객관식'
                analysis['recommendations'].append({
                    'type': 'type',
                    'message': f'{type_name} 유형 문제를 더 많이 연습하세요. ({max_type[1]}회 오답)',
                    'priority': 'high' if max_type[1] >= stats['total_mistakes'] * 0.5 else 'medium'
                })
            
            # 가장 많이 틀린 강의
            if stats['by_lecture']:
                max_lecture = max(stats['by_lecture'].items(), key=lambda x: x[1])
                lecture_title = self._get_lecture_title(max_lecture[0])
                analysis['recommendations'].append({
                    'type': 'lecture',
                    'message': f'"{lecture_title}" 강의 내용을 다시 복습하세요. ({max_lecture[1]}회 오답)',
                    'lecture_id': max_lecture[0],
                    'priority': 'high' if max_lecture[1] >= stats['total_mistakes'] * 0.3 else 'medium'
                })
            
            # 반복적으로 틀린 문제
            if stats['most_mistaken_questions']:
                top_mistake = stats['most_mistaken_questions'][0]
                if top_mistake['mistake_count'] >= 2:
                    analysis['recommendations'].append({
                        'type': 'question',
                        'message': f'특정 문제를 {top_mistake["mistake_count"]}회 틀렸습니다. 해당 문제를 집중적으로 복습하세요.',
                        'question_id': top_mistake['question_id'],
                        'priority': 'high'
                    })
        
        return analysis
    
    def _get_lecture_title(self, lecture_id):
        """
        강의 ID로 강의 제목 가져오기
        """
        try:
            lecture_doc = self.db.collection('lectures').document(lecture_id).get()
            if lecture_doc.exists:
                return lecture_doc.to_dict().get('title', '제목 없음')
        except:
            pass
        return '제목 없음'