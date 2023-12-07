document.addEventListener('DOMContentLoaded', () => {
    loadQuestion();
});

function loadQuestion() {
    // Implement AJAX call to Flask backend to load a question
    // Update the DOM with the question and options
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
