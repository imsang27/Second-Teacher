document.addEventListener('DOMContentLoaded', function() {
    // 시험 통계 로드
    loadStatistics();
    
    // 시험 기록 목록 로드
    loadExamHistory();
});

// 시험 통계 로드
function loadStatistics() {
    fetch('/api/exam/statistics')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderStatistics(data.statistics);
            } else {
                console.error('통계 로드 실패:', data.error);
            }
        })
        .catch(error => {
            console.error('통계 로드 중 오류:', error);
        });
}

// 통계 렌더링
function renderStatistics(stats) {
    document.getElementById('totalExams').textContent = stats.total_exams || 0;
    document.getElementById('averageScore').textContent = (stats.average_score || 0) + '%';
    document.getElementById('bestScore').textContent = (stats.best_score || 0) + '%';
}

// 시험 기록 목록 로드
function loadExamHistory() {
    fetch('/api/exam/history')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderExamHistory(data.exams);
            } else {
                console.error('시험 기록 로드 실패:', data.error);
                document.getElementById('examList').innerHTML = 
                    '<div class="no-exams"><p>시험 기록을 불러오는 중 오류가 발생했습니다.</p></div>';
            }
        })
        .catch(error => {
            console.error('시험 기록 로드 중 오류:', error);
            document.getElementById('examList').innerHTML = 
                '<div class="no-exams"><p>시험 기록을 불러오는 중 오류가 발생했습니다.</p></div>';
        });
}

// 시험 기록 목록 렌더링
function renderExamHistory(exams) {
    const examListElem = document.getElementById('examList');
    
    if (!exams || exams.length === 0) {
        examListElem.innerHTML = `
            <div class="no-exams">
                <h3>시험 기록이 없습니다</h3>
                <p>시험을 응시하면 기록이 저장됩니다.</p>
            </div>
        `;
        return;
    }
    
    examListElem.innerHTML = '<div class="exam-list"></div>';
    const listContainer = examListElem.querySelector('.exam-list');
    
    exams.forEach((exam) => {
        const examItem = document.createElement('div');
        examItem.className = 'exam-item';
        
        const examDate = exam.exam_date ? formatDate(exam.exam_date) : '날짜 정보 없음';
        const totalQuestions = exam.total_questions || 0;
        const correctCount = exam.correct_count || 0;
        const score = totalQuestions > 0 ? Math.round((correctCount / totalQuestions) * 100) : 0;
        
        examItem.innerHTML = `
            <div class="exam-header">
                <div>
                    <h3 style="margin: 0;">시험 기록</h3>
                    <span class="exam-date">${examDate}</span>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 24px; font-weight: bold; color: #007bff;">${score}%</div>
                    <div style="font-size: 14px; color: #666;">${correctCount}/${totalQuestions}</div>
                </div>
            </div>
            <div class="exam-stats">
                <div class="stat-box">
                    <div class="stat-value">${exam.short_answer_correct || 0}/${exam.short_answer_total || 0}</div>
                    <div class="stat-label">서술형</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${exam.multiple_choice_correct || 0}/${exam.multiple_choice_total || 0}</div>
                    <div class="stat-label">객관식</div>
                </div>
            </div>
        `;
        
        examItem.addEventListener('click', () => {
            window.location.href = `/exam/history/${exam.id}`;
        });
        
        listContainer.appendChild(examItem);
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

