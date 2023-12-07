 
from flask import Flask, render_template, jsonify, request
import random, json

app = Flask(__name__)


def parse_questions(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    questions_blocks = content.split('\n\n')  # Split by double newline
    questions = []

    for block in questions_blocks:
        lines = block.strip().split('\n')

        if len(lines) < 8:
            continue  # Skip blocks that don't have enough lines

        question_text = lines[1]
        options = lines[2:6]
        correct_answer = lines[6].split(':')[-1].strip()[-1]  # More robust parsing
        explanation = lines[7].split(':', 1)[-1].strip()

        question = {
            'text': question_text,
            'options': options,
            'answer': correct_answer,
            'explanation': explanation
        }
        questions.append(question)

    return questions


questions = parse_questions('questions.md')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_question', methods=['GET'])
def get_question():
    question = random.choice(questions)
    return jsonify(question=question)

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.json
    # Logic to verify answer and return correctness and explanation
    return jsonify(result=result, explanation=explanation)
