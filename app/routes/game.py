from flask import Blueprint, jsonify, request, current_app, render_template, session
import json
import time
from threading import Thread

game_bp = Blueprint('game', __name__)

QUIZ_PLAYERS_KEY = "quiz:{quiz_id}:players"
QUIZ_ANSWERS_KEY = "quiz:{quiz_id}:answers"
QUIZ_CURRENT_QUESTION_KEY = "quiz:{quiz_id}:current_question"

@game_bp.route('/_refresh',methods=['GET','POST'])  # 5
def refresh():
    if request.method == 'GET': 
        print('DEBUG: Refresh requested')

        quiz_id = '46ba8128-e3a3-4b53-9a39-c5c64d9eacab'

        # Obter dados do quiz do Redis
        redis_client = current_app.redis_client
        quiz_data = redis_client.get(f"quiz:{quiz_id}")

        if not quiz_data:
            return jsonify({"error": "Quiz data not found"}), 404
        
        quiz_data = json.loads(quiz_data)

        if not quiz_data or 'questions' not in quiz_data:
            return jsonify({"error": "No questions available in the quiz"}), 400

        # Obter o índice da próxima pergunta, incrementando a cada refresh
        current_question_idx = redis_client.incr(f"quiz:{quiz_id}:current_question")

        questions = quiz_data['questions']

        print(current_question_idx-1)
        print(len(questions))
        # Se o índice ultrapassou o número de perguntas, finalizar o quiz
        if current_question_idx - 1 >= len(questions):
            redis_client.delete(f"quiz:{quiz_id}:current_question")
            redis_client.delete(f"quiz:{quiz_id}")
            return jsonify({"message": "Quiz completed!"}), 200

        # Pega a pergunta correspondente ao índice atual
        question = questions[current_question_idx - 1]
        

        

        # Construir a resposta para enviar ao cliente
        response = {
            'status': 'Success',
            'data': question['question_text']
        }

        print(f'DEBUG: Sending question {response}')
        return jsonify(response)
  
    
@game_bp.route('/quiz/join')
def main():
    print(f'DEBUG: Sending main page')
    return render_template('game.html')

@game_bp.route('/quiz/end')
def end():
    return '<h1>FIM DESTA MERDA</h1>'


