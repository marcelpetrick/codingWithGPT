from flask import Flask, render_template, jsonify, request
import random
import re

app = Flask(__name__)

def parse_questions_from_markdown(file_path):
    """
    Parse questions from a markdown file.

    Each question block in the file should contain the question text,
    four answer options, the correct answer, and an explanation.

    Args:
        file_path (str): The path to the markdown file.

    Returns:
        list: A list of dictionaries, each containing a question, options, answer, and explanation.
    """
    with open(file_path, 'r') as file:
        content = file.read()

    question_blocks = content.split('\n\n')
    parsed_questions = []

    for block in question_blocks:
        lines = block.strip().split('\n')

        if len(lines) < 8:
            continue

        question_text = lines[1]
        options = [line.strip()[2:] for line in lines[2:6]]
        correct_answer_match = re.search(r'Answer:\s*([A-Z])', lines[6])
        correct_answer = correct_answer_match.group(1) if correct_answer_match else ''
        explanation = lines[7].split(':', 1)[-1].strip()
        if explanation.startswith('** '):
            explanation = explanation[3:]

        question = {
            'text': question_text,
            'options': options,
            'answer': correct_answer,
            'explanation': explanation
        }
        parsed_questions.append(question)

    return parsed_questions

questions = parse_questions_from_markdown('questions.md')


@app.route('/')
def index():
    """
    Render the index page.
    """
    return render_template('index.html')

@app.route('/get_question', methods=['GET'])
def get_random_question():
    """
    Get a random question from the parsed questions.

    Returns:
        json: JSON object containing the question text and options.
    """
    question = random.choice(questions)
    client_question = {
        'text': question['text'],
        'options': question['options']
    }
    return jsonify(question=client_question)


@app.route('/submit_answer', methods=['POST'])
def submit_answer_and_get_feedback():
    """
    Submit an answer and receive feedback.

    Returns:
        json: JSON object containing the correctness of the answer and explanation.
    """
    data = request.json
    submitted_answer = data['answer']
    question_text = data['questionText']

    question = next((q for q in questions if q['text'] == question_text), None)

    if question:
        submitted_answer_char = submitted_answer.strip()[0].upper()
        is_correct = submitted_answer_char == question['answer']
        explanation = question['explanation']
        result = {'is_correct': is_correct, 'explanation': explanation}
    else:
        result = {'error': 'Question not found'}

    return jsonify(result)
