// Event listener for DOM content load
document.addEventListener('DOMContentLoaded', () => {
    loadRandomQuestion();
});

// Load and display a random question
function loadRandomQuestion() {
    console.log("Loading question");
    fetch('/get_question')
        .then(response => response.json())
        .then(data => {
            displayQuestionOnPage(data.question);
        })
        .catch(error => console.error('Error:', error));
}

// Display a question and its options
function displayQuestionOnPage(question) {
    console.log("Displaying question");
    document.getElementById('question').textContent = question.text;

    const optionsDiv = document.getElementById('options');
    optionsDiv.innerHTML = '';

    question.options.forEach((option, index) => {
        const optionButton = createOptionButton(option, question);
        optionsDiv.appendChild(optionButton);
    });
}

// Create an option button
function createOptionButton(optionText, question) {
    const button = document.createElement('button');
    button.textContent = optionText;
    button.classList.add('option');
    button.addEventListener('click', () => submitAnswer(optionText, question));
    return button;
}

// Display feedback for the submitted answer
function displayFeedback(data, selectedOptionButton) {
    console.log("Displaying feedback");
    selectedOptionButton.classList.add('selected');

    const options = document.getElementsByClassName('option');
    Array.from(options).forEach(option => {
        if (option.textContent === data.correct_answer) {
            option.classList.add('correct');
        }
    });

    const feedbackDiv = document.getElementById('feedback');
    feedbackDiv.innerHTML = `Your answer is ${data.is_correct ? 'correct' : 'incorrect'}.<br><br>Explanation: ${data.explanation}`;
}

// Update score statistics
let correctAnswers = 0;
let totalQuestions = 0;

function updateScoreStatistics(isCorrect) {
    console.log("Updating statistics");
    totalQuestions++;
    if (isCorrect) {
        correctAnswers++;
    }
    const statsDiv = document.getElementById('stats');
    statsDiv.textContent = `Score: ${correctAnswers} out of ${totalQuestions}`;
}

// Submit an answer and process the response
function submitAnswer(selectedOption, question) {
    console.log("Answer submitted:", selectedOption);
    fetch('/submit_answer', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({answer: selectedOption, questionText: question.text})
    })
    .then(response => response.json())
    .then(data => {
        const selectedOptionButton = findButtonByText(selectedOption);
        displayFeedback(data, selectedOptionButton);
        updateScoreStatistics(data.is_correct);
        setTimeout(loadRandomQuestion, 3000);
    })
    .catch(error => console.error('Error:', error));
}

// Find a button by its text content
function findButtonByText(buttonText) {
    return Array.from(document.getElementsByClassName('option')).find(button => button.textContent === buttonText);
}

// Event listener for keydown actions
document.addEventListener('keydown', (event) => {
    console.log("Key pressed:", event.key);
    const keyToOptionMap = { 'A': 0, 'a': 0, 'S': 1, 's': 1, 'D': 2, 'd': 2, 'F': 3, 'f': 3 };
    if (keyToOptionMap.hasOwnProperty(event.key)) {
        const optionsButtons = document.querySelectorAll('.option');
        if (optionsButtons.length > keyToOptionMap[event.key]) {
            const selectedOptionButton = optionsButtons[keyToOptionMap[event.key]];
            console.log("Selected option:", selectedOptionButton.textContent);
            submitAnswer(selectedOptionButton.textContent, { text: document.getElementById('question').textContent });
        }
    }
});

console.log("Script loaded and running");
