rom flask import Blueprint, jsonify, request, current_app, render_template, session
from app import socketio  # Import the socketio instance
from flask_socketio import emit, join_room,SocketIO
import json
import time
from threading import Thread

game_bp = Blueprint('game', __name__)

# Redis Keys
QUIZ_PLAYERS_KEY = "quiz:{quiz_id}:players"
QUIZ_ANSWERS_KEY = "quiz:{quiz_id}:answers"
QUIZ_CURRENT_QUESTION_KEY = "quiz:{quiz_id}:current_question"

# WebSocket event for real-time quiz
@game_bp.route('/quiz/<quiz_id>/start_dynamics', methods=['POST'])
def start_quiz_dynamics(quiz_id):
    """Start the quiz dynamics and broadcast questions in real-time."""
    redis_client = current_app.redis_client
    quiz_data = redis_client.get(f"quiz:{quiz_id}")
    if not quiz_data:
        return jsonify({"error": "Quiz data not found"}), 404
    quiz_data = json.loads(quiz_data)

    questions = quiz_data.get('questions', [])
    if not questions:
        return jsonify({"error": "No questions available in the quiz"}), 400

    def broadcast_questions(app):
        with app.app_context():
            for idx, question in enumerate(questions):
                redis_client.set(QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id), idx)
                socketio.emit('question', {
                    'question_id': idx,
                    'question': question
                }, room=f'quiz_{quiz_id}')
                # Print the question being broadcasted
                print(f"Broadcasting question {idx}: {question}")
                time.sleep(20)
            socketio.emit('quiz_finished', {"message": "Quiz finished"}, room=f'quiz_{quiz_id}')

    Thread(target=broadcast_questions, args=(current_app._get_current_object(),)).start()

    return jsonify({"message": "Quiz started"}), 200




@game_bp.route('/quiz/<quiz_id>/join', methods=['GET', 'POST'])
def join_quiz(quiz_id):
    redis_client = current_app.redis_client

    if request.method == 'GET':
        return render_template('game.html', quiz_id=quiz_id)
    
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

@socketio.on('join_quiz_room')
def handle_join_quiz_room(data):
    quiz_id = data.get('quiz_id')
    username = data.get('username')
    if not quiz_id or not username:
        return emit('error', {'error': 'Quiz ID and username are required.'})
    
    room = f'quiz_{quiz_id}'
    join_room(room)
    emit('room_joined', {'message': f'{username} joined {room}'}, room=room)

@game_bp.route('/quiz/<quiz_id>/submit_answer', methods=['POST'])
def submit_answer(quiz_id):
    """Submit an answer for the current question."""
    username = request.json.get('username')
    answer_id = request.json.get('answer_id')
    if not username or not answer_id:
        return jsonify({"error": "Username and answer_id are required"}), 400

    redis_client = current_app.redis_client
    current_question_idx = int(redis_client.get(QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id)) or 0)
    answers_key = QUIZ_ANSWERS_KEY.format(quiz_id=quiz_id)
    redis_client.hset(answers_key, f"{current_question_idx}:{username}", json.dumps({
        "answer_id": answer_id,
        "timestamp": time.time()
    }))
    return jsonify({"message": "Answer submitted"}), 200