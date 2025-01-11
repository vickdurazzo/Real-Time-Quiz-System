# Redis-specific functions
from flask import jsonify, session
import redis
import json
import time
from app import socketio

from app.models import Answer

def get_redis_connection():
    return redis.StrictRedis(host='localhost', port=6379, db=0)

def load_quiz_to_redis(quiz_id, quiz_data):
    """Load quiz data into Redis."""
    redis_client = get_redis_connection()
    redis_key = f"quiz:{str(quiz_id)}"  # Convert UUID to string
    redis_client.set(redis_key, json.dumps(quiz_data))
    redis_client.set(f"{redis_key}:started",0)

def get_quiz_from_redis( quiz_id):
    """Retrieve quiz data from Redis."""
    redis_client = get_redis_connection()
    redis_key = f"quiz:{quiz_id}"
    quiz_data = redis_client.get(redis_key)
    if quiz_data:
        return json.loads(quiz_data)
    return None

def delete_quiz_from_redis( quiz_id):
    """
    Delete all quiz-related data from Redis.

    Args:
        redis_client: Redis client instance.
        quiz_id: ID of the quiz to delete.

    Returns:
        bool: True if the keys were deleted, False if no keys were found.
    """
    redis_client = get_redis_connection()
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

def redis_active_quiz(quiz_id,quiz_data):
    redis_client = get_redis_connection()
    
    # Adiciona a lista de question_ids ao quiz_info
    question_ids = [str(q['question_id']) for q in quiz_data['questions']]
    # Preparar os dados do quiz
    quiz_info = {
        'quiz_id': str(quiz_data['quiz_id']),
        'title': quiz_data['title'],
        'question_ids' : json.dumps(question_ids)
    }
    
    # Armazenar informações gerais do quiz em um Hash no Redis
    redis_client.hset(f"quiz:{quiz_id}:info", mapping=quiz_info)
    
    for q in quiz_data['questions']:
        
        question_data = {
            'question_id': str(q['question_id']),  # Use chave em vez de atributo
            'question_text': q['question_text'],   # Use chave em vez de atributo
        }

        # Armazenar alternativas da questão em uma lista
        alternatives = [
            {
                'answer_id': str(a['answer_id']),  # Use dictionary key
                'answer_text': a['answer_text'],   # Use dictionary key
                'is_correct': str(a['is_correct']),  # Use dictionary key
                'nm_answer_option': a['nm_answer_option']  # Use dictionary key
            } for a in q['answers']  # Iterate over the list of answer dictionaries
        ]
        
        # Convert the list of answers into a JSON string
        question_data['alternatives'] = json.dumps(alternatives)

        # Retrieve the correct answer directly from the alternatives
        correct_answer = next((a for a in q['answers'] if a['is_correct']), None)

        if correct_answer:
            # Store the correct answer in a dictionary
            question_data['correct_answer'] = json.dumps({
                'answer_id': str(correct_answer['answer_id']),
                'answer_text': correct_answer['answer_text'],
                'is_correct': str(correct_answer['is_correct']),
                'nm_answer_option': correct_answer['nm_answer_option']
            })

        # Store question data in a Redis Hash
        redis_client.hset(f"quiz:{quiz_id}:question:{q['question_id']}:info", mapping=question_data)

        # Create ranking data for the question
        ranking_data = {
            'question_order': 0,
            'question_text': q['question_text'],
            'opcao_mais_votada': "",
            'qtd_acertos': 0,
            'qtd_abstencoes': 0,
            'tempo_medio_resposta': 0
        }

        # Store ranking data in Redis
        redis_client.hset(f"quiz:{quiz_id}:question:{q['question_id']}:ranking", mapping=ranking_data)

def initialize_quiz(quiz_id):
    """Check if the quiz is started."""
    redis_client = get_redis_connection()
    game_started = redis_client.get(f"quiz:{quiz_id}:started")
    return game_started.decode('utf-8') if game_started else "0"

def broadcast_question(quiz_id):
    """Broadcast the current question to all connected clients."""
    redis_client = get_redis_connection()
    question_ids = json.loads(redis_client.hget(f"quiz:{quiz_id}:info", "question_ids"))
    print(question_ids)
    # Obtém a quantidade de registros
    num_players = redis_client.scard(f"quiz:{quiz_id}:players")
    print(num_players)
    
    # Emite um sinal via WebSocket para notificar todos os clientes conectados que o quiz foi iniciado.
    socketio.emit('quiz_started', {'quiz_id': quiz_id}, room=quiz_id)
    print(quiz_id)
    def send_questions():
        
        # Envia a pergunta atual para todos os clientes conectados
        for index, question_id in enumerate(question_ids):
            
            # Define o valor do campo
            redis_client.hset(f"quiz:{quiz_id}:question:{question_id}:ranking", "qtd_abstencoes", num_players)
            redis_client.hset(f"quiz:{quiz_id}:question:{question_id}:ranking", "question_order", index + 1)
            # Obtém a pergunta atual com base no índice.
            question_data = redis_client.hgetall(f"quiz:{quiz_id}:question:{question_id}:info")
            # Assuming question_data is a dictionary with byte strings
            question_data = {key.decode(): value.decode() for key, value in question_data.items()}

            # Now, you can safely convert to a JSON object
            question_data_str = json.dumps(question_data)
            question = json.loads(question_data_str)
            print(question)
            # Emit the question to all connected clients via WebSocket
            socketio.emit('new_question', {'question': question}, room=quiz_id)
            # Aguarda 20 segundos antes de enviar a próxima pergunta, dando tempo para os participantes responderem.
            socketio.sleep(6)
            ranking_middle(f"quiz:{quiz_id}:question:{question_id}")
            
        socketio.emit('quiz_finished', {'quiz_id': quiz_id, 'message': 'Quiz finished!'}, room=quiz_id)
        # Inicia a função `send_questions` como uma tarefa em segundo plano usando o WebSocket.
    socketio.start_background_task(send_questions)  
    
    
def ranking_middle(current_question_key):
    redis_client = get_redis_connection()
    try:
        time.sleep(4)  # Aguarda 25 segundos antes de processar os dados.
        # Obtém a opção mais votada.
        top_option = redis_client.zrevrange(f"{current_question_key}:votes", 0, 0, withscores=True)
        redis_client.hset(f"{current_question_key}:ranking", "opcao_mais_votada", top_option[0][0])
        
        
        # Calcula o tempo médio de resposta.
        response_times = redis_client.zrange(f"{current_question_key}:response_time", 0, -1, withscores=True)
        total_time = sum(time for _, time in response_times)
        num_users = len(response_times)
        average_time = round(total_time / num_users, 2) if num_users > 0 else 0
        redis_client.hset(f"{current_question_key}:ranking", "tempo_medio_resposta", average_time)
        print(f"average_time : {average_time}")

    except Exception as e:
        print(f"Error in process_question_ranking: {e}")


def handle_player_join(quiz_id,data):
    """Handle player joining the quiz."""
    redis_client = get_redis_connection()
    username = data.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400

    players_key = f"quiz:{quiz_id}:players"
    if redis_client.sismember(players_key, username):
        return jsonify({"error": "Username is already taken"}), 400

    redis_client.sadd(players_key, username)
    session['username'] = username
    return jsonify({"message": "Successfully joined the quiz"}), 200

def submit_player_answer(quiz_id,data):
    """Submit an answer for the current question."""
    redis_client = get_quiz_from_redis()
    try:
        username = data.get('username')
        option = data.get('option')
        question_id = data.get('question_id')
        time_taken = data.get('time_taken')

        # Validate required fields
        if not all([username, option, question_id]):
            return jsonify({"error": "Username, option, and question_id are required"}), 400

        # Ensure option is a dictionary
        if isinstance(option, str):
            try:
                option = json.loads(option)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid option format"}), 400

        # Extract fields from option and validate
        nm_answer_option = option.get('nm_answer_option')
        is_correct = option.get('is_correct')

        if not nm_answer_option or is_correct is None:
            return jsonify({"error": "Option must include nm_answer_option and is_correct"}), 400

        # Define Redis keys
        current_question_key = f"quiz:{quiz_id}:question:{question_id}"
        redis_keys = {
            "votes": f"{current_question_key}:votes",
            "voters": f"{current_question_key}:voters",
            "responses": f"quiz:{quiz_id}:responses",
            "response_time": f"{current_question_key}:response_time",
            "correct_responses": f"{current_question_key}:correct_responses",
            "global_correct_responses": f"quiz:{quiz_id}:global:correct_responses",
            "global_responses_time": f"quiz:{quiz_id}:global:responses_time",
            "ranking": f"{current_question_key}:ranking"
        }

        # Check if the user already voted
        if redis_client.sismember(redis_keys["voters"], username):
            return jsonify({"error": "User has already voted"}), 400

        # Register the user's response
        redis_client.hset(redis_keys["responses"], f"{question_id}:{username}", json.dumps({
            "nm_answer_option": nm_answer_option,
            "is_correct": is_correct,
            "timestamp": time.time()
        }))

        # Increment votes for the selected option
        redis_client.zincrby(redis_keys["votes"], 1.0, nm_answer_option)

        # Process response time and correctness
        if time_taken and isinstance(time_taken, (int, float)):
            redis_client.zadd(redis_keys["response_time"], {username: time_taken})
            redis_client.zincrby(redis_keys["global_responses_time"], time_taken, username)

            if is_correct:  # True means the answer is correct
                redis_client.zadd(redis_keys["correct_responses"], {username: time_taken})
                redis_client.hincrbyfloat(redis_keys["global_correct_responses"], f"{username}:response_time", time_taken)
                redis_client.hincrby(redis_keys["global_correct_responses"], f"{username}:correct_responses", 1)
                redis_client.hincrby(redis_keys["ranking"], "qtd_acertos", 1)
        else:
            print(f"Invalid time_taken value: {time_taken}. Expected a number.")

        # Mark the user as a voter and update abstention count
        redis_client.sadd(redis_keys["voters"], username)
        redis_client.hincrby(redis_keys["ranking"], "qtd_abstencoes", -1)

        return jsonify({"message": "Answer submitted successfully"}), 200

    except Exception as e:
        # Log the error for debugging
        print(f"Error in submit_answer: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

def ranking_final(quiz_id):
    
    """Retrieve and process rankings and results for a quiz."""
    redis_client = get_redis_connection()
    try:
        # Finaliza o quiz no Redis
        redis_client.set(f"quiz:{quiz_id}:started", 0)

        # Obter dados globais de respostas corretas
        correct_responses_key = f"quiz:{quiz_id}:global:correct_responses"
        all_data = redis_client.hgetall(correct_responses_key)

        # Processar os dados dos usuários
        users_data = {}
        for key, value in all_data.items():
            user_id, attribute = key.split(":")
            users_data.setdefault(user_id, {"user_id": user_id, "response_time": 0, "correct_responses": 0})
            if attribute == "response_time":
                users_data[user_id]["response_time"] = float(value)
            elif attribute == "correct_responses":
                users_data[user_id]["correct_responses"] = int(value)

        # Criar lista de usuários e rankear por pontuação e tempo de resposta
        users_list = list(users_data.values())
        ranked_students = sorted(users_list, key=lambda x: (-x["correct_responses"], x["response_time"]))

        # Adicionar posições ao ranking
        ranked_students_with_positions = [
            {**student, "rank": index + 1} for index, student in enumerate(ranked_students)
        ]

        # Filtrar alunos com maior número de respostas corretas
        max_correct_responses = max(item["correct_responses"] for item in users_list)
        top_students = [item for item in users_list if item["correct_responses"] == max_correct_responses]

        # Obter ranking dos alunos mais rápidos
        responses_time_key = f"quiz:{quiz_id}:global:responses_time"
        top_fastest = redis_client.zrange(responses_time_key, 0, -1, withscores=True)
        ranked_fastest_users = [
            {"rank": i + 1, "user_id": member, "response_time": round(score, 2)}
            for i, (member, score) in enumerate(top_fastest)
        ]

        # Obter ranking das questões
        question_ids = json.loads(redis_client.hget(f"quiz:{quiz_id}:info", "question_ids"))
        question_rank = [
            redis_client.hgetall(f"quiz:{quiz_id}:question:{q}:ranking") for q in question_ids
        ]

        # Retornar os resultados em JSON
        return jsonify({
            "students_ranking": ranked_students_with_positions,
            "top_students_correct_answer": top_students,
            "fastest_students": ranked_fastest_users,
            "question_ranking": question_rank,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500