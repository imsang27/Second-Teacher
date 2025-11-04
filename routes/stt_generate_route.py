from flask import Blueprint, request, jsonify, render_template, session
import os
from services.audio_service import AudioService
from services.question_generator import generate_question
from services.firebase_service import save_question, get_materials, get_material_content
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
        
        # 문제 생성
        try:
            question = generate_question(material_content)
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
        try:
            save_question(None, question)
            print("DEBUG: Question saved to Firebase")
        except Exception as e:
            print(f"WARNING: Failed to save question to Firebase: {str(e)}")
            # 저장 실패해도 문제는 반환
        
        return jsonify({
            "success": True,
            "question": question,
            "message": "문제가 생성되고 저장되었습니다."
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

        # 문제 생성 및 저장
        question = generate_question(result['text'])
        save_question(None, question)

        return jsonify({
            "success": True,
            "text": result['text'],
            "question": question
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
