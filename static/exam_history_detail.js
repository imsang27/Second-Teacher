document.addEventListener('DOMContentLoaded', function() {
    // 시험 기록 상세 데이터 로드
    loadExamDetail();
});

// 시험 기록 상세 로드
function loadExamDetail() {
    fetch(`/api/exam/history/${examId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderExamDetail(data.exam);
            } else {
                alert('시험 기록을 불러올 수 없습니다: ' + data.error);
                window.location.href = '/exam/history';
            }
        })
        .catch(error => {
            console.error('시험 기록 상세 로드 중 오류:', error);
            alert('시험 기록을 불러오는 중 오류가 발생했습니다.');
            window.location.href = '/exam/history';
        });
}

// 시험 기록 상세 렌더링
function renderExamDetail(exam) {
    // 점수 표시
    const correctCountElem = document.getElementById('correctCount');
    const totalCountElem = document.getElementById('totalCount');
    const shortAnswerScoreElem = document.getElementById('shortAnswerScore');
    const multipleChoiceScoreElem = document.getElementById('multipleChoiceScore');
    const examDateElem = document.getElementById('examDate');
    const questionsResultsElem = document.getElementById('questionsResults');
    
    const totalQuestions = exam.total_questions || 0;
    const correctAnswers = exam.correct_count || 0;
    const shortAnswerTotal = exam.short_answer_total || 0;
    const shortAnswerCorrect = exam.short_answer_correct || 0;
    const multipleChoiceTotal = exam.multiple_choice_total || 0;
    const multipleChoiceCorrect = exam.multiple_choice_correct || 0;
    
    correctCountElem.textContent = correctAnswers;
    totalCountElem.textContent = totalQuestions;
    shortAnswerScoreElem.textContent = `${shortAnswerCorrect}/${shortAnswerTotal}`;
    multipleChoiceScoreElem.textContent = `${multipleChoiceCorrect}/${multipleChoiceTotal}`;
    
    // 날짜 표시
    const examDate = exam.exam_date ? formatDate(exam.exam_date) : '날짜 정보 없음';
    examDateElem.textContent = examDate;
    
    // 문제별 결과 렌더링
    const questions = exam.questions || [];
    const userAnswers = exam.user_answers || [];
    const results = exam.results || [];
    
    questionsResultsElem.innerHTML = '';
    
    questions.forEach((question, index) => {
        const result = results.find(r => r.question_id === question.id);
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
        const questionText = question.question || question.text || '문제 내용 없음';
        resultItem.innerHTML = `
            <h3>
                <div>문제 ${index + 1} ${questionTypeHTML}</div>
                ${resultStatusHTML}
            </h3>
            <div class="question-text">${questionText}</div>
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
            
            if (userAnswer !== null && userAnswer !== undefined) {
                if (question.options && question.options[userAnswer]) {
                    answerText = question.options[userAnswer];
                } else {
                    answerText = `선택지 ${userAnswer + 1}`;
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
            
            if (question.answer !== undefined && question.answer !== null && 
                question.options && question.options[question.answer]) {
                correctAnswerText = question.options[question.answer];
            } else if (question.answer !== undefined && question.answer !== null) {
                correctAnswerText = `선택지 ${parseInt(question.answer) + 1}`;
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

// 날짜 포맷팅
function formatDate(dateValue) {
    if (!dateValue) return '날짜 정보 없음';
    
    let date;
    if (dateValue.toDate) {
        // Firestore Timestamp
        date = dateValue.toDate();
    } else if (dateValue.seconds) {
        // Firestore Timestamp (직렬화된 형태)
        date = new Date(dateValue.seconds * 1000);
    } else {
        date = new Date(dateValue);
    }
    
    if (isNaN(date.getTime())) {
        return '날짜 정보 없음';
    }
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}`;
}

