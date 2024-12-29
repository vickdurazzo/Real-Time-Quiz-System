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
    quiz_keys_pattern = f"quiz:{quiz_id}*"
    
    # Use SCAN para encontrar todas as chaves que correspondem ao padrão
    keys_to_delete = redis_client.scan_iter(quiz_keys_pattern)
    
    # Deletar as chaves encontradas
    deleted_count = 0
    for key in keys_to_delete:
        redis_client.delete(key)
        deleted_count += 1
    
    return deleted_count > 0




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
        return redirect(url_for('login'))
    try:
        quizzes = get_user_quizzes()
        return render_template('home.html', quizzes=quizzes)
    except Exception as e:
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
                #return jsonify({"message": "Login successfully"}), 200
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
            return jsonify({"message": "Quiz created successfully!"}), 200

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
            return jsonify({"message": "Quiz updated successfully!"}), 200

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

@app.route('/quiz/<quiz_id>/active', methods=['GET'])
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

    quiz.is_active = True
    db.session.commit()
    quiz_data = format_quiz_data(quiz)
    load_quiz_to_redis(redis_client, quiz.quiz_id, quiz_data)
    return jsonify({'message': 'Game started', 'quiz_id': str(quiz.quiz_id)}), 200

###########################################################################################################
############################################ Rotas Do Jogo ################################################

########################################### Lado do Professor #############################################

QUIZ_PLAYERS_KEY = "quiz:{quiz_id}:players"
QUIZ_PLAYERS_KEY_READY = "quiz:{quiz_id}:players:ready_players"
QUIZ_ANSWERS_KEY = "quiz:{quiz_id}:answers"
QUIZ_CURRENT_QUESTION_KEY = "quiz:{quiz_id}:current_question"

@app.route('/ranking/<quiz_id>', methods=['GET'])
def get_rankings(quiz_id):
    QUIZ_DATA_KEY = f"quiz:{quiz_id}"
    QUIZ_ID = quiz_id
    # Dados do quiz
    quiz_data = json.loads(redis_client.get(QUIZ_DATA_KEY))
    questions = {q["question_id"]: q for q in quiz_data["questions"]}

    # Rankings
    print("==== Rankings do Quiz ====\n")

    # Alternativas mais votadas
    print("Alternativas Mais Votadas:")
    for question_id, question in questions.items():
        votes = []
        for answer in question["answers"]:
            answer_id = answer["answer_id"]
            vote_count = redis_client.zscore(f"quiz:{QUIZ_ID}:votes", answer_id) or 0
            votes.append((answer["nm_answer_option"], vote_count))
        votes.sort(key=lambda x: -x[1])  # Ordenar por número de votos
        print(f"Questão {question_id}: {votes[0][0]} ({votes[0][1]} votos)")

    # Questões mais acertadas
    print("\nQuestões Mais Acertadas:")
    for question_id in questions.keys():
        correct_count = redis_client.get(f"quiz:{QUIZ_ID}:correct:{question_id}") or 0
        print(f"Questão {question_id}: {correct_count} acertos")

    # Questões com mais abstenções
    print("\nQuestões com Mais Abstenções:")
    for question_id, question in questions.items():
        total_responses = redis_client.hlen(f"quiz:{QUIZ_ID}:answers:{question_id}") or 0
        total_options = len(question["answers"])
        abstentions = total_options - total_responses
        print(f"Questão {question_id}: {abstentions} abstenções")

    # Tempo médio de resposta por questão
    print("\nTempo Médio de Resposta por Questão:")
    for question_id in questions.keys():
        times = redis_client.zrange(f"quiz:{QUIZ_ID}:response_time:{question_id}", 0, -1, withscores=True)
        if times:
            avg_time = sum(time for _, time in times) / len(times)
            print(f"Questão {question_id}: {avg_time:.2f} segundos")
        else:
            print(f"Questão {question_id}: Sem respostas")

    # Alunos com maior acerto e mais rápidos
    print("\nRanking Final (Acertos e Velocidade):")
    users = redis_client.zrange(f"quiz:{QUIZ_ID}:user_scores", 0, -1, withscores=True)
    for user, score in sorted(users, key=lambda x: (-x[1], x[0])):
        print(f"Usuário {user}: {score} pontos")

    # Alunos com maior acerto
    print("\nAlunos com Maior Acerto:")
    accuracies = redis_client.zrange(f"quiz:{QUIZ_ID}:user_correct", 0, -1, withscores=True)
    for user, corrects in sorted(accuracies, key=lambda x: -x[1]):
        print(f"Usuário {user}: {corrects} acertos")

    # Alunos mais rápidos
    print("\nAlunos Mais Rápidos:")
    speeds = redis_client.zrange(f"quiz:{QUIZ_ID}:user_speed", 0, -1, withscores=True)
    for user, time in sorted(speeds, key=lambda x: x[1]):
        print(f"Usuário {user}: {time:.2f} segundos")

@app.route('/start_quiz/<quiz_id>', methods=['GET', 'POST'])
def start_quiz(quiz_id):
    """Start the quiz dynamics and broadcast questions in real-time."""
    
    if request.method == 'GET':
        game_started = redis_client.get(f"quiz:{quiz_id}:started")
        return jsonify({"message": game_started.decode('utf-8') if game_started else "0"})
    
    if request.method == 'POST':
        quiz_data = redis_client.get(f"quiz:{quiz_id}")
        if not quiz_data:
            return jsonify({"error": "Quiz data not found"}), 404
        
        quiz_data = json.loads(quiz_data)
        questions = quiz_data.get('questions', [])
        if not questions:
            return jsonify({"error": "No questions available in the quiz"}), 400
        
        # Configuração do Redis para iniciar o quiz
        redis_client.set(QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id), 0)
        redis_client.set(f"quiz:{quiz_id}:started", 1)

        # Emitindo sinal via WebSocket para notificar todos os clientes conectados
        socketio.emit('quiz_started', {'quiz_id': quiz_id}, room=quiz_id)
        print(f"Async mode: {socketio.async_mode}")
        
        # Função síncrona para envio de perguntas
        def send_questions():
            question_index = 0
            while question_index < len(questions):
                try:
                    question = questions[question_index]
                    socketio.emit('new_question', {'question': question}, room=quiz_id)
                    print(f"Sent question {question_index + 1}: {question}")

                    redis_client.set(QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id), question_index + 1)
                    socketio.sleep(6)  # Substitui time.sleep(6)
                    question_index += 1
                except Exception as e:
                    print(f"Error in send_questions loop: {e}")
                    break
            # Após o loop, emitir a mensagem de quiz finalizado
            try:
                socketio.emit('quiz_finished', {'quiz_id': quiz_id, 'message': 'Quiz finished!'}, room=quiz_id)
                print("Quiz finished!")
            except Exception as e:
                print(f"Error sending quiz_finished event: {e}")


        # Usar socketio.start_background_task para iniciar a tarefa síncrona
        socketio.start_background_task(send_questions)
        
        # Retornar uma resposta indicando que o quiz foi iniciado
        return jsonify({"message": "Quiz started and questions are being sent"}), 200




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
    username = request.json.get('username')
    answer_id = request.json.get('answer_id')
    if not username or not answer_id:
        return jsonify({"error": "Username and answer_id are required"}), 400

    
    current_question_idx = int(redis_client.get(QUIZ_CURRENT_QUESTION_KEY.format(quiz_id=quiz_id)) or 0)
    answers_key = QUIZ_ANSWERS_KEY.format(quiz_id=quiz_id)
    redis_client.hset(answers_key, f"{current_question_idx}:{username}", json.dumps({
        "answer_id": answer_id,
        "timestamp": time.time()
    }))
    return jsonify({"message": "Answer submitted"}), 200
    




if __name__ == '__main__':
    socketio.run(app, debug=True)