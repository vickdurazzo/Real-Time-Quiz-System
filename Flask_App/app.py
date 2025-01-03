from flask import Flask, render_template,jsonify,request, session,redirect,url_for
from flask_socketio import SocketIO, join_room, leave_room, emit,send
import uuid
from sqlalchemy.dialects.postgresql import UUID
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
import redis
import json
import threading
import time
from werkzeug.security import generate_password_hash, check_password_hash


# Inicializando o Flask e o SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:1234@localhost:5432/questionredis'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Desativa warnings desnecessários


# Inicializando extensões
socketio = SocketIO(app)
db = SQLAlchemy(app)
redis_client = redis.StrictRedis.from_url('redis://localhost:6379/0', decode_responses=True)

################### MODELO DE DAS BASES DE DADOS ######################

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nm_user = db.Column(db.String, nullable=False)
    des_user_passwd = db.Column(db.String, nullable=False)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'nm_user': self.nm_user,
            'des_user_passwd': self.des_user_passwd
        }

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    quiz_id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(UUID(db.String), db.ForeignKey('users.user_id'), nullable=False)
    title = db.Column(db.String, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False)
    def to_dict(self):
        return {
            'quiz_id': self.quiz_id,
            'user_id': self.user_id,
            'title': self.title,
            'is_active' : self.is_active
        }

class Question(db.Model):
    __tablename__ = 'questions'
    question_id = db.Column(db.Integer, primary_key=True, nullable=False)
    quiz_id = db.Column(UUID(db.String), db.ForeignKey('quizzes.quiz_id'), nullable=False)
    question_text = db.Column(db.String, nullable=False)
    def to_dict(self):
        return {
            'question_id': self.question_id,
            'quiz_id': self.quiz_id,
            'question_text': self.question_text
        }

class Answer(db.Model):
    __tablename__ = 'answers'
    answer_id = db.Column(db.Integer, primary_key=True, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.question_id'), nullable=False)
    answer_text = db.Column(db.String, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    nm_answer_option = db.Column(db.String(1))
    def to_dict(self):
        return {
            'answer_id': self.answer_id,
            'question_id': self.question_id,
            'answer_text': self.answer_text,
            'is_correct':self.is_correct,
            'nm_answer_option':self.nm_answer_option
        }
####################################################################################################

#TESTE DB RELACIONAL
@app.route('/test_postgresql', methods=['GET'])
def test_postgresql():
    try:
        # Tenta fazer uma consulta simples no banco de dados
        result = db.session.execute(text('SELECT 1'))
        return jsonify({"message": "Conexão bem-sucedida com o PostgreSQL!"}), 200
    except OperationalError as e:
        # Em caso de erro de conexão, retornamos um erro
        return jsonify({"error": "Falha na conexão com o PostgreSQL", "details": str(e)}), 500


# Rota para testar a conexão com o Redis
@app.route('/test_redis', methods=['GET'])
def test_redis_connection():# Função para testar a conexão com o Redis
    try:
        # Conecta ao Redis usando a URL configurada
        redis_client = redis.StrictRedis.from_url('redis://localhost:6379/0', decode_responses=True)
        
        # Tenta um comando simples para verificar a conexão
        redis_client.ping()  # Redis deve responder com "PONG"
        return jsonify({"message": "Conexão bem-sucedida com o Redis!"}), 200
    except redis.ConnectionError as e:
        # Se ocorrer erro de conexão, retorna False
        return jsonify({"error": "Falha na conexão com o Redis"}), 500

##############################################################################################################
################################## Serviços Redis ###########################################################
def load_quiz_to_redis(redis_client, quiz_id, quiz_data):
    """Load quiz data into Redis."""
    redis_key = f"quiz:{str(quiz_id)}"  # Convert UUID to string
    redis_client.set(redis_key, json.dumps(quiz_data))
    redis_client.set(f"{redis_key}:started",0)

def get_quiz_from_redis(redis_client, quiz_id):
    """Retrieve quiz data from Redis."""
    redis_key = f"quiz:{quiz_id}"
    quiz_data = redis_client.get(redis_key)
    if quiz_data:
        return json.loads(quiz_data)
    return None

def delete_quiz_from_redis(redis_client, quiz_id):
    """
    Delete all quiz-related data from Redis.

    Args:
        redis_client: Redis client instance.
        quiz_id: ID of the quiz to delete.

    Returns:
        bool: True if the keys were deleted, False if no keys were found.
    """
    # Definir um padrão de chave que abrange todas as chaves relacionadas ao quiz
    quiz_keys_pattern = f"quiz:{quiz_id}:*"
    
    # Use SCAN para encontrar todas as chaves que correspondem ao padrão
    keys_to_delete = redis_client.scan_iter(quiz_keys_pattern)
    
    # Deletar as chaves encontradas
    deleted_count = 0
    for key in keys_to_delete:
        redis_client.delete(key)
        deleted_count += 1
    
    return deleted_count > 0

#################################### CHAVES REDIS ##############################################################
QUIZ_PLAYERS_KEY = "quiz:{quiz_id}:players"
QUIZ_PLAYERS_KEY_READY = "quiz:{quiz_id}:players:ready_players"
QUIZ_ANSWERS_KEY = "quiz:{quiz_id}:answers"
QUIZ_CURRENT_QUESTION_KEY = "quiz:{quiz_id}:current_question"


###########################################################################################################
################################## Rota de Login e Cadastro de Usuário ####################################
def get_user_quizzes():
    """Helper function to fetch quizzes for the logged-in user."""
    try:
        quizzes = Quiz.query.filter_by(user_id=session['user_id']).all() or []
        return quizzes
    except Exception as e:
        raise Exception(f"Error fetching quizzes: {str(e)}")

@app.route('/')
@app.route('/home', methods=['GET'])
def home():
    if 'user_id' not in session:
        # Retorno JSON prioritário
        if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({"message": "Login is necessary"}), 401
        return redirect(url_for('login'))

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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            if not request.is_json:
                return jsonify({"message": "Request must be JSON"}), 415

            data = request.get_json()
            
            username = data.get('username')
            password = data.get('password')

            user = User.query.filter_by(nm_user=username).first()
            
            if user and check_password_hash(user.des_user_passwd, password):
                session['user_id'] = user.user_id
                
                if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
                    return jsonify({"message": "Login successfully","user_id":session['user_id']}), 200
                
                return redirect(url_for('home'))
            else:
                return jsonify({"message": "Invalid credentials"}), 401
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            if not request.is_json:
                return jsonify({"message": "Request must be JSON"}), 415

            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            new_user = User(nm_user=username, des_user_passwd=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            return jsonify({"message": "User registered successfully!"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Error: {str(e)}"}), 500

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "User logout successfully!"}), 200
    #return redirect(url_for('login'))

###########################################################################################################
############################################ Rota de Quiz #################################################
# Função auxiliar para validar sessão
def validate_session():
    if 'user_id' not in session:
        return False
    return True

# Função auxiliar para responder erros
def handle_error(message, code=500):
    return jsonify({"message": message}), code

# Função auxiliar para buscar um quiz pelo ID
def get_quiz_by_id(quiz_id, user_specific=True):
    filters = {"quiz_id": quiz_id}
    if user_specific:
        filters["user_id"] = session['user_id']
    return Quiz.query.filter_by(**filters).first()

# Função auxiliar para formatar dados de quiz
def format_quiz_data(quiz):
    questions = Question.query.filter_by(quiz_id=quiz.quiz_id).all()
    return {
        'quiz_id': str(quiz.quiz_id),
        'title': quiz.title,
        'is_active': quiz.is_active,
        'questions': [
            {
                'question_id': str(q.question_id),
                'question_text': q.question_text,
                'answers': [
                    {
                        'answer_id': str(a.answer_id),
                        'answer_text': a.answer_text,
                        'is_correct': a.is_correct,
                        'nm_answer_option': a.nm_answer_option
                    } for a in Answer.query.filter_by(question_id=q.question_id).all()
                ]
            } for q in questions
        ]
    }

@app.route('/quiz', methods=['GET', 'POST'])
def quiz_route():
    if not validate_session():
        return redirect(url_for('login'))

    if request.method == 'GET':
        if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({"message": "Rota para form do quiz"}), 200
        return render_template("create_quiz.html")

    if request.method == 'POST':
        try:
            data = request.get_json()
            quiz_title = data.get('quiz_title')
            questions = data.get('questions', [])

            new_quiz = Quiz(user_id=session['user_id'], title=quiz_title, is_active=False)
            db.session.add(new_quiz)
            db.session.commit()

            for question in questions:
                new_question = Question(quiz_id=new_quiz.quiz_id, question_text=question['question_text'])
                db.session.add(new_question)
                db.session.flush()  # Garante ID do question

                for answer in question['answers']:
                    new_answer = Answer(
                        question_id=new_question.question_id,
                        answer_text=answer['answer_text'],
                        is_correct=answer['is_correct'],
                        nm_answer_option=answer['nm_answer_option']
                    )
                    db.session.add(new_answer)

            db.session.commit()
           
            return jsonify({"message": "Quiz Created successfully!"}), 200

        except Exception as e:
            db.session.rollback()
            return handle_error(f"Error: {str(e)}")

@app.route('/quiz/<quiz_id>', methods=['GET', 'PUT', 'DELETE'])
def specific_quiz_route(quiz_id):
    if not validate_session():
        return redirect(url_for('login'))

    if request.method == 'GET':
        try:
            quiz = get_quiz_by_id(quiz_id, user_specific=False)
            if not quiz:
                return handle_error("Quiz not found", 404)

            quiz_data = format_quiz_data(quiz)

            # Verifica se a solicitação espera JSON
            if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
                return jsonify({"quiz": quiz_data}), 200

            return render_template('update_quiz.html', quiz_data=quiz_data)

        except Exception as e:
            return handle_error(f"Error: {str(e)}")

    if request.method == 'PUT':
        try:
            data = request.get_json()
            quiz = get_quiz_by_id(quiz_id)
            if not quiz:
                return handle_error("Quiz not found or not authorized to update", 404)

            quiz.title = data.get('quiz_title', quiz.title)
            updated_questions = data.get('questions', [])
            existing_questions = {q.question_id: q for q in Question.query.filter_by(quiz_id=quiz_id).all()}

            for question_data in updated_questions:
                question_id = question_data.get('question_id')
                question_text = question_data.get('question_text')
                answers = question_data.get('answers', [])

                if question_id in existing_questions:
                    question = existing_questions.pop(question_id)
                    question.question_text = question_text

                    existing_answers = {a.answer_id: a for a in Answer.query.filter_by(question_id=question.question_id).all()}
                    for answer_data in answers:
                        answer_id = answer_data.get('answer_id')

                        if answer_id in existing_answers:
                            answer = existing_answers.pop(answer_id)
                            answer.answer_text = answer_data.get('answer_text')
                            answer.is_correct = answer_data.get('is_correct')
                            answer.nm_answer_option = answer_data.get('nm_answer_option')
                        else:
                            new_answer = Answer(
                                question_id=question.question_id,
                                answer_text=answer_data.get('answer_text'),
                                is_correct=answer_data.get('is_correct'),
                                nm_answer_option=answer_data.get('nm_answer_option')
                            )
                            db.session.add(new_answer)

                    for leftover_answer in existing_answers.values():
                        db.session.delete(leftover_answer)
                else:
                    new_question = Question(quiz_id=quiz_id, question_text=question_text)
                    db.session.add(new_question)
                    db.session.flush()

                    for answer_data in answers:
                        new_answer = Answer(
                            question_id=new_question.question_id,
                            answer_text=answer_data.get('answer_text'),
                            is_correct=answer_data.get('is_correct'),
                            nm_answer_option=answer_data.get('nm_answer_option')
                        )
                        db.session.add(new_answer)

            for leftover_question in existing_questions.values():
                Answer.query.filter_by(question_id=leftover_question.question_id).delete()
                db.session.delete(leftover_question)

            db.session.commit()
            # Retornar dados do quiz atualizado
            quiz_data = {
                "quiz_id": quiz.quiz_id,
                "quiz_title": quiz.title,
                "questions": [
                    {
                        "question_id": question.question_id,
                        "question_text": question.question_text,
                        "answers": [
                            {
                                "answer_id": answer.answer_id,
                                "answer_text": answer.answer_text,
                                "is_correct": answer.is_correct,
                                "nm_answer_option": answer.nm_answer_option
                            }
                            for answer in Answer.query.filter_by(question_id=question.question_id).all()
                        ]
                    }
                    for question in Question.query.filter_by(quiz_id=quiz.quiz_id).all()
                ]
            }
            return jsonify({"message": "Quiz Updated successfully!", "quiz": quiz_data}), 200
            

        except Exception as e:
            db.session.rollback()
            return handle_error(f"Error: {str(e)}")

    if request.method == 'DELETE':
        try:
            quiz = Quiz.query.filter_by(quiz_id=quiz_id, user_id=session['user_id']).first()
            if not quiz:
                return jsonify({"message": "Quiz not found or not authorized to delete"}), 404

            # Delete related questions and answers
            questions = Question.query.filter_by(quiz_id=quiz_id).all()
            for question in questions:
                Answer.query.filter_by(question_id=question.question_id).delete()
                db.session.delete(question)

            db.session.delete(quiz)
            db.session.commit()
            return jsonify({"message": "Quiz deleted successfully!"}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Error: {str(e)}"}), 500



@app.route('/quiz/<quiz_id>/active', methods=['GET']) #ATIVAR O QUIZ
def active_quiz(quiz_id):
    if not validate_session():
        return redirect(url_for('login'))

    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        return handle_error("Quiz not found or not authorized to start", 404)

    if quiz.is_active:
        quiz.is_active = False
        db.session.commit()
        delete_quiz_from_redis(redis_client, quiz.quiz_id)
        return jsonify({'message': 'Quiz desativado com sucesso'}), 200

    
    quiz_data = format_quiz_data(quiz)

    # Preparar os dados do quiz
    quiz_info = {
        'quiz_id': str(quiz_data['quiz_id']),
        'title': quiz_data['title'],
        #'is_active': str(quiz_data['is_active'])  # Converte o booleano para string
    }

    # Adiciona a lista de question_ids ao quiz_info
    question_ids = [str(q['question_id']) for q in quiz_data['questions']]
    quiz_info['question_ids'] = json.dumps(question_ids)  # Converte a lista para uma string JSON

    # Armazenar informações gerais do quiz em um Hash no Redis
    redis_client.hset(f"quiz:{quiz.quiz_id}:info", mapping=quiz_info)
    
    # Armazenar cada questão do quiz como um Hash no Redis
    for q in quiz_data['questions']:
        
        question_data = {
            'question_id': str(q['question_id']),  # Use chave em vez de atributo
            'question_text': q['question_text'],   # Use chave em vez de atributo
        }

        # Armazenar alternativas da questão em uma lista
        alternatives = [
            {
                'answer_id': str(a.answer_id),
                'answer_text': a.answer_text,
                'is_correct': str(a.is_correct),
                'nm_answer_option': a.nm_answer_option
            } for a in Answer.query.filter_by(question_id=q['question_id']).all() 
        ]
        
        # Converte a lista de respostas em uma string JSON
        question_data['alternatives'] = json.dumps(alternatives)
        
        # Obter a alternativa correta diretamente
        correct_answer = Answer.query.filter_by(question_id=q['question_id'], is_correct=True).first()

        if correct_answer:
            # Armazenar a alternativa correta em um dicionário
            question_data['correct_answer'] = json.dumps({
                'answer_id': str(correct_answer.answer_id),
                'answer_text': correct_answer.answer_text,
                'is_correct': str(correct_answer.is_correct),
                'nm_answer_option': correct_answer.nm_answer_option
            })

        # Armazenar dados da questão em um Hash no Redis
        #HASH DE ARMAZENAMENTO INFO DA QUESTAO
        redis_client.hset(f"quiz:{quiz_data['quiz_id']}:question:{q['question_id']}:info", mapping=question_data)
        #CHAVE RANKING
        # Cria os dados para o ranking.
        ranking_data = {
            'question_order': 0,
            'question_text': q['question_text'],
            'opcao_mais_votada': "",
            'qtd_acertos': 0,
            'qtd_abstencoes': 0,
            'tempo_medio_resposta': 0
        }

        # Armazena os dados no Redis.
        redis_client.hset(f"quiz:{quiz_data['quiz_id']}:question:{q['question_id']}:ranking", mapping=ranking_data)
        
    quiz.is_active = True
    db.session.commit()
    return jsonify({'message': 'Quiz Ativado', 'quiz_id': str(quiz.quiz_id)}), 200

###########################################################################################################
############################################ Rotas Do Jogo ################################################

########################################### Lado do Professor #############################################




@app.route('/start_quiz/<quiz_id>', methods=['GET', 'POST'])  # INICIAR O QUIZ
def start_quiz(quiz_id):
    """Start the quiz dynamics and broadcast questions in real-time."""
    
    if request.method == 'GET':
        game_started = redis_client.get(f"quiz:{quiz_id}:started")
        return jsonify({"message": game_started.decode('utf-8') if game_started else "0"})
    
    if request.method == 'POST':
        # Obtém as informações gerais do quiz do Redis usando o ID do quiz.
        quiz_info = redis_client.hgetall(f"quiz:{quiz_id}:info")

        # Verifica se os dados do quiz existem no Redis. Caso contrário, retorna um erro 404.
        if not quiz_info:
            return jsonify({"error": "Quiz data not found"}), 404

        # Converte os dados do quiz para um formato legível (dict)
        quiz_info = {key: value for key, value in quiz_info.items()}
        print(quiz_info)

        # Obtém o título e o estado de atividade do quiz
        title = quiz_info.get('title')
        is_active = quiz_info.get('is_active')

        # Busca as perguntas do quiz no Redis
        questions = []

        # Recupera a lista de question_ids do Redis
        question_ids = json.loads(redis_client.hget(f"quiz:{quiz_id}:info", 'question_ids'))

        # Configura o Redis para rastrear o estado do quiz.
        # Define a questão atual como a primeira (índice 0).
        redis_client.set(QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id), 0)

        # Marca o quiz como iniciado no Redis.
        redis_client.set(f"quiz:{quiz_id}:started", 1)
        # Obtém a quantidade de registros
        num_players = redis_client.scard(f"quiz:{quiz_id}:players")
        # Emite um sinal via WebSocket para notificar todos os clientes conectados que o quiz foi iniciado.
        socketio.emit('quiz_started', {'quiz_id': quiz_id}, room=quiz_id)
        #print(f"Async mode: {socketio.async_mode}")

        # Define uma função para enviar perguntas aos clientes conectados de forma sequencial.
        def send_questions():
            question_index = 0  # Começa com a primeira pergunta.
            while question_index < len(question_ids):  # Continua até que todas as perguntas sejam enviadas.
                try:
                    # Define o valor do campo
                    redis_client.hset(f"quiz:{quiz_id}:question:{question_ids[question_index]}:ranking", "qtd_abstencoes", num_players)
                    redis_client.hset(f"quiz:{quiz_id}:question:{question_ids[question_index]}:ranking", "question_order", question_index + 1)
                    # Obtém a pergunta atual com base no índice.
                    question_data = redis_client.hgetall(f"quiz:{quiz_id}:question:{question_ids[question_index]}:info")
                    question = {key: value for key, value in question_data.items()}
                    # Emite a pergunta para todos os clientes conectados ao WebSocket na sala correspondente ao quiz.
                    socketio.emit('new_question', {'question': question}, room=quiz_id)
                    #print(f"Sent question {question_index + 1}: {question}")
                    print(f"Sent question {question_index + 1}")

                    # Atualiza no Redis o índice da próxima pergunta.
                    redis_client.set(QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id), question_index + 1)
                    
                    # Aguarda 20 segundos antes de enviar a próxima pergunta, dando tempo para os participantes responderem.
                    socketio.sleep(6)
                    
                    process_question_ranking(f"quiz:{quiz_id}:question:{question_ids[question_index]}")
                
                    
                    # Incrementa o índice para enviar a próxima pergunta no próximo loop.
                    question_index += 1
                    
                except Exception as e:
                    # Captura e registra erros que ocorram no loop de envio de perguntas.
                    print(f"Error in send_questions loop: {e}")
                    break
            
            # Após o envio de todas as perguntas, emite um sinal indicando que o quiz foi finalizado.
            try:
                socketio.emit('quiz_finished', {'quiz_id': quiz_id, 'message': 'Quiz finished!'}, room=quiz_id)
                print("Quiz finished!")

            except Exception as e:
                # Captura e registra erros ao tentar emitir o evento de quiz finalizado.
                print(f"Error sending quiz_finished event: {e}")

        # Inicia a função `send_questions` como uma tarefa em segundo plano usando o WebSocket.
        socketio.start_background_task(send_questions)

        
        # Retorna uma resposta HTTP para confirmar que o quiz foi iniciado e que as perguntas estão sendo enviadas.
        return jsonify({"message": "Quiz started and questions are being sent"}), 200


def process_question_ranking(current_question_key):
    try:
        time.sleep(4)  # Aguarda 25 segundos antes de processar os dados.
        # Obtém a opção mais votada.
        top_option = redis_client.zrevrange(f"{current_question_key}:votes", 0, 0, withscores=True)
        redis_client.hset(f"{current_question_key}:ranking", "opcao_mais_votada", top_option[0][0])
        #print(f"top_option : {top_option}")
        
        # Calcula o tempo médio de resposta.
        response_times = redis_client.zrange(f"{current_question_key}:response_time", 0, -1, withscores=True)
        total_time = sum(time for _, time in response_times)
        num_users = len(response_times)
        average_time = round(total_time / num_users, 2) if num_users > 0 else 0
        redis_client.hset(f"{current_question_key}:ranking", "tempo_medio_resposta", average_time)
        print(f"average_time : {average_time}")

    except Exception as e:
        print(f"Error in process_question_ranking: {e}")



# SocketIO Event Listener (ouvindo o evento de conexão)
@socketio.on('connect')
def handle_connect():
    """Quando um cliente se conecta, entra na room do quiz"""
    quiz_id = request.args.get('quiz_id')  # Pegando o quiz_id da URL de conexão
    username = request.args.get('username')  # Pegando o quiz_id da URL de conexão
    if quiz_id:
        join_room(quiz_id)  # Adicionando o cliente à room do quiz
        print("#################################################")
        print(f'Cliente {username} conectado ao quiz: {quiz_id}')
        print("#################################################")

@socketio.on('disconnect')
def handle_disconnect():
    """Quando o cliente desconectar, ele sai da room"""
    quiz_id = request.args.get('quiz_id')
    username = request.args.get('username')  # Pegando o quiz_id da URL de conexão
    if quiz_id:
        leave_room(quiz_id)  # Removendo o cliente da room do quiz
        print("#################################################")
        print(f'Cliente {username} desconectado do quiz: {quiz_id}')
        print("#################################################")

@app.route('/<quiz_id>/results', methods=['GET'])  # INICIAR O QUIZ
def ranking(quiz_id):
    # Marca o quiz como iniciado no Redis.
    redis_client.set(f"quiz:{quiz_id}:started", 0)
    quiz_global_key = f"quiz:{quiz_id}:global:correct_responses"
    
    all_data = redis_client.hgetall(quiz_global_key)
    # Processar os dados em uma lista de dicionários
    users_data = {}
    for key, value in all_data.items():
        user_id, attribute = key.split(":")
        if user_id not in users_data:
            users_data[user_id] = {"user_id": user_id, "response_time": 0, "correct_responses": 0}
        if attribute == "response_time":
            users_data[user_id]["response_time"] = float(value)
        elif attribute == "correct_responses":
            users_data[user_id]["correct_responses"] = int(value)
    users_list = users_data.values()
    # Capturar o alunos que obtiveram a maior pontuação e em menor tempo
    ranked_students = sorted(
        users_list,
        key=lambda x: (-x["correct_responses"], x["response_time"])
    )
    # Adiciona o ranking à lista
    ranked_students_with_positions = [
        {**student, "rank": index + 1} for index, student in enumerate(ranked_students)
    ]
    # Encontra o maior número de respostas corretas
    max_correct_responses = max(item['correct_responses'] for item in users_list)
    # Filtra os alunos com o maior número de respostas corretas
    top_students = [item for item in users_list if item['correct_responses'] == max_correct_responses]
    
    quiz_global_key = f"quiz:{quiz_id}:global:responses_time"
    # Obter o ranking dos alunos com os menores tempos de resposta (menor é melhor)
    top_fastest = redis_client.zrange(quiz_global_key, 0, -1, withscores=True)

    # Inicializando a lista para armazenar o ranking
    ranked_fastest_users = []

    # Iterar sobre o resultado e adicionar o número de ordenação
    for i, (member, score) in enumerate(top_fastest, 1):  # A enumeração começa em 1 para refletir o ranking correto
        print(member)
        print(score)
        ranked_fastest_users.append({"rank": i, "user_id": member, "response_time": round(score,2)})
            
    
    # Recupera a lista de question_ids do Redis
    question_ids = json.loads(redis_client.hget(f"quiz:{quiz_id}:info", 'question_ids')) 
    question_rank = []
    for q in question_ids:
        data = redis_client.hgetall(f"quiz:{quiz_id}:question:{q}:ranking")
        json_data = json.dumps(data, indent=4)
        question_rank.append(json.loads(json_data))
    
    return jsonify({"students_ranking": ranked_students_with_positions, 
                    "top_students_correct_answer": top_students,
                    "fastest_students":ranked_fastest_users,
                    "question_ranking": question_rank
                })
                    
        
        


########################################### Lado do Aluno #############################################
@app.route('/quiz/<quiz_id>/join', methods=['GET', 'POST']) #jogadores entram e se cadastram
def join_quiz(quiz_id):
    """Join the quiz and get the player's data."""

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
        
        
        # Returning a JSON response that contains the URL for game.html
        return jsonify({"message": "Successfully joined the quiz"}),200
    
@app.route('/quiz/<quiz_id>/<username>/game')
def game(quiz_id,username):
    return render_template('game.html',quiz_id=quiz_id,username=username)

@app.route('/quiz/<quiz_id>/submit_answer', methods=['POST'])
def submit_answer(quiz_id):
    """Submit an answer for the current question."""
    try:
        username = request.json.get('username')
        option = request.json.get('option')  # Aqui o option é um objeto
        question_id = request.json.get('question_id')
        time_taken = request.json.get('time_taken')
        
        if not username or not option or not question_id:
            return jsonify({"error": "Username, option, and question_id are required"}), 400
        
        # Garantir que o `option` seja um dicionário
        if isinstance(option, str):
            try:
                option = json.loads(option)  # Converter string para JSON
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid option format"}), 400

        # Validar os campos do objeto `option`
        nm_answer_option = option.get('nm_answer_option')
        is_correct = option.get('is_correct')

        if not nm_answer_option or is_correct is None:
            return jsonify({"error": "Option must include nm_answer_option and is_correct"}), 400

        # Definir as chaves no Redis
        current_question_key = f"quiz:{quiz_id}:question:{question_id}"
        votes_key = f"{current_question_key}:votes"
        voters_key = f"{current_question_key}:voters"
        responses_key = f"quiz:{quiz_id}:responses"
        response_time_key = f"{current_question_key}:response_time"
        correct_responses_key = f"{current_question_key}:correct_responses"
        global_correct_responses_key = f"quiz:{quiz_id}:global:correct_responses"
        global_responses_time_key = f"quiz:{quiz_id}:global:responses_time"

        

        # Verifica se o usuário já votou
        if redis_client.sismember(voters_key, username):
            return jsonify({"error": "User has already voted"}), 400

        # Registra o voto no Hash de respostas
        redis_client.hset(responses_key, f"{question_id}:{username}", json.dumps({
            "nm_answer_option": nm_answer_option,
            "is_correct": is_correct,
            "timestamp": time.time()
        }))

        # Verifica se a resposta do usuário está correta
        #if is_correct == "True":  # Verifica se a resposta enviada é a correta
        #   redis_client.sadd(correct_responses_key, username)  # Adiciona o usuário à lista de

        # Incrementa o número de votos para a opção
        redis_client.zincrby(votes_key,1.0,nm_answer_option)

        # Registra o tempo de resposta no Sorted Set
        # Ensure time_taken is a valid number before using it
        if time_taken is not None and isinstance(time_taken, (int, float)):
            redis_client.zadd(response_time_key, {username: time_taken})
            # Incrementa o número de respostas no Sorted Set
            redis_client.zincrby(global_responses_time_key,time_taken,username)
            # Verifica se a resposta do usuário está correta
            if is_correct == "True":  # Verifica se a resposta enviada é a correta
                redis_client.zadd(correct_responses_key, {username: time_taken})  # Adiciona o usuário à lista de
                # Incrementar o tempo de resposta
                redis_client.hincrbyfloat(global_correct_responses_key, f"{username}:response_time", time_taken)
                # Incrementar o número de respostas corretas
                redis_client.hincrby(global_correct_responses_key, f"{username}:correct_responses", 1)
                #Incrementar o número de respostas corretas no ranking
                redis_client.hincrby(f"{current_question_key}:ranking", "qtd_acertos", 1)
                
        else:
            print(f"Invalid time_taken value: {time_taken}. Expected a number.")

        # Marca o usuário como votante
        redis_client.sadd(voters_key, username)
        #Decrementa o número de abstenções no ranking
        redis_client.hincrby(f"{current_question_key}:ranking", "qtd_abstencoes", -1)

        return jsonify({"message": "Answer submitted successfully"}), 200

    except Exception as e:
        # Log do erro para depuração
        print(f"Error in submit_answer: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500
    




if __name__ == '__main__':
    socketio.run(app, debug=True)