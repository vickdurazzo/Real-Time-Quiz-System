from flask import Blueprint, jsonify, request, session, render_template
from app.models import User, Quiz, db

# Criação de um Blueprint chamado 'home', responsável por agrupar rotas relacionadas à página inicial do aplicativo
home_bp = Blueprint('home', __name__)

# Rota para a página inicial, onde o usuário pode criar um novo quiz, visualizar os quizzes criados, acessar quizzes existentes, iniciar um jogo, entre outros
@home_bp.route('/', methods=['GET'])
def home():
    """
    Função de visualização da página inicial.
    
    Essa rota exibe uma lista de quizzes criados pelo usuário autenticado.
    Se a requisição for feita com um formato JSON, os quizzes serão retornados como um objeto JSON.
    Caso contrário, será renderizada a página HTML com os quizzes.

    A função realiza as seguintes ações:
    1. Recupera todos os quizzes criados pelo usuário atualmente logado, identificando-o via `session['user_id']`.
    2. Se não houver quizzes, uma lista vazia será retornada.
    3. Caso a requisição seja feita com o cabeçalho 'Accept: application/json' ou um parâmetro 'format=json', os quizzes são serializados para JSON e retornados com status 200.
    4. Se a requisição não for JSON, a página `home.html` é renderizada, exibindo a lista de quizzes.

    Exceções:
    - Em caso de erro, uma resposta JSON com a mensagem de erro será retornada com status 500.
    """
    try:
        # Recupera os quizzes do usuário atual
        quizzes = Quiz.query.filter_by(user_id=session['user_id']).all()
        
        # Se não houver quizzes, passa uma lista vazia
        if not quizzes:
            quizzes = []  
        
        # Verifica se a requisição foi feita em formato JSON
        if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
            # Serializa os quizzes para um formato JSON
            quizzes_serialized = [
                {
                    "quiz_id": quiz.quiz_id,
                    "title": quiz.title,
                    "is_active": quiz.is_active,
                }
                for quiz in quizzes
            ]
            return jsonify({"quizzes": quizzes_serialized}), 200

        # Caso contrário, renderiza a página HTML com os quizzes
        return render_template('home.html', quizzes=quizzes)
    
    except Exception as e:
        # Em caso de erro, retorna uma mensagem JSON com o erro
        return jsonify({"message": f"Error: {str(e)}"}), 500
