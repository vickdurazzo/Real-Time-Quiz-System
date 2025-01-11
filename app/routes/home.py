# Home routes
from flask import Blueprint, jsonify,request,session,render_template
from app.models import User,Quiz,db
home_bp = Blueprint('home', __name__)

@home_bp.route('/', methods=['GET'])
def home():
    try:
        quizzes = Quiz.query.filter_by(user_id=session['user_id']).all()
        if not quizzes:
            quizzes = []  # Pass an empty list if no quizzes exist
        # Retorno JSON prioritário
        if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
            # Serializar os quizzes em JSON-friendly
            quizzes_serialized = [
                {
                    "quiz_id": quiz.quiz_id,
                    "title": quiz.title,
                    "is_active": quiz.is_active,
                }
                for quiz in quizzes
            ]
            return jsonify({"quizzes": quizzes_serialized}), 200

        return render_template('home.html', quizzes=quizzes)
    except Exception as e:
        # Sempre retorno JSON para erros
        return jsonify({"message": f"Error: {str(e)}"}), 500
