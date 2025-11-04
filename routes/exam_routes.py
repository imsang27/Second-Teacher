from flask import Blueprint, render_template, request, jsonify, session
from services.exam_service import ExamService
from services.auth import auth_required

# Blueprint 생성
exam_bp = Blueprint('exam', __name__)
exam_service = ExamService()

@exam_bp.route('/platform')
@auth_required
def exam_platform():
    """시험 설정 페이지"""
    return render_template('exam_platform.html')

@exam_bp.route('/interface')
@auth_required
def exam_interface():
    """시험 진행 페이지"""
    return render_template('exam_interface.html')

@exam_bp.route('/results')
@auth_required
def exam_results():
    """시험 결과 페이지"""
    return render_template('exam_results.html')

@exam_bp.route('/api/exam/questions', methods=['POST'])
@auth_required
def get_exam_questions():
    """
    시험 설정에 따라 문제를 랜덤하게 불러오는 API
        "total_questions":
        "short_answer_count":
        "multiple_choice_count":
    """
    try:
        # 사용자 정보
        user = session.get('user', {})
        user_id = user.get('uid')
        
        if not user_id:
            return jsonify({"success": False, "error": "인증 오류가 발생했습니다."}), 401
        
        # 요청 데이터 검증
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "요청 데이터가 없습니다."}), 400
        
        total_questions = data.get('total_questions')
        short_answer_count = data.get('short_answer_count')
        multiple_choice_count = data.get('multiple_choice_count')
        
        if not all([total_questions, short_answer_count is not None, multiple_choice_count is not None]):
            return jsonify({"success": False, "error": "필수 파라미터가 누락되었습니다."}), 400
        
        if short_answer_count + multiple_choice_count != total_questions:
            return jsonify({"success": False, "error": "문제 유형의 합이 총 문제 수와 일치하지 않습니다."}), 400
        
        # 서비스를 통해 문제 불러오기
        questions = exam_service.get_random_questions(
            short_answer_count=short_answer_count,
            multiple_choice_count=multiple_choice_count
        )
        
        return jsonify({
            "success": True,
            "questions": questions
        })
        
    except Exception as e:
        import traceback
        print(f"문제 로드 중 오류: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@exam_bp.route('/api/exam/submit', methods=['POST'])
@auth_required
def submit_exam():
    """
    시험 답안 제출 및 채점 API
    요청 본문:
    {
        "answers": [],  # 사용자 답안 배열
        "questions": []  # 문제 ID 배열
    }
    """
    try:
        # 사용자 정보
        user = session.get('user', {})
        user_id = user.get('uid')
        
        if not user_id:
            return jsonify({"success": False, "error": "인증 오류가 발생했습니다."}), 401
        
        # 요청 데이터 검증
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "요청 데이터가 없습니다."}), 400
        
        answers = data.get('answers')
        question_ids = data.get('questions')
        
        if not answers or not question_ids:
            return jsonify({"success": False, "error": "필수 파라미터가 누락되었습니다."}), 400
        
        if len(answers) != len(question_ids):
            return jsonify({"success": False, "error": "답안 수와 문제 수가 일치하지 않습니다."}), 400
        
        # 서비스를 통해 채점
        results = exam_service.grade_exam(user_id, question_ids, answers)
        
        return jsonify({
            "success": True,
            "results": results
        })
        
    except Exception as e:
        import traceback
        print(f"시험 제출 중 오류: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@exam_bp.route('/mistakes')
@auth_required
def mistake_notebook():
    """오답 노트 페이지"""
    return render_template('mistake_notebook.html')

@exam_bp.route('/api/mistakes', methods=['GET'])
@auth_required
def get_mistakes():
    """
    사용자의 오답 노트 조회 API
    """
    try:
        user = session.get('user', {})
        user_id = user.get('uid')
        
        if not user_id:
            return jsonify({"success": False, "error": "인증 오류가 발생했습니다."}), 401
        
        limit = request.args.get('limit', type=int)
        mistakes = exam_service.mistake_repo.get_user_mistakes(user_id, limit=limit)
        
        return jsonify({
            "success": True,
            "mistakes": mistakes
        })
        
    except Exception as e:
        import traceback
        print(f"오답 노트 조회 중 오류: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@exam_bp.route('/api/mistakes/analysis', methods=['GET'])
@auth_required
def get_weakness_analysis():
    """
    사용자의 약점 분석 데이터 조회 API
    """
    try:
        user = session.get('user', {})
        user_id = user.get('uid')
        
        if not user_id:
            return jsonify({"success": False, "error": "인증 오류가 발생했습니다."}), 401
        
        analysis = exam_service.get_weakness_analysis(user_id)
        
        return jsonify({
            "success": True,
            "analysis": analysis
        })
        
    except Exception as e:
        import traceback
        print(f"약점 분석 중 오류: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500