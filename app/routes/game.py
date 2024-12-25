from flask import Blueprint, jsonify, request, session, current_app
import uuid
import time
import json
from datetime import datetime

game_bp = Blueprint('game', __name__)

# Redis Keys
QUIZ_PLAYERS_KEY = "quiz:{quiz_id}:players"
QUIZ_ANSWERS_KEY = "quiz:{quiz_id}:answers"
QUIZ_CURRENT_QUESTION_KEY = "quiz:{quiz_id}:current_question"

@game_bp.route('/quiz/<quiz_id>/join', methods=['GET', 'POST'])
def join_quiz(quiz_id):
    redis_client = current_app.redis_client
    quiz_key = f'quiz:{quiz_id}'
    
    if redis_client.get(quiz_key):
        if request.method == 'GET':
            return jsonify({"message": "Let's join the game"}), 200
        
        if request.method == 'POST':
            #Player joins the quiz with a unique username.
            username = request.json.get('username')
            if not username:
                return jsonify({"error": "Username is required"}), 400
            
            players_key = QUIZ_PLAYERS_KEY.format(quiz_id=quiz_id)
            
            # Check if username is already taken
            existing_players = redis_client.smembers(players_key)
            if username in existing_players:
                return jsonify({"error": "Username is already taken"}), 400
            
            # Add player to the set of participants
            redis_client.sadd(players_key, username)
            
            return jsonify({"message": "Player registered successfully"}), 200
    else:
        return jsonify({"message": "Game not started"}), 404


    


@game_bp.route('/quiz/<quiz_id>/start_dynamics', methods=['POST'])
def start_quiz_dynamics(quiz_id):
    """Start the quiz dynamics."""
    redis_client = current_app.redis_client
    quiz_key = QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id)
    
    # Fetch quiz data from Redis
    quiz_data = redis_client.get(f"quiz:{quiz_id}")
    if not quiz_data:
        return jsonify({"error": "Quiz data not found"}), 404
    quiz_data = json.loads(quiz_data)
    
    questions = quiz_data.get('questions', [])
    if not questions:
        return jsonify({"error": "No questions available in the quiz"}), 400
    
    # Start the quiz: send first question to clients
    redis_client.set(quiz_key, 0)  # Store index of the current question
    current_question = questions[0]
    return jsonify({"message": "Quiz started", "current_question": current_question}), 200




@game_bp.route('/quiz/<quiz_id>/submit_answer', methods=['POST'])
def submit_answer(quiz_id):
    """Submit an answer for the current question."""
    username = request.json.get('username')
    answer_id = request.json.get('answer_id')
    if not username or not answer_id:
        return jsonify({"error": "Username and answer_id are required"}), 400
    
    redis_client = current_app.redis_client
    players_key = QUIZ_PLAYERS_KEY.format(quiz_id=quiz_id)
    if not redis_client.sismember(players_key, username):
        return jsonify({"error": "Player not registered"}), 400
    
    # Captura o índice da pergunta atual
    current_question_idx = int(redis_client.get(QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id)) or 0)
    
    # Verifica se o jogador já respondeu à pergunta atual
    answers_key = QUIZ_ANSWERS_KEY.format(quiz_id=quiz_id)
    if redis_client.hexists(answers_key, f"{current_question_idx}:{username}"):
        return jsonify({"error": "You have already submitted an answer for this question"}), 403
    
    # Captura o timestamp atual
    submission_time = datetime.utcnow().isoformat()  # Usa UTC para consistência
    
    # Armazena a resposta e o timestamp no Redis
    answer_record = {
        "answer_id": answer_id,
        "timestamp": submission_time
    }
    redis_client.hset(answers_key, f"{current_question_idx}:{username}", json.dumps(answer_record))
    
    return jsonify({"message": "Answer submitted", "timestamp": submission_time}), 200



@game_bp.route('/quiz/<quiz_id>/next_question', methods=['POST'])
def next_question(quiz_id):
    """Advance to the next question if time expires or all players answer."""
    redis_client = current_app.redis_client
    quiz_key = QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id)
    quiz_data = redis_client.get(f"quiz:{quiz_id}")
    if not quiz_data:
        return jsonify({"error": "Quiz data not found"}), 404
    quiz_data = json.loads(quiz_data)

    current_question_idx = int(redis_client.get(quiz_key) or 0)
    questions = quiz_data.get('questions', [])
    
    if current_question_idx >= len(questions) - 1:
        return jsonify({"message": "Quiz finished"}), 200
    
    # Advance to the next question
    current_question_idx += 1
    redis_client.set(quiz_key, current_question_idx)
    current_question = questions[current_question_idx]
    
    return jsonify({"message": "Next question", "current_question": current_question}), 200


    