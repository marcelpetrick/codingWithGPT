document.addEventListener('DOMContentLoaded', () => {
    loadQuestion();
});

function loadQuestion() {
    fetch('/get_question')
        .then(response => response.json())
        .then(data => {
            displayQuestion(data.question);
        })
        .catch(error => console.error('Error:', error));
}

function displayQuestion(question) {
    // Display the question text
    document.getElementById('question').textContent = question.text;

    // Clear previous options
    const optionsDiv = document.getElementById('options');
    optionsDiv.innerHTML = '';

    // Create and display options
    question.options.forEach((option, index) => {
        const button = document.createElement('button');
        button.textContent = option;
        button.classList.add('option');
        button.addEventListener('click', () => submitAnswer(option, question));
        optionsDiv.appendChild(button);
    });
}

function displayFeedback(data) {
    const feedbackDiv = document.getElementById('feedback');
    feedbackDiv.innerHTML = `Your answer is ${data.is_correct ? 'correct' : 'incorrect'}.<br>Explanation: ${data.explanation}`;
}

let correctAnswers = 0;
let totalQuestions = 0;

function updateStatistics(isCorrect) {
    totalQuestions++;
    if (isCorrect) {
        correctAnswers++;
    }
    const statsDiv = document.getElementById('stats'); // Make sure you have a stats div in your HTML
    statsDiv.textContent = `Score: ${correctAnswers} out of ${totalQuestions}`;
}

function submitAnswer(selectedOption, question) {
    console.log("Answer submitted:", selectedOption);
    fetch('/submit_answer', {
        method: 'POST', headers: {
            'Content-Type': 'application/json',
        }, body: JSON.stringify({answer: selectedOption, questionText: question.text})
    })
        .then(response => response.json())
        .then(data => {
            displayFeedback(data);
            updateStatistics(data.is_correct);
            setTimeout(loadQuestion, 3000); // Load next question after a delay
        })
        .catch(error => console.error('Error:', error));
}

// Add event listeners for keypress or button click events
document.addEventListener('keydown', (event) => {

    if (event.key === 'A' || event.key === 'S' || event.key === 'D' || event.key === 'F') {
        submitAnswer(event.key);
    }
});
