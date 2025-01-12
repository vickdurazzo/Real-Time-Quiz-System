from flask import Blueprint, request, session, jsonify, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, db

# Criação de um Blueprint chamado 'auth', responsável por agrupar rotas relacionadas à autenticação de usuários
auth_bp = Blueprint('auth', __name__)

# Rota para entrada do usuário (login)
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Função de visualização para realizar o login do usuário.

    Quando a requisição é feita com o método GET, a página de login (`login.html`) é renderizada.
    Quando a requisição é feita com o método POST, o sistema tenta autenticar o usuário com as credenciais fornecidas.

    A função realiza as seguintes ações:
    1. Verifica se a requisição é no formato JSON.
    2. Extrai o nome de usuário e senha do corpo da requisição JSON.
    3. Verifica se o nome de usuário existe no banco de dados.
    4. Se o nome de usuário for encontrado, verifica se a senha informada é válida comparando com o hash da senha armazenado.
    5. Caso as credenciais sejam válidas, armazena o ID do usuário na sessão.
    6. Se a requisição for para uma API (solicitando JSON), retorna uma resposta com status 200 e o ID do usuário.
    7. Se a requisição for para um navegador, redireciona o usuário para a página inicial (rota `home.home`).

    Exceções:
    - Se ocorrer algum erro, uma resposta JSON com a mensagem de erro será retornada com status 500.
    - Caso as credenciais sejam inválidas, retorna uma mensagem de erro com status 401.
    """
    if request.method == 'POST':
        try:
            if not request.is_json:
                return jsonify({"message": "Request must be JSON"}), 415

            data = request.get_json()
            
            username = data.get('username')
            password = data.get('password')

            # Verifica se o usuário existe no banco de dados
            user = User.query.filter_by(nm_user=username).first()
            
            if user and check_password_hash(user.des_user_passwd, password):
                session['user_id'] = user.user_id
                # Retorna resposta JSON para APIs
                if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
                    return jsonify({"message": "Login successfully", "user_id": session['user_id']}), 200
                
                # Redireciona o usuário para a página inicial
                return redirect(url_for('home.home'))
            else:
                return jsonify({"message": "Invalid credentials"}), 401
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    # Se a requisição for GET, renderiza o formulário de login
    return render_template('login.html')


# Rota para registro de um novo usuário
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Função de visualização para registrar um novo usuário.

    Quando a requisição é feita com o método GET, a página de registro (`register.html`) é renderizada.
    Quando a requisição é feita com o método POST, o sistema cria um novo usuário com as credenciais fornecidas.

    A função realiza as seguintes ações:
    1. Verifica se a requisição é no formato JSON.
    2. Extrai o nome de usuário e a senha do corpo da requisição JSON.
    3. Gera um hash seguro da senha usando o algoritmo 'pbkdf2:sha256'.
    4. Cria um novo usuário no banco de dados com o nome de usuário e a senha hashada.
    5. Adiciona o novo usuário ao banco de dados e faz o commit.

    Exceções:
    - Se ocorrer algum erro, a transação é revertida e uma mensagem de erro é retornada com status 500.
    """
    if request.method == 'POST':
        try:
            if not request.is_json:
                return jsonify({"message": "Request must be JSON"}), 415

            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            # Cria um novo usuário
            new_user = User(nm_user=username, des_user_passwd=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            return jsonify({"message": "User registered successfully!"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Error: {str(e)}"}), 500

    # Se a requisição for GET, renderiza o formulário de registro
    return render_template('register.html')


# Rota para logout do usuário
@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Função para realizar o logout do usuário.

    A função realiza as seguintes ações:
    1. Remove o ID do usuário da sessão, efetivamente desconectando-o.
    2. Retorna uma resposta JSON com status 200, confirmando o logout.

    Exceções:
    - Não há exceções específicas tratadas nesta função.
    """
    session.pop('user_id', None)
    return jsonify({"message": "User logout successfully!"}), 200
