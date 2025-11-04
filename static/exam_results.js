document.addEventListener('DOMContentLoaded', function() {
    // 결과 데이터 불러오기
    const examResults = JSON.parse(sessionStorage.getItem('examResults'));
    if (!examResults) {
        // 결과가 없으면 시험 설정 페이지로 리디렉션
        alert('시험 결과 데이터가 없습니다.');
        window.location.href = '/exam/platform';
        return;
    }
    
    // DOM 요소
    const correctCountElem = document.getElementById('correctCount');
    const totalCountElem = document.getElementById('totalCount');
    const shortAnswerScoreElem = document.getElementById('shortAnswerScore');
    const multipleChoiceScoreElem = document.getElementById('multipleChoiceScore');
    const questionsResultsElem = document.getElementById('questionsResults');
    
    // 초기화 함수
    function init() {
        // 채점 결과 처리 및 표시
        processResults();
    }
    
    // 채점 결과 처리
    function processResults() {
        // 전체 점수 계산
        const { questions, userAnswers, results } = examResults;
        const totalQuestions = questions.length;
        
        // 디버깅: 저장된 답안 확인
        console.log('=== 시험 결과 디버깅 ===');
        console.log('저장된 답안:', userAnswers);
        questions.forEach((q, idx) => {
            if (q.type === 'multiple') {
                console.log(`문제 ${idx + 1} (ID: ${q.id}):`);
                console.log(`  - 저장된 답안 인덱스: ${userAnswers[idx]}`);
                console.log(`  - 원본 보기:`, q.originalOptions || q.options);
                console.log(`  - 원본 정답 인덱스: ${q.originalAnswer !== undefined ? q.originalAnswer : q.answer}`);
                if (q.originalOptions && userAnswers[idx] !== undefined) {
                    console.log(`  - 제출한 답안 텍스트: ${q.originalOptions[userAnswers[idx]]}`);
                }
            }
        });
        
        // 결과 배열에서 정답 수 계산 - is_correct 값을 직접 사용
        const correctAnswers = results.filter(result => result.is_correct === true).length;
        
        // 유형별 점수 계산
        let shortAnswerTotal = 0;
        let shortAnswerCorrect = 0;
        let multipleChoiceTotal = 0;
        let multipleChoiceCorrect = 0;
        
        questions.forEach((question, index) => {
            const result = results.find(r => r.question_id === question.id);
            const isCorrect = result ? result.is_correct === true : false;
            
            if (question.type === 'short') {
                shortAnswerTotal++;
                if (isCorrect) shortAnswerCorrect++;
            } else if (question.type === 'multiple') {
                multipleChoiceTotal++;
                if (isCorrect) multipleChoiceCorrect++;
            }
        });
        
        // 점수 표시
        correctCountElem.textContent = correctAnswers;
        totalCountElem.textContent = totalQuestions;
        shortAnswerScoreElem.textContent = `${shortAnswerCorrect}/${shortAnswerTotal}`;
        multipleChoiceScoreElem.textContent = `${multipleChoiceCorrect}/${multipleChoiceTotal}`;
        
        // 문제별 결과 렌더링
        renderQuestionResults();
    }
    
    // 문제별 결과 렌더링
    function renderQuestionResults() {
        questionsResultsElem.innerHTML = '';
        
        const { questions, userAnswers, results } = examResults;
        
        questions.forEach((question, index) => {
            const result = results.find(r => r.question_id === question.id);
            
            // 명시적으로 boolean 값으로 변환하여 정답 여부 판단
            const isCorrect = result && result.is_correct === true;
            
            const resultItem = document.createElement('div');
            resultItem.className = `question-result ${isCorrect ? 'correct' : 'incorrect'}`;
            
            // 문제 유형에 따른 표시
            let questionTypeHTML = '';
            if (question.type === 'short') {
                questionTypeHTML = '<span class="badge badge-short">서술형</span>';
            } else if (question.type === 'multiple') {
                questionTypeHTML = '<span class="badge badge-multiple">선택형</span>';
            }
            
            // 정답 여부 표시
            const resultStatusHTML = `<span class="result-status ${isCorrect ? 'correct' : 'incorrect'}">${isCorrect ? '정답' : '오답'}</span>`;
            
            // 문제 내용
            resultItem.innerHTML = `
                <h3>
                    <div>문제 ${index + 1} ${questionTypeHTML}</div>
                    ${resultStatusHTML}
                </h3>
                <div class="question-text">${question.text}</div>
            `;
            
            // 제출한 답안 표시
            const userAnswerElem = document.createElement('div');
            userAnswerElem.className = 'answer-section';
            
            if (question.type === 'short') {
                userAnswerElem.innerHTML = `
                    <h4>제출한 답안:</h4>
                    <div class="answer-content">${userAnswers[index] || '(답변 없음)'}</div>
                `;
            } else if (question.type === 'multiple') {
                const userAnswer = userAnswers[index];
                let answerText = '(답변 없음)';
                
                // 원본 보기 사용 (섞인 보기 대신)
                const originalOptions = question.originalOptions || question.options;
                
                // 디버깅 로그
                console.log(`문제 ${index + 1} - 제출한 답안 표시:`, {
                    userAnswerIndex: userAnswer,
                    originalOptions: originalOptions,
                    hasOriginalOptions: !!question.originalOptions
                });
                
                if (userAnswer !== null && userAnswer !== undefined) {
                    // 선택한 답변이 있는 경우 (userAnswer는 원본 인덱스)
                    if (originalOptions && originalOptions.length > userAnswer && originalOptions[userAnswer] !== undefined) {
                        answerText = originalOptions[userAnswer];
                        console.log(`문제 ${index + 1} - 표시할 답안 텍스트: ${answerText}`);
                    } else {
                        answerText = `선택지 ${userAnswer + 1} (인덱스: ${userAnswer})`;
                        console.warn(`문제 ${index + 1} - 원본 보기에서 답안을 찾을 수 없음. 인덱스: ${userAnswer}, 원본 보기 개수: ${originalOptions ? originalOptions.length : 0}`);
                    }
                }
                
                userAnswerElem.innerHTML = `
                    <h4>제출한 답안:</h4>
                    <div class="answer-content">${answerText}</div>
                `;
            }
            
            resultItem.appendChild(userAnswerElem);
            
            // 정답 표시
            const correctAnswerElem = document.createElement('div');
            correctAnswerElem.className = 'answer-section';
            
            if (question.type === 'short') {
                correctAnswerElem.innerHTML = `
                    <h4>모범 답안:</h4>
                    <div class="answer-content">${question.answer || '(답안 정보 없음)'}</div>
                `;
            } else if (question.type === 'multiple') {
                let correctAnswerText = '(정답 정보 없음)';
                
                // 원본 보기와 원본 정답 인덱스 사용
                const originalOptions = question.originalOptions || question.options;
                const originalAnswer = question.originalAnswer !== undefined ? question.originalAnswer : question.answer;
                
                if (originalAnswer !== undefined && originalAnswer !== null && 
                    originalOptions && originalOptions[originalAnswer] !== undefined) {
                    correctAnswerText = originalOptions[originalAnswer];
                } else if (originalAnswer !== undefined && originalAnswer !== null) {
                    correctAnswerText = `선택지 ${parseInt(originalAnswer) + 1}`;
                }
                
                correctAnswerElem.innerHTML = `
                    <h4>정답:</h4>
                    <div class="answer-content">${correctAnswerText}</div>
                `;
            }
            
            resultItem.appendChild(correctAnswerElem);
            
            // 결과 컨테이너에 추가
            questionsResultsElem.appendChild(resultItem);
        });
    }
    
    // 초기화 실행
    init();
});