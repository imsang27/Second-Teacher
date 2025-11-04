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

@exam_bp.route('/history')
@auth_required
def exam_history():
    """시험 기록 목록 페이지"""
    return render_template('exam_history.html')

@exam_bp.route('/history/<exam_id>')
@auth_required
def exam_history_detail(exam_id):
    """시험 기록 상세 페이지"""
    return render_template('exam_history_detail.html', exam_id=exam_id)

@exam_bp.route('/api/exam/history', methods=['GET'])
@auth_required
def get_exam_history():
    """
    사용자의 시험 기록 목록 조회 API
    """
    try:
        user = session.get('user', {})
        user_id = user.get('uid')
        
        if not user_id:
            return jsonify({"success": False, "error": "인증 오류가 발생했습니다."}), 401
        
        limit = request.args.get('limit', type=int)
        exams = exam_service.exam_history_repo.get_user_exam_history(user_id, limit=limit)
        
        return jsonify({
            "success": True,
            "exams": exams
        })
        
    except Exception as e:
        import traceback
        print(f"시험 기록 조회 중 오류: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@exam_bp.route('/api/exam/history/<exam_id>', methods=['GET'])
@auth_required
def get_exam_history_detail(exam_id):
    """
    특정 시험 기록 상세 조회 API
    """
    try:
        user = session.get('user', {})
        user_id = user.get('uid')
        
        if not user_id:
            return jsonify({"success": False, "error": "인증 오류가 발생했습니다."}), 401
        
        exam = exam_service.exam_history_repo.get_exam_by_id(user_id, exam_id)
        
        if not exam:
            return jsonify({"success": False, "error": "시험 기록을 찾을 수 없습니다."}), 404
        
        return jsonify({
            "success": True,
            "exam": exam
        })
        
    except Exception as e:
        import traceback
        print(f"시험 기록 상세 조회 중 오류: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@exam_bp.route('/api/exam/statistics', methods=['GET'])
@auth_required
def get_exam_statistics():
    """
    사용자의 시험 통계 조회 API
    """
    try:
        user = session.get('user', {})
        user_id = user.get('uid')
        
        if not user_id:
            return jsonify({"success": False, "error": "인증 오류가 발생했습니다."}), 401
        
        stats = exam_service.exam_history_repo.get_exam_statistics(user_id)
        
        return jsonify({
            "success": True,
            "statistics": stats
        })
        
    except Exception as e:
        import traceback
        print(f"시험 통계 조회 중 오류: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500