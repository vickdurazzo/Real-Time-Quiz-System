from flask import Blueprint, jsonify, request, current_app, render_template, session
import json
import time
from app.models import db, User,Quiz,Question,Answer
from threading import Thread

@game_bp.route('/quiz/<quiz_id>/<username>/confirm_question', methods=['POST'])
    def confirm_question(quiz_id, username):
        """Marks a player's confirmation for the current question."""
        redis_client = current_app.redis_client
    
        if not username:
            return jsonify({"error": "User not logged in"}), 403
    
        current_question_idx = redis_client.get(f"quiz:{quiz_id}:current_question")
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
            redis_client.incr(f"quiz:{quiz_id}:current_question")
    
        return jsonify({"message": f"{username} confirmed the question"}), 200
    
    
    @game_bp.route('/_refresh', methods=['GET', 'POST'])
    def refresh():
        """Refresh the question for players."""
        redis_client = current_app.redis_client
        quiz_id = '46ba8128-e3a3-4b53-9a39-c5c64d9eacab'
    
        # Retrieve quiz data
        quiz_data = redis_client.get(f"quiz:{quiz_id}")
        if not quiz_data:
            return jsonify({"error": "Quiz data not found"}), 404
    
        quiz_data = json.loads(quiz_data)
        if 'questions' not in quiz_data:
            return jsonify({"error": "No questions available in the quiz"}), 400
    
        # Get the current question index
        current_question_idx = redis_client.get(f"quiz:{quiz_id}:current_question")
        current_question_idx = int(current_question_idx) if current_question_idx else 0
    
        questions = quiz_data['questions']
    
        if current_question_idx >= len(questions):
            # End of quiz
            redis_client.delete(f"quiz:{quiz_id}:current_question")
            redis_client.delete(f"quiz:{quiz_id}")
            return jsonify({"message": "Quiz completed!"}), 200
    
        # Get the current question
        question = questions[current_question_idx]
    
        response = {
            'status': 'Success',
            'data': question['question_text'],
        }
        return jsonify(response)
    