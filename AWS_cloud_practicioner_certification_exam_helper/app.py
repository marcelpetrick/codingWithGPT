 
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
        # Remove the leading "- " from each option
        options = [line.strip()[2:] for line in lines[2:6]]
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
    print(f"Question: {question['text']}")
    # Send only the text and options to the client
    client_question = {
        'text': question['text'],
        'options': question['options']
    }
    return jsonify(question=client_question)


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.json
    submitted_answer = data['answer']
    print(f"Submitted answer: {submitted_answer}")
    question_text = data['questionText']
    print(f"Question text: {question_text}")

    # Find the question in the list
    question = next((q for q in questions if q['text'] == question_text), None)

    if question:
        # Extract the first character (A, B, C, or D) from the submitted answer
        submitted_answer_char = submitted_answer.strip()[0].upper()
        print(f"Submitted answer char: {submitted_answer_char}")

        # Compare with the correct answer
        is_correct = submitted_answer_char == question['answer']
        print(f"Is correct: {is_correct}")
        explanation = question['explanation']
        result = {'is_correct': is_correct, 'explanation': explanation}
    else:
        result = {'error': 'Question not found'}

    print(f"result: {result}")
    return jsonify(result)
