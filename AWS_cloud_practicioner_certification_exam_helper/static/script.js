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
    // Implement the logic to display the question and options in the HTML
    // For example:
    document.getElementById('question').textContent = question.text;
    // And similarly for options...
}


function submitAnswer(answer) {
    // Implement logic to submit answer and handle response
}

// Add event listeners for keypress or button click events
document.addEventListener('keydown', (event) => {
    if (event.key === 'A' || event.key === 'S' || event.key === 'D' || event.key === 'F') {
        submitAnswer(event.key);
    }
});
