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

function submitAnswer(selectedOption, question) {
    // AJAX call to submit the answer and handle the response
    // Example:
    fetch('/submit_answer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ answer: selectedOption, questionText: question.text })
    })
    .then(response => response.json())
    .then(data => {
        // Handle response (display feedback and explanation)
    })
    .catch(error => console.error('Error:', error));
}


// Add event listeners for keypress or button click events
document.addEventListener('keydown', (event) => {
    if (event.key === 'A' || event.key === 'S' || event.key === 'D' || event.key === 'F') {
        submitAnswer(event.key);
    }
});
