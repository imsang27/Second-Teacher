from flask import Blueprint, request, jsonify, render_template, session
import os
from services.audio_service import AudioService
from services.question_generator import generate_question
from services.firebase_service import save_question, get_materials, get_material_content, get_questions
from werkzeug.utils import secure_filename
from utils.file_utils import is_allowed_audio_file, validate_file_request, ALLOWED_AUDIO_EXTENSIONS

stt_gen_bp = Blueprint('stt_gen', __name__)
audio_service = AudioService()

@stt_gen_bp.route('/stt-generate', methods=['GET'])
def stt_generate_page():
    """
    문제 생성 페이지를 렌더링
    """
    return render_template('stt_generate.html')

@stt_gen_bp.route('/questions', methods=['GET'])
def questions_list():
    """
    저장된 문제 목록 페이지를 렌더링
    """
    return render_template('questions_list.html')

@stt_gen_bp.route('/api/questions', methods=['GET'])
def get_questions_list():
    """
    저장된 문제 목록을 조회하는 API
    """
    try:
        user_id = session.get('user', {}).get('uid')
        
        if not user_id:
            return jsonify({"success": False, "error": "로그인이 필요합니다."}), 401
        
        questions = get_questions()
        
        return jsonify({
            "success": True,
            "questions": questions
        })
    except Exception as e:
        print(f"Error getting questions list: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@stt_gen_bp.route('/api/materials', methods=['GET'])
def get_material_list():
    """
    저장된 자료 목록을 조회
    """
    try:
        material_type = request.args.get('type', 'pdf')
        user_id = session.get('user', {}).get('uid')
        
        if not user_id:
            return jsonify({"success": False, "error": "로그인이 필요합니다."}), 401
        
        materials = get_materials(None, material_type)
        
        return jsonify({
            "success": True,
            "materials": materials
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@stt_gen_bp.route('/api/generate-question', methods=['POST'])
def generate_from_material():
    """
    기존 자료로부터 문제 생성
    """
    try:
        # 세션 확인
        user_id = session.get('user', {}).get('uid')
        if not user_id:
            print("ERROR: 사용자 세션이 없습니다.")
            return jsonify({
                "success": False, 
                "error": "로그인이 필요합니다."
            }), 401
        
        # 요청 데이터 확인
        if not request.json:
            print("ERROR: 요청 데이터가 없습니다.")
            return jsonify({
                "success": False, 
                "error": "요청 데이터가 없습니다."
            }), 400
        
        data = request.json
        material_id = data.get('material_id')
        material_type = data.get('material_type')
        
        print(f"DEBUG: Generating question from material - ID: {material_id}, Type: {material_type}, User: {user_id}")
        
        if not material_id or not material_type:
            print(f"ERROR: 필수 파라미터 누락 - material_id: {material_id}, material_type: {material_type}")
            return jsonify({
                "success": False, 
                "error": "필수 파라미터가 누락되었습니다."
            }), 400
        
        # 자료 내용 가져오기
        try:
            material_content = get_material_content(material_id, material_type)
            if not material_content:
                print(f"ERROR: Material content not found for ID: {material_id}, Type: {material_type}")
                return jsonify({
                    "success": False, 
                    "error": "자료를 찾을 수 없습니다."
                }), 404
            
            if not isinstance(material_content, str) or len(material_content.strip()) == 0:
                print(f"ERROR: Material content is empty or invalid")
                return jsonify({
                    "success": False, 
                    "error": "자료 내용이 비어있습니다."
                }), 400
        except Exception as e:
            print(f"ERROR: Exception in get_material_content: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return jsonify({
                "success": False, 
                "error": f"자료 내용을 가져오는 중 오류가 발생했습니다: {str(e)}"
            }), 500
        
        print(f"DEBUG: Material content length: {len(material_content)}")
        print(f"DEBUG: Material content preview: {material_content[:200]}...")
        
        # 기존 문제 목록 가져오기 (중복 방지 및 다양성 확보)
        existing_questions = []
        try:
            existing_questions = get_questions()
            print(f"DEBUG: 기존 문제 {len(existing_questions)}개를 참고하여 새로운 문제 생성")
        except Exception as e:
            print(f"WARNING: 기존 문제 목록을 가져오는데 실패했습니다: {str(e)}")
            # 기존 문제 목록 가져오기 실패해도 문제 생성은 계속 진행
        
        # 문제 생성 (기존 문제 목록과 함께 전달)
        try:
            question = generate_question(material_content, existing_questions=existing_questions)
            if not question:
                print("ERROR: generate_question returned None")
                return jsonify({
                    "success": False, 
                    "error": "문제 생성에 실패했습니다. 서버 로그를 확인해주세요."
                }), 500
        except Exception as e:
            print(f"ERROR: Exception in generate_question: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return jsonify({
                "success": False, 
                "error": f"문제 생성 중 오류가 발생했습니다: {str(e)}"
            }), 500
            
        print("DEBUG: Question generated successfully")
        print(f"DEBUG: Question data: {question}")
        
        # 생성된 문제를 Firebase에 저장
        save_result = None
        try:
            print(f"DEBUG: 저장할 문제 데이터: {question}")
            print(f"DEBUG: 문제 타입: {question.get('type')}, 보기 옵션: {question.get('options')}")
            save_result = save_question(None, question)
            
            if save_result and save_result.get('is_duplicate'):
                print("WARNING: 중복 문제 - 저장하지 않음")
                return jsonify({
                    "success": True,
                    "question": question,
                    "message": save_result.get('message', '중복된 문제입니다.'),
                    "is_duplicate": True,
                    "warning": "이미 존재하는 문제와 유사한 문제입니다."
                })
            elif save_result and save_result.get('success'):
                print("DEBUG: Question saved to Firebase")
            else:
                print(f"WARNING: 문제 저장 실패: {save_result.get('message') if save_result else 'Unknown error'}")
        except Exception as e:
            print(f"WARNING: Failed to save question to Firebase: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # 저장 실패해도 문제는 반환
        
        return jsonify({
            "success": True,
            "question": question,
            "message": save_result.get('message', '문제가 생성되었습니다.') if save_result else "문제가 생성되었습니다.",
            "is_duplicate": save_result.get('is_duplicate', False) if save_result else False
        })
    except Exception as e:
        print(f"ERROR: Unexpected error in generate_from_material: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            "success": False, 
            "error": f"예기치 않은 오류가 발생했습니다: {str(e)}"
        }), 500

@stt_gen_bp.route('/api/stt-generate', methods=['POST'])
def stt_generate():
    # 파일 요청 검증
    is_valid, result, status_code = validate_file_request(
        request, 
        file_key='file', 
        required_extensions=ALLOWED_AUDIO_EXTENSIONS,
        lecture_id_required=False
    )
    
    if not is_valid:
        return jsonify(result), status_code
    
    # 검증 통과 시 file 객체를 가져옴
    file = result
    user_id = session.get('user', {}).get('uid')
    
    if not user_id:
        return jsonify({"success": False, "error": "로그인이 필요합니다."}), 401

    try:
        # 오디오 파일을 텍스트로 변환
        result = audio_service.transcribe_audio(file)
        if not result['success']:
            return jsonify({"error": result['error']}), 500

        # 기존 문제 목록 가져오기 (중복 방지 및 다양성 확보)
        existing_questions = []
        try:
            from services.firebase_service import get_questions
            existing_questions = get_questions()
            print(f"DEBUG: 기존 문제 {len(existing_questions)}개를 참고하여 새로운 문제 생성")
        except Exception as e:
            print(f"WARNING: 기존 문제 목록을 가져오는데 실패했습니다: {str(e)}")
            # 기존 문제 목록 가져오기 실패해도 문제 생성은 계속 진행

        # 문제 생성 및 저장 (기존 문제 목록과 함께 전달)
        question = generate_question(result['text'], existing_questions=existing_questions)
        if not question:
            return jsonify({
                "success": False,
                "error": "문제 생성에 실패했습니다."
            }), 500
        
        # 문제 저장 (중복 체크 포함)
        save_result = save_question(None, question)
        
        return jsonify({
            "success": True,
            "text": result['text'],
            "question": question,
            "message": save_result.get('message', '문제가 생성되었습니다.') if save_result else "문제가 생성되었습니다.",
            "is_duplicate": save_result.get('is_duplicate', False) if save_result else False,
            "warning": "이미 존재하는 문제와 유사한 문제입니다." if save_result and save_result.get('is_duplicate') else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
