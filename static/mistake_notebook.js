document.addEventListener('DOMContentLoaded', function() {
    // 약점 분석 데이터 로드
    loadWeaknessAnalysis();
    
    // 오답 목록 로드
    loadMistakes();
});

// 탭 전환
function switchTab(tabName) {
    // 모든 탭 버튼 비활성화
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // 모든 탭 콘텐츠 숨김
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // 선택된 탭 활성화
    if (tabName === 'analysis') {
        document.querySelector('.tab:first-child').classList.add('active');
        document.getElementById('analysis-tab').classList.add('active');
    } else {
        document.querySelector('.tab:last-child').classList.add('active');
        document.getElementById('mistakes-tab').classList.add('active');
    }
}

// 약점 분석 데이터 로드
function loadWeaknessAnalysis() {
    fetch('/api/mistakes/analysis')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderWeaknessAnalysis(data.analysis);
            } else {
                console.error('약점 분석 로드 실패:', data.error);
            }
        })
        .catch(error => {
            console.error('약점 분석 로드 중 오류:', error);
        });
}

// 약점 분석 렌더링
function renderWeaknessAnalysis(analysis) {
    // 전체 오답 수
    document.getElementById('total-mistakes').textContent = analysis.total_mistakes || 0;
    
    // 문제 유형별 통계
    const typeStatsElem = document.getElementById('type-stats');
    typeStatsElem.innerHTML = '';
    
    if (analysis.weakness_by_type) {
        for (const [type, count] of Object.entries(analysis.weakness_by_type)) {
            if (count > 0) {
                const typeName = type === 'short' ? '서술형' : '객관식';
                const statItem = document.createElement('div');
                statItem.className = 'stat-item';
                statItem.innerHTML = `
                    <span>${typeName}</span>
                    <strong>${count}회</strong>
                `;
                typeStatsElem.appendChild(statItem);
            }
        }
    }
    
    if (typeStatsElem.children.length === 0) {
        typeStatsElem.innerHTML = '<p style="color: #666; padding: 10px;">오답 데이터가 없습니다.</p>';
    }
    
    // 강의별 통계
    const lectureStatsElem = document.getElementById('lecture-stats');
    lectureStatsElem.innerHTML = '';
    
    if (analysis.weakness_by_lecture && Object.keys(analysis.weakness_by_lecture).length > 0) {
        for (const [lectureId, count] of Object.entries(analysis.weakness_by_lecture)) {
            const statItem = document.createElement('div');
            statItem.className = 'stat-item';
            statItem.innerHTML = `
                <span>강의 ID: ${lectureId}</span>
                <strong>${count}회</strong>
            `;
            lectureStatsElem.appendChild(statItem);
        }
    } else {
        lectureStatsElem.innerHTML = '<p style="color: #666; padding: 10px;">강의별 오답 데이터가 없습니다.</p>';
    }
    
    // 학습 추천
    const recommendationsElem = document.getElementById('recommendations');
    recommendationsElem.innerHTML = '';
    
    if (analysis.recommendations && analysis.recommendations.length > 0) {
        analysis.recommendations.forEach(rec => {
            const recItem = document.createElement('div');
            recItem.className = `recommendation ${rec.priority || 'medium'}`;
            recItem.textContent = rec.message;
            recommendationsElem.appendChild(recItem);
        });
    } else {
        recommendationsElem.innerHTML = '<p style="color: #666; padding: 10px;">추천 사항이 없습니다. 모든 문제를 정확히 풀고 계시네요!</p>';
    }
}

// 오답 목록 로드
function loadMistakes() {
    fetch('/api/mistakes')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderMistakes(data.mistakes);
            } else {
                console.error('오답 목록 로드 실패:', data.error);
                document.getElementById('mistakes-list').innerHTML = 
                    '<div class="no-mistakes"><p>오답 목록을 불러오는 중 오류가 발생했습니다.</p></div>';
            }
        })
        .catch(error => {
            console.error('오답 목록 로드 중 오류:', error);
            document.getElementById('mistakes-list').innerHTML = 
                '<div class="no-mistakes"><p>오답 목록을 불러오는 중 오류가 발생했습니다.</p></div>';
        });
}

// 오답 목록 렌더링
function renderMistakes(mistakes) {
    const mistakesListElem = document.getElementById('mistakes-list');
    
    if (!mistakes || mistakes.length === 0) {
        mistakesListElem.innerHTML = `
            <div class="no-mistakes">
                <h3>오답이 없습니다!</h3>
                <p>모든 문제를 정확히 풀고 계시네요. 계속 좋은 성적을 유지하세요!</p>
            </div>
        `;
        return;
    }
    
    mistakesListElem.innerHTML = '';
    
    mistakes.forEach((mistake, index) => {
        const mistakeItem = document.createElement('div');
        mistakeItem.className = 'mistake-item';
        
        const questionType = mistake.question_type === 'short' ? '서술형' : '객관식';
        const examDate = mistake.exam_date ? formatDate(mistake.exam_date) : '날짜 정보 없음';
        
        let optionsHTML = '';
        if (mistake.options && mistake.question_type === 'multiple') {
            optionsHTML = `
                <div style="margin-top: 10px;">
                    <strong>선택지:</strong>
                    <ul style="margin: 8px 0; padding-left: 20px;">
                        ${mistake.options.map((opt, idx) => `<li>${idx + 1}. ${opt}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        let userAnswerDisplay = mistake.user_answer || '(답변 없음)';
        let correctAnswerDisplay = mistake.correct_answer || '(정답 정보 없음)';
        
        // 객관식 문제인 경우 선택지 번호를 텍스트로 변환
        if (mistake.question_type === 'multiple' && mistake.options) {
            const userAnswerNum = parseInt(mistake.user_answer);
            const correctAnswerNum = parseInt(mistake.correct_answer);
            
            if (!isNaN(userAnswerNum) && mistake.options[userAnswerNum]) {
                userAnswerDisplay = `${userAnswerNum + 1}. ${mistake.options[userAnswerNum]}`;
            }
            
            if (!isNaN(correctAnswerNum) && mistake.options[correctAnswerNum]) {
                correctAnswerDisplay = `${correctAnswerNum + 1}. ${mistake.options[correctAnswerNum]}`;
            }
        }
        
        mistakeItem.innerHTML = `
            <div class="mistake-header">
                <div>
                    <span class="mistake-type">${questionType}</span>
                    <span style="margin-left: 10px; font-weight: bold;">문제 ${index + 1}</span>
                </div>
                <span class="mistake-date">${examDate}</span>
            </div>
            <div class="question-text" style="margin-bottom: 15px;">
                ${mistake.question_text || '문제 내용 없음'}
            </div>
            ${optionsHTML}
            <div class="answer-comparison">
                <div class="answer-box user-answer">
                    <div class="answer-label">내 답안</div>
                    <div class="answer-content">${userAnswerDisplay}</div>
                </div>
                <div class="answer-box correct-answer">
                    <div class="answer-label">정답</div>
                    <div class="answer-content">${correctAnswerDisplay}</div>
                </div>
            </div>
        `;
        
        mistakesListElem.appendChild(mistakeItem);
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

