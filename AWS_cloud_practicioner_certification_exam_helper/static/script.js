document.addEventListener('DOMContentLoaded', () => {
    loadQuestion();
});

function loadQuestion() {
    console.log("Loading question");
    fetch('/get_question')
        .then(response => response.json())
        .then(data => {
            displayQuestion(data.question);
        })
        .catch(error => console.error('Error:', error));
}

function displayQuestion(question) {
    console.log("Displaying question");
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

function displayFeedback(data, selectedOptionButton) {
    console.log("Displaying feedback");
    // Add class to the selected option
    selectedOptionButton.classList.add('selected');

    // Find and mark the correct option
    const options = document.getElementsByClassName('option');
    Array.from(options).forEach(option => {
        if (option.textContent === data.correct_answer) {
            option.classList.add('correct');
        }
    });

    // Display feedback
    const feedbackDiv = document.getElementById('feedback');
    feedbackDiv.innerHTML = `Your answer is ${data.is_correct ? 'correct' : 'incorrect'}.<br><br>Explanation: ${data.explanation}`;
}

let correctAnswers = 0;
let totalQuestions = 0;

function updateStatistics(isCorrect) {
    console.log("Updating statistics");
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
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ answer: selectedOption, questionText: question.text })
    })
    .then(response => response.json())
    .then(data => {
        // Find the clicked button element
        const selectedOptionButton = Array.from(document.getElementsByClassName('option')).find(button => button.textContent === selectedOption);
        displayFeedback(data, selectedOptionButton);
        updateStatistics(data.is_correct);
        setTimeout(loadQuestion, 3000); // Load next question after a delay
    })
    .catch(error => console.error('Error:', error));
}

document.addEventListener('keydown', (event) => {
    console.log("Key pressed:", event.key);
    //const keyToOptionMap = { 'A': 0, 'S': 1, 'D': 2, 'F': 3 };
    const keyToOptionMap = { 'A': 0, 'a':0, 'S': 1, 's':1, 'D': 2, 'd': 2, 'F': 3, 'f':3 };
    if (event.key.toUpperCase() in keyToOptionMap) {
        const optionsButtons = document.querySelectorAll('.option');
        if (optionsButtons.length > keyToOptionMap[event.key.toUpperCase()]) {
            const selectedOptionButton = optionsButtons[keyToOptionMap[event.key.toUpperCase()]];
            console.log("Selected option:", selectedOptionButton.textContent);
            const selectedOptionText = selectedOptionButton.textContent;
            console.log("Selected option text:", selectedOptionText);
            submitAnswer(selectedOptionText, { text: document.getElementById('question').textContent });
        }
    }
});


window.addEventListener('keydown', (event) => {
    console.log("window listener: Key pressed:", event.key);
});


console.log("Script loaded and running");
