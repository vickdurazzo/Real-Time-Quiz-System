from flask import Blueprint, jsonify,session,request,render_template
from app.services.redis_service import handle_player_join, initialize_quiz,broadcast_question, ranking_final, submit_player_answer

game_bp = Blueprint('game', __name__)

@game_bp.route('/start_quiz/<quiz_id>', methods=['GET', 'POST'])  # INICIAR O QUIZ
def start_quiz(quiz_id):
    """Start the quiz dynamics and broadcast questions in real-time."""
    
    if request.method == 'GET':
        game_started = initialize_quiz(quiz_id)
        return jsonify({"message":game_started})
    
    if request.method == 'POST':
        try:
            print('requisicao post')
            broadcast_question(quiz_id)
            return jsonify({"message": "Quiz started and questions are being sent"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        

@game_bp.route('/quiz/<quiz_id>/join', methods=['GET', 'POST']) #jogadores entram e se cadastram
def join_quiz(quiz_id):
    """Join the quiz and get the player's data."""

    if request.method == 'GET':
        return render_template('join_quiz.html', quiz_id=quiz_id) #renderiza a tela de entrada para o jogo
    
    if request.method == 'POST':
        return handle_player_join(quiz_id,request.json)


@game_bp.route('/quiz/<quiz_id>/<username>/game')
def game(quiz_id,username):
    return render_template('game.html',quiz_id=quiz_id,username=username)

@game_bp.route('/quiz/<quiz_id>/submit_answer', methods=['POST'])
def submit_answer(quiz_id):
    """Submit an answer for the current question."""
    try:
        print("Resposta enviada")
        return submit_player_answer(quiz_id, request.json)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@game_bp.route('/<quiz_id>/results', methods=['GET'])  
def ranking(quiz_id):
    """Return the ranking of players in the quiz."""
    try:
        return jsonify({"ranking": ranking_final(quiz_id)}),200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
                    