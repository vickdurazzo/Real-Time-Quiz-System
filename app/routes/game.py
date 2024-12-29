from flask import Blueprint, jsonify, request, current_app, render_template, session
import json
import time
from app.models import db, User,Quiz,Question,Answer
from threading import Thread

game_bp = Blueprint('game', __name__)

QUIZ_PLAYERS_KEY = "quiz:{quiz_id}:players"
QUIZ_PLAYERS_KEY_READY = "quiz:{quiz_id}:players:ready_players"
QUIZ_ANSWERS_KEY = "quiz:{quiz_id}:answers"
QUIZ_CURRENT_QUESTION_KEY = "quiz:{quiz_id}:current_question"


###STEP DO JOGO ###

@game_bp.route('/quiz/<quiz_id>/join', methods=['GET', 'POST']) #jogadores entram e se cadastram
def join_quiz(quiz_id):
    redis_client = current_app.redis_client

    if request.method == 'GET':
        return render_template('join_quiz.html', quiz_id=quiz_id) #renderiza a tela de entrada para o jogo
    
    if request.method == 'POST':
        username = request.json.get('username')
        if not username:
            return jsonify({"error": "Username is required"}), 400

        players_key = QUIZ_PLAYERS_KEY.format(quiz_id=quiz_id)
        if redis_client.sismember(players_key, username):
            return jsonify({"error": "Username is already taken"}), 400

        redis_client.sadd(players_key, username)
        session['username'] = username  # Store username in session
        
        return jsonify({"message": "Player registered successfully"}), 200
    

@game_bp.route('/quiz/<quiz_id>/start_dynamics', methods=['GET','POST'])
def start_quiz_dynamics(quiz_id):
    """Start the quiz dynamics and broadcast questions in real-time."""
    redis_client = current_app.redis_client
    if request.method == 'GET':
        game_started = redis_client.get(f"quiz:{quiz_id}:started")
        return jsonify({"message":game_started})
    
    if request.method == 'POST':
        redis_client = current_app.redis_client
        quiz_data = redis_client.get(f"quiz:{quiz_id}")
        if not quiz_data:
            return jsonify({"error": "Quiz data not found"}), 404
        
        quiz_data = json.loads(quiz_data)
        questions = quiz_data.get('questions', [])
        if not questions:
            return jsonify({"error": "No questions available in the quiz"}), 400
        
        redis_client.set(QUIZ_CURRENT_QUESTION_KEY,0)
        redis_client.set(f"quiz:{quiz_id}:started",1)

        return jsonify({"message": "Quiz started"}), 200

@game_bp.route('/quiz/<quiz_id>/<username>/mark_ready', methods=['POST'])
def mark_ready(quiz_id,username):
    redis_client = current_app.redis_client
    if not username:
        return jsonify({"error": "User  not logged in"}), 403

    ready_players_key = QUIZ_PLAYERS_KEY_READY.format(quiz_id=quiz_id)
    # Add the player to the ready players set
    redis_client.sadd(ready_players_key, username)

    return jsonify({"message": f"{username} is now ready!"}), 200

@game_bp.route('/quiz/<quiz_id>/<username>/confirm_question', methods=['POST'])
def confirm_question(quiz_id, username):
    """Marks a player's confirmation for the current question."""
    redis_client = current_app.redis_client

    if not username:
        return jsonify({"error": "User not logged in"}), 403

    current_question_idx = redis_client.get(QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id))
    if not current_question_idx:
        return jsonify({"error": "No question being displayed currently"}), 400

    confirmation_key = f"quiz:{quiz_id}:question:{current_question_idx}:confirmations"
    redis_client.sadd(confirmation_key, username)

    # Check if all players have confirmed
    players_key = f"quiz:{quiz_id}:players"
    total_players = redis_client.scard(players_key)
    confirmed_players = redis_client.scard(confirmation_key)

    if confirmed_players == total_players:
        # Clear confirmation set and proceed to next question
        redis_client.delete(confirmation_key)
        redis_client.incr(QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id))

    return jsonify({"message": f"{username} confirmed the question"}), 200


@game_bp.route('/quiz/<quiz_id>/<username>/game')
def game(quiz_id,username):
    print(f'DEBUG: Sending main page')
    return render_template('game.html',quiz_id=quiz_id,username=username)




@game_bp.route('/_refresh', methods=['GET', 'POST'])
def refresh():
    """Refresh the question for players."""
    if request.method == 'GET':
        print('DEBUG: Refresh requested')
        redis_client = current_app.redis_client
        quiz_id = '46ba8128-e3a3-4b53-9a39-c5c64d9eacab'
        # Check if all players are ready
        players_key = f"quiz:{quiz_id}:players"
        ready_players = redis_client.smembers(QUIZ_PLAYERS_KEY_READY.format(quiz_id=quiz_id))
        total_players = redis_client.scard(players_key)

        if len(ready_players) < total_players:
            return jsonify({"data": "Waiting for all players to be ready."}), 200
        else:
            #time.sleep(5)
            quiz_data = redis_client.get(f"quiz:{quiz_id}")

            if not quiz_data:
                return jsonify({"error": "Quiz data not found"}), 404
            
            quiz_data = json.loads(quiz_data)

            if not quiz_data or 'questions' not in quiz_data:
                return jsonify({"error": "No questions available in the quiz"}), 400

            # Obter o índice da próxima pergunta, incrementando a cada refresh
            current_question_idx = redis_client.incr(QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id))

            questions = quiz_data['questions']

            print(current_question_idx-1)
            print(len(questions))
            # Se o índice ultrapassou o número de perguntas, finalizar o quiz
            if current_question_idx - 1 >= len(questions):
                #redis_client.delete(f"quiz:{quiz_id}:current_question")
                #redis_client.delete(f"quiz:{quiz_id}")
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
        
        
@game_bp.route('/quiz/end')
def end():
    return '<h1>FIM DESTA MERDA</h1>'




"""
@game_bp.route('/_refresh', methods=['GET', 'POST'])
def refresh():
    if request.method == 'GET':
        print('DEBUG: Refresh requested')
        redis_client = current_app.redis_client
        quiz_id = '46ba8128-e3a3-4b53-9a39-c5c64d9eacab'
        # Check if all players are ready
        players_key = f"quiz:{quiz_id}:players"
        ready_players = redis_client.smembers(QUIZ_PLAYERS_KEY_READY.format(quiz_id=quiz_id))
        total_players = redis_client.scard(players_key)

        if len(ready_players) < total_players:
            return jsonify({"data": "Waiting for all players to be ready."}), 200
        else:
            #time.sleep(5)
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

"""




