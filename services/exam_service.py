from repositories.question_repository import QuestionRepository
from firebase_admin import firestore
from flask import session
import random

class ExamService:
    def __init__(self):
        self.question_repo = QuestionRepository()
        self.db = firestore.client()
    
    def get_random_questions(self, short_answer_count, multiple_choice_count, user_id=None):
        """
        지정된 유형별 개수에 맞춰 문제를 랜덤하게 가져옴
        
        Args:
            short_answer_count (int): 주관식 문제 개수
            multiple_choice_count (int): 객관식 문제 개수
            user_id (str): 사용자 ID. 제공되면 해당 사용자의 문제만 가져옴
        """
        # 세션에서 user_id 가져오기 (전달되지 않은 경우)
        if not user_id:
            user_id = session.get('user', {}).get('uid')
        
        all_questions = self.question_repo.get_all_questions(user_id=user_id)
        
        # 디버깅: 문제 데이터 확인
        print(f"DEBUG: 전체 문제 개수: {len(all_questions)}")
        for idx, q in enumerate(all_questions[:5]):  # 처음 5개만 출력
            print(f"DEBUG: 문제 {idx + 1} - ID: {q.get('id')}, Type: {q.get('type')}, Options: {q.get('options')}")
        
        short_questions = [q for q in all_questions if q['type'] == 'short']
        multiple_questions = [q for q in all_questions if q['type'] == 'multiple']
        
        print(f"DEBUG: 주관식 문제 개수: {len(short_questions)}, 객관식 문제 개수: {len(multiple_questions)}")
        
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
        시험 답안을 채점
        
        Args:
            user_id (str): 사용자 ID
            question_ids (list): 문제 ID 리스트
            answers (list): 사용자 답안 리스트
        """
        results = []
        questions = self.question_repo.get_questions_by_ids(question_ids, user_id=user_id)
        
        question_dict = {q['id']: q for q in questions}
        
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
                    
                    # 디버깅 로그 추가
                    print(f"DEBUG: 채점 - 문제 ID: {question_id}, 사용자 답안: {user_int}, 정답 인덱스: {correct_int}")
                    print(f"DEBUG: 문제 내용: {question.get('question', question.get('text', ''))[:100]}")
                    if 'options' in question:
                        print(f"DEBUG: 보기 옵션: {question['options']}")
                    
                    is_correct = user_int == correct_int
                except Exception as e:
                    print(f"DEBUG: 채점 중 오류: {str(e)}, answer: {answer}, question['answer']: {question.get('answer')}")
                    is_correct = answer == question['answer']
            else:
                is_correct = False
            
            # 결과에 문제 정보도 포함 (디버깅 및 결과 표시용)
            result_data = {
                'question_id': question_id,
                'is_correct': bool(is_correct),
                'correct_answer': question['answer'],
                'question_text': question.get('question', question.get('text', ''))[:100]  # 문제 내용 일부
            }
            
            # 객관식 문제인 경우 보기 정보도 포함
            if question['type'] == 'multiple' and 'options' in question:
                result_data['correct_answer_option'] = question['options'][question['answer']] if question['answer'] < len(question['options']) else None
                result_data['options'] = question['options']
            
            results.append(result_data)
        
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