from repositories.question_repository import QuestionRepository
from repositories.exam_history_repository import ExamHistoryRepository
from firebase_admin import firestore
from datetime import datetime
import random

class ExamService:
    def __init__(self):
        self.question_repo = QuestionRepository()
        self.exam_history_repo = ExamHistoryRepository()
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
        시험 답안을 채점하고 시험 기록 저장
        """
        results = []
        questions = self.question_repo.get_questions_by_ids(question_ids)
        
        question_dict = {q['id']: q for q in questions}
        
        # 통계 변수
        short_answer_total = 0
        short_answer_correct = 0
        multiple_choice_total = 0
        multiple_choice_correct = 0
        
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
                     short_answer_total += 1
                     if is_correct:
                         short_answer_correct += 1
            elif question['type'] == 'multiple':
            # 정수 변환을 통한 일관된 비교
                 try:
                     user_int = int(answer) if answer is not None else None
                     correct_int = int(question['answer']) if question['answer'] is not None else None
                     is_correct = user_int == correct_int
                 except:
                     is_correct = answer == question['answer']
                 multiple_choice_total += 1
                 if is_correct:
                     multiple_choice_correct += 1
            else:
                is_correct = False
            
            results.append({
                 'question_id': question_id,
                 'is_correct': bool(is_correct),
                 'correct_answer': question['answer']
            })
        
        # 정답 수 계산
        correct_count = sum(1 for r in results if r.get('is_correct', False))
        total_questions = len(question_ids)
        
        # 시험 기록 저장
        exam_data = {
            'total_questions': total_questions,
            'correct_count': correct_count,
            'short_answer_total': short_answer_total,
            'short_answer_correct': short_answer_correct,
            'multiple_choice_total': multiple_choice_total,
            'multiple_choice_correct': multiple_choice_correct,
            'questions': questions,
            'user_answers': answers,
            'results': results,
            'exam_date': datetime.now()
        }
        
        self.exam_history_repo.save_exam_result(user_id, exam_data)
        
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