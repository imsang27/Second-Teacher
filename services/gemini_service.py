# services/gemini_service.py
import os
import requests
import json
import PyPDF2
import io
from dotenv import load_dotenv
import google.generativeai as genai
from typing import Dict, Optional

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

class GeminiService:
    def __init__(self):
        # Gemini API 키 설정
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        # 인스턴스 속성으로 저장
        self.api_key = api_key
        self.api_url = GEMINI_API_URL
        
        genai.configure(api_key=api_key)
        # 최신 Gemini 모델 사용 (gemini-pro는 더 이상 사용 불가)
        # gemini-1.5-flash: 빠르고 효율적인 모델
        # gemini-1.5-pro: 더 강력한 모델
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def summarize_pdf(self, pdf_file, prompt_option=1):
        """PDF 파일을 분석하여 요약"""
        try:
            # PDF 파일에서 텍스트 추출
            pdf_text = self._extract_text_from_pdf(pdf_file)
            
            if not pdf_text.strip():
                return {
                    "success": False,
                    "error": "PDF에서 텍스트를 추출할 수 없습니다."
                }
            
            # 텍스트가 너무 길면 잘라내기 (Gemini 토큰 제한)
            if len(pdf_text) > 30000:
                pdf_text = pdf_text[:30000] + "... (텍스트가 너무 길어 일부 생략되었습니다)"
            
            # 선택한 옵션에 따라 프롬프트 설정
            prompt = self._get_prompt_by_option(prompt_option, pdf_text)
            
            # Gemini에 요약 요청
            return self._send_gemini_request(prompt)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"PDF 요약 처리 중 오류가 발생했습니다: {str(e)}"
            }
    
    def _extract_text_from_pdf(self, pdf_file):
        """PDF 파일에서 텍스트 추출"""
        # 파일 위치 저장
        current_position = pdf_file.tell()
        # 파일 포인터를 처음으로 이동
        pdf_file.seek(0)
        
        file_content = pdf_file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        
        text = ""
        for page in pdf_reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text + "\n"
        
        # 파일 포인터 원래 위치로 복원
        pdf_file.seek(current_position)
        return text
    
    def _get_prompt_by_option(self, option, pdf_text):
        """옵션에 따른 프롬프트 반환"""
        prompts = {
            1: f"다음 PDF 문서의 내용을 한국어로 간결하게 요약해주세요. 주요 내용과 핵심 포인트에 초점을 맞춰주세요.\n\n{pdf_text}",
            2: f"다음 PDF 문서의 내용을 한국어로 상세하게 요약해주세요. 주요 내용과 핵심 포인트를 모두 포함하되, 각 섹션별로 구분하여 요약해주세요. 정보의 손실을 최소화하면서 원본 내용의 구조를 유지해주세요.\n\n{pdf_text}"
        }
        
        return prompts.get(option, prompts[1])  # 기본값은 옵션 1
    
    def _send_gemini_request(self, prompt):
        """Gemini API에 요청 보내기"""
        try:
            request_data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "topP": 0.8,
                    "topK": 40
                }
            }
            
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                data=json.dumps(request_data),
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    content = result["candidates"][0]["content"]
                    parts = content.get("parts", [])
                    if parts and "text" in parts[0]:
                        return {
                            "success": True,
                            "summary": parts[0]["text"]
                        }
            
            return {
                "success": False,
                "error": f"API 요청 실패: {response.status_code}, {response.text}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def generate_question(self, text: str) -> Optional[Dict]:
        """
        Gemini API를 사용하여 주어진 텍스트로부터 문제를 생성
        
        Args:
            text (str): 문제를 생성할 텍스트
            
        Returns:
            dict: 생성된 문제 정보 (프론트엔드가 기대하는 형태)
        """
        try:
            # 텍스트 길이 제한 (Gemini 토큰 제한 고려)
            if len(text) > 10000:
                text = text[:10000] + "... (텍스트가 너무 길어 일부 생략되었습니다)"
            
            # 프롬프트 구성 - JSON 형식으로 응답 요청
            prompt = f"""다음 텍스트를 바탕으로 교육용 객관식 문제 1개를 생성해주세요.

텍스트:
{text}

다음 JSON 형식으로만 응답해주세요 (다른 설명 없이 JSON만):
{{
    "question": "문제 내용",
    "options": ["보기1", "보기2", "보기3", "보기4"],
    "answer": 0
}}

주의사항:
- answer는 정답의 인덱스입니다 (0, 1, 2, 3 중 하나)
- options는 정확히 4개의 보기가 있어야 합니다
- 문제는 텍스트 내용을 바탕으로 의미있고 교육적이어야 합니다
- JSON 형식만 응답하고 다른 설명은 포함하지 마세요"""
            
            # REST API를 사용하여 Gemini API 호출 (SDK 대신)
            response_result = self._send_gemini_request(prompt)
            
            if not response_result.get('success'):
                print(f"ERROR: Gemini API 요청 실패: {response_result.get('error', 'Unknown error')}")
                return None
            
            response_text = response_result.get('summary', '')
            
            
            print(f"DEBUG: Gemini 응답 텍스트 길이: {len(response_text)}")
            print(f"DEBUG: Gemini 응답 미리보기: {response_text[:500]}...")
            
            if not response_text or len(response_text.strip()) == 0:
                print("ERROR: Gemini API 응답이 비어있습니다.")
                return None
            
            # 응답 파싱 및 구조화
            question = self._parse_response(response_text)
            
            if not question:
                print(f"ERROR: 응답 파싱 실패. 원본 응답: {response_text[:1000]}")
            
            return question
            
        except Exception as e:
            print(f"Error generating question with Gemini: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
            
    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """
        Gemini API의 응답을 파싱하여 구조화된 문제 데이터로 변환
        """
        try:
            import re
            
            # 먼저 JSON 코드 블록에서 추출 시도 (```json ... ``` 형식)
            json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_block_match:
                json_str = json_block_match.group(1)
                try:
                    question_data = json.loads(json_str)
                    if all(key in question_data for key in ['question', 'options', 'answer']):
                        answer = question_data['answer']
                        if isinstance(answer, str):
                            answer = int(answer)
                        print("DEBUG: JSON 코드 블록에서 파싱 성공")
                        return {
                            "question": question_data['question'],
                            "options": question_data['options'],
                            "answer": answer if isinstance(answer, int) else 0
                        }
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    print(f"DEBUG: JSON 코드 블록 파싱 실패: {str(e)}")
            
            # 중괄호를 세어서 완전한 JSON 객체 찾기
            brace_count = 0
            start_idx = -1
            for i, char in enumerate(response_text):
                if char == '{':
                    if brace_count == 0:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        json_str = response_text[start_idx:i+1]
                        try:
                            question_data = json.loads(json_str)
                            if all(key in question_data for key in ['question', 'options', 'answer']):
                                answer = question_data['answer']
                                if isinstance(answer, str):
                                    answer = int(answer)
                                print("DEBUG: 중괄호 매칭으로 JSON 파싱 성공")
                                return {
                                    "question": question_data['question'],
                                    "options": question_data['options'],
                                    "answer": answer if isinstance(answer, int) else 0
                                }
                        except (json.JSONDecodeError, ValueError, KeyError) as e:
                            print(f"DEBUG: 중괄호 매칭 JSON 파싱 실패: {str(e)}")
                        start_idx = -1
            
            # JSON 부분만 추출 (코드 블록이나 다른 텍스트 제거)
            # 중첩된 JSON 객체를 처리하기 위한 더 나은 정규식
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                try:
                    question_data = json.loads(json_str)
                    
                    # 필수 필드 확인
                    if all(key in question_data for key in ['question', 'options', 'answer']):
                        # answer가 정수인지 확인
                        if isinstance(question_data['answer'], int):
                            return {
                                "question": question_data['question'],
                                "options": question_data['options'],
                                "answer": question_data['answer']
                            }
                        # answer가 문자열인 경우 (예: "0", "1" 등)
                        elif isinstance(question_data['answer'], str):
                            try:
                                answer_idx = int(question_data['answer'])
                                return {
                                    "question": question_data['question'],
                                    "options": question_data['options'],
                                    "answer": answer_idx
                                }
                            except ValueError:
                                pass
                except json.JSONDecodeError as e:
                    print(f"JSON 파싱 오류: {str(e)}")
                    print(f"응답 텍스트: {response_text}")
            
            # JSON 파싱 실패 시, 텍스트에서 직접 추출 시도
            return self._parse_text_response(response_text)
            
        except Exception as e:
            print(f"Error parsing Gemini response: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
    
    def _parse_text_response(self, response_text: str) -> Optional[Dict]:
        """
        JSON 파싱 실패 시 텍스트에서 정보 추출
        """
        try:
            import re
            
            # 문제 추출
            question_match = re.search(r'문제[:\s]*([^\n]+)', response_text, re.IGNORECASE)
            if not question_match:
                question_match = re.search(r'question[:\s]*([^\n]+)', response_text, re.IGNORECASE)
            
            # 보기 추출
            options = []
            option_patterns = [
                r'(?:보기|옵션|option)[\s\d]*[:\-]\s*([^\n]+)',
                r'[①②③④⑤⑥⑦⑧]\s*([^\n]+)',
                r'[1-4][\.\)]\s*([^\n]+)'
            ]
            
            for pattern in option_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                if matches:
                    options = [m.strip() for m in matches[:4]]
                    break
            
            # 정답 추출
            answer_match = re.search(r'정답[:\s]*([0-9])', response_text, re.IGNORECASE)
            if not answer_match:
                answer_match = re.search(r'answer[:\s]*([0-9])', response_text, re.IGNORECASE)
            
            if question_match and len(options) >= 4:
                question = question_match.group(1).strip()
                answer = int(answer_match.group(1)) if answer_match else 0
                
                return {
                    "question": question,
                    "options": options[:4],
                    "answer": answer
                }
            
            # 기본값 반환하지 않고 None 반환 (파싱 실패 시)
            print(f"ERROR: 텍스트 파싱 실패. 원본 응답: {response_text[:500]}")
            return None
            
        except Exception as e:
            print(f"Error in text parsing: {str(e)}")
            return None