 
from flask import Flask, render_template, jsonify, request
import random, json

app = Flask(__name__)

def load_questions():
    with open('questions.txt', 'r') as file:
        questions = [line.strip().split(';') for line in file]
    return questions

questions = load_questions()


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
