# Redis-specific functions
from flask import jsonify, session,current_app, url_for
import redis
import json
import time
from app import socketio
from datetime import timedelta
import requests


from app.models import Answer

# Tempo de expiração das chaves no Redis (30 dias em segundos)
EXPIRATION_TIME = 30 * 24 * 60 * 60  # 2592000 segundos
TEMPO_TRANSMISSAO_PERGUNTA = 20


def get_redis_connection():
    """
    Estabelece uma conexão com o servidor Redis.
    
    Retorna:
        redis.StrictRedis: Instância do cliente Redis para interações com o servidor Redis.
    """
    return redis.StrictRedis(host="quiz_redis", port=6379, db=0)

def load_quiz_to_redis(quiz_id, quiz_data):
    """
    Carrega os dados de um quiz no Redis.
    
    Args:
        quiz_id (int): O ID do quiz.
        quiz_data (dict): Os dados do quiz a serem armazenados no Redis.
        
    Armazena os dados do quiz na chave `quiz:{quiz_id}:{session_id}` no Redis, com um tempo de expiração de 30 dias.
    Também armazena o estado do quiz (iniciado ou não) em uma chave separada.
    """
    redis_client = get_redis_connection()
    redis_key = f"quiz:{str(quiz_id)}:{session['quiz_session_id']}"  # Converte o ID do quiz para string
    redis_client.setex(redis_key, EXPIRATION_TIME, json.dumps(quiz_data))
    redis_client.set(f"{redis_key}:started", 0)

def get_quiz_from_redis(quiz_id):
    """
    Recupera os dados de um quiz do Redis.
    
    Args:
        quiz_id (int): O ID do quiz a ser recuperado.
        
    Retorna:
        dict: Os dados do quiz armazenados no Redis, ou `None` caso não seja encontrado.
    """
    redis_client = get_redis_connection()
    redis_key = f"quiz:{quiz_id}:{session['quiz_session_id']}"
    quiz_data = redis_client.get(redis_key)
    if quiz_data:
        return json.loads(quiz_data)
    return None

def check_quiz_session(quiz_id):
    """
    Verifica se existe uma sessão ativa para o quiz.
    
    Args:
        quiz_id (int): O ID do quiz a ser verificado.
        
    Retorna:
        bool: Retorna `True` se uma sessão de quiz estiver ativa, `False` caso contrário.
    """
    redis_client = get_redis_connection()
    quiz_session_id = redis_client.get(f"quiz:{quiz_id}:current_quiz_session_id")
    
    # Retorna True se o valor existir, caso contrário, False
    return quiz_session_id is not None

def check_user_quiz_session(user_id):
    """
    Verifica se o usuário está associado a um quiz ativo.
    
    Args:
        user_id (int): O ID do usuário a ser verificado.
        
    Retorna:
        bool: Retorna `True` se o usuário estiver associado a um quiz ativo, `False` caso contrário.
    """
    redis_client = get_redis_connection()
    user_quiz_id = redis_client.get(f"quiz:{user_id}")
    
    # Retorna True se o valor existir, caso contrário, False
    return user_quiz_id is not None


def delete_quiz_from_redis(quiz_id):
    """
    Deleta todos os dados relacionados a um quiz do Redis.
    
    Args:
        quiz_id (int): O ID do quiz a ser deletado.
        
    Retorna:
        bool: Retorna `True` se as chaves foram deletadas com sucesso, `False` caso não tenham sido encontradas chaves.
    """
    redis_client = get_redis_connection()
    quiz_keys_pattern = f"quiz:{quiz_id}:*"  # Padrão para encontrar todas as chaves relacionadas ao quiz
    
    
    # Usando o comando SCAN para buscar todas as chaves que atendem ao padrão
    keys_to_delete = redis_client.scan_iter(quiz_keys_pattern)
    
     # Deleta as chaves encontradas
    deleted_count = 0
    for key in keys_to_delete:
        redis_client.delete(key)
        deleted_count += 1
    
    return deleted_count > 0


def redis_stop_quiz(user_id):
    """
    Interrompe um quiz para um usuário, deletando os dados relacionados a ele no Redis.
    
    Args:
        user_id (int): O ID do usuário cuja sessão de quiz será encerrada.
        
    Deleta as chaves associadas à sessão ativa do quiz e também remove a associação do usuário ao quiz.
    """
    redis_client = get_redis_connection()
    quiz_id = redis_client.get(f"quiz:{user_id}")
    quiz_id = quiz_id.decode('utf-8')
    # Deleta as chaves de controle da sessão do quiz
    redis_client.delete(f"quiz:{quiz_id}:current_quiz_session_id")
    redis_client.delete(f"quiz:{user_id}")
    
    
def redis_active_quiz(quiz_id, quiz_data, user_id):
    """
    Ativa um quiz no Redis, armazenando informações gerais, questões e alternativas,
    além de associar o quiz ao usuário.

    Args:
        quiz_id (int): O ID do quiz a ser ativado.
        quiz_data (dict): Dados do quiz, incluindo o ID do quiz, título e lista de questões.
        user_id (int): O ID do usuário que está ativando o quiz.

    Armazena as informações do quiz, incluindo a associação entre o quiz e o usuário, além das questões, alternativas e dados de classificação no Redis.
    """
    redis_client = get_redis_connection()
    
    # Gera um ID de sessão para o quiz com base no timestamp atual
    quiz_session_id = int(time.time())
    redis_client.set(f"quiz:{quiz_id}:current_quiz_session_id", quiz_session_id)
    
    # Associa o quiz ao usuário no Redis
    redis_client.set(f"quiz:{user_id}", quiz_id)
    
    # Adiciona a lista de IDs das questões ao quiz_info
    question_ids = [str(q['question_id']) for q in quiz_data['questions']]
    
    # Prepara as informações gerais do quiz
    quiz_info = {
        'quiz_id': str(quiz_data['quiz_id']),
        'quiz_owner': str(user_id),
        'title': quiz_data['title'],
        'question_ids': json.dumps(question_ids)
    }
    
    # Armazena as informações gerais do quiz em um Hash no Redis
    redis_client.hset(f"quiz:{quiz_id}:{quiz_session_id}:info", mapping=quiz_info)
    
    # Processa cada questão do quiz
    for q in quiz_data['questions']:
        question_data = {
            'question_id': str(q['question_id']),
            'question_text': q['question_text'],
        }

        # Armazena alternativas da questão em uma lista
        alternatives = [
            {
                'answer_id': str(a['answer_id']),
                'answer_text': a['answer_text'],
                'is_correct': str(a['is_correct']),
                'nm_answer_option': a['nm_answer_option']
            } for a in q['answers']
        ]
        
        # Converte a lista de alternativas para uma string JSON
        question_data['alternatives'] = json.dumps(alternatives)

        # Recupera a resposta correta da questão
        correct_answer = next((a for a in q['answers'] if a['is_correct']), None)

        if correct_answer:
            # Armazena a resposta correta no formato de dicionário
            question_data['correct_answer'] = json.dumps({
                'answer_id': str(correct_answer['answer_id']),
                'answer_text': correct_answer['answer_text'],
                'is_correct': str(correct_answer['is_correct']),
                'nm_answer_option': correct_answer['nm_answer_option']
            })

        # Armazena os dados da questão no Redis
        redis_client.hset(f"quiz:{quiz_id}:{quiz_session_id}:question:{q['question_id']}:info", mapping=question_data)
        
        # Cria dados de classificação para a questão
        ranking_data = {
            'question_order': 0,
            'question_text': q['question_text'],
            'opcao_mais_votada': "",
            'qtd_acertos': 0,
            'qtd_abstencoes': 0,
            'tempo_medio_resposta': 0
        }

        # Armazena os dados de classificação no Redis
        redis_client.hset(f"quiz:{quiz_id}:{quiz_session_id}:question:{q['question_id']}:ranking", mapping=ranking_data)
  
    
        
def initialize_quiz(quiz_id):
    """
    Verifica se o quiz foi iniciado. Retorna o status do quiz com base em uma chave de sessão no Redis.

    Args:
        quiz_id (int): O ID do quiz a ser verificado.

    Returns:
        str: O status do quiz. Retorna '1' se o quiz foi iniciado, ou '0' caso contrário.
    """
    redis_client = get_redis_connection()
    
    # Recupera o ID da sessão atual do quiz a partir do Redis
    quiz_session_id = redis_client.get(f"quiz:{quiz_id}:current_quiz_session_id")
    quiz_session_id = quiz_session_id.decode('utf-8')  # Converte o ID da sessão para string
    
    # Verifica se o quiz foi iniciado, consultando a chave "started" associada à sessão
    game_started = redis_client.get(f"quiz:{quiz_id}:{quiz_session_id}:started")
    
    # Retorna o status do quiz (iniciado ou não)
    return game_started.decode('utf-8') if game_started else "0"


def broadcast_question(quiz_id):
    """
    Transmite a pergunta atual do quiz para todos os clientes conectados via WebSocket.
    
    A função recupera as perguntas do quiz armazenadas no Redis e as envia para os clientes
    conectados, emitindo eventos por WebSocket. Além disso, ela atualiza o ranking de cada pergunta
    e configura o tempo de expiração das chaves relacionadas ao quiz e suas perguntas.

    Args:
        quiz_id (int): O ID do quiz cujas perguntas serão transmitidas.

    Returns:
        None
    """
    redis_client = get_redis_connection()

    # Recupera o ID da sessão atual do quiz
    quiz_session_id = redis_client.get(f"quiz:{quiz_id}:current_quiz_session_id")
    quiz_session_id = quiz_session_id.decode('utf-8')
    
    # Recupera a lista de IDs de perguntas associadas ao quiz
    question_ids = json.loads(redis_client.hget(f"quiz:{quiz_id}:{quiz_session_id}:info", "question_ids"))
    
    # Obtém a quantidade de jogadores conectados
    num_players = redis_client.scard(f"quiz:{quiz_id}:{quiz_session_id}:players")
    
    # Emite uma mensagem 'quiz_started' somente se houver clientes conectados
    socketio.emit('quiz_started', {'quiz_id': quiz_id}, room=quiz_id)

    def send_questions():
        """
        Envia as perguntas do quiz para os clientes conectados e aguarda o tempo necessário
        para cada pergunta. Atualiza o ranking e expira as chaves relevantes no Redis.
        
        O envio das perguntas é interrompido se o quiz for interrompido (existe uma verificação
        no Redis para a sessão do quiz). Cada pergunta é transmitida para os clientes a cada 
        X segundos. O ranking é atualizado após cada pergunta.

        Returns:
            None
        """
        for index, question_id in enumerate(question_ids):
            # Verifica se a sessão do quiz ainda está ativa
            if not redis_client.get(f"quiz:{quiz_id}:current_quiz_session_id"):
                print("Envio de perguntas interrompido")
                return  # Interrompe o envio se a sessão do quiz não estiver mais ativa

            # Atualiza o ranking da pergunta
            redis_client.hset(f"quiz:{quiz_id}:{quiz_session_id}:question:{question_id}:ranking", "qtd_abstencoes", num_players)
            redis_client.hset(f"quiz:{quiz_id}:{quiz_session_id}:question:{question_id}:ranking", "question_order", index + 1)
            
            try:
                # Recupera os dados da pergunta
                question_data = redis_client.hgetall(f"quiz:{quiz_id}:{quiz_session_id}:question:{question_id}:info")
                question_data = {key.decode(): value.decode() for key, value in question_data.items()}
            except redis.RedisError as e:
                print(f"Error accessing Redis: {e}")
                return
            
            # Prepara os dados da pergunta para o envio
            question_data_str = json.dumps(question_data)
            question = json.loads(question_data_str)

            # Emite a pergunta para todos os clientes via WebSocket
            socketio.emit('new_question', {'question': question}, room=quiz_id)
            #print(f"Pergunta {question_id} enviada")
            #print(f"Resposta: {question['correct_answer']}")

            # Aguarda 11 segundos antes de enviar a próxima pergunta
            socketio.sleep(TEMPO_TRANSMISSAO_PERGUNTA)
            
            # Atualiza o ranking da pergunta
            ranking_middle(f"quiz:{quiz_id}:{quiz_session_id}:question:{question_id}")
        
        # Emite uma mensagem de finalização do quiz após o envio de todas as perguntas
        socketio.emit('quiz_finished', {'quiz_id': quiz_id, 'message': 'Quiz finished!'}, room=quiz_id)
        
        # **Nova requisição para obter o ranking**
        try:
            response = requests.get(f"http://127.0.0.1:5000/{quiz_id}/results")

            if response.status_code == 200:
                ranking_data = response.json()
                socketio.emit('quiz_results', ranking_data, room=quiz_id)
            else:
                print(f"Erro ao obter ranking: {response.status_code}, {response.text}")
        except requests.RequestException as e:
            print(f"Erro ao requisitar ranking: {e}")
        
        ################ TEMPO DE EXPIRAÇÃO DAS CHAVES ###################
        # Configura o tempo de expiração para as chaves relacionadas ao quiz
        redis_client.expire(f"quiz:{quiz_id}:{quiz_session_id}:info", EXPIRATION_TIME)
        redis_client.expire(f"quiz:{quiz_id}:{quiz_session_id}:players", EXPIRATION_TIME)
        redis_client.expire(f"quiz:{quiz_id}:{quiz_session_id}:responses", EXPIRATION_TIME)
        redis_client.expire(f"quiz:{quiz_id}:{quiz_session_id}:global:correct_responses", EXPIRATION_TIME)
        redis_client.expire(f"quiz:{quiz_id}:{quiz_session_id}:global:responses_time", EXPIRATION_TIME)

        # Configura o tempo de expiração para as chaves das perguntas individuais
        for index, question_id in enumerate(question_ids):
            current_question_key = f"quiz:{quiz_id}:{quiz_session_id}:question:{question_id}"
            redis_client.expire(f"{current_question_key}:ranking", EXPIRATION_TIME)
            redis_client.expire(f"{current_question_key}:votes", EXPIRATION_TIME)
            redis_client.expire(f"{current_question_key}:voters", EXPIRATION_TIME)
            redis_client.expire(f"{current_question_key}:response_time", EXPIRATION_TIME)
            redis_client.expire(f"{current_question_key}:correct_responses", EXPIRATION_TIME)
            redis_client.expire(f"{current_question_key}:info", EXPIRATION_TIME)

    # Inicia a função `send_questions` como uma tarefa em segundo plano usando o WebSocket
    socketio.start_background_task(send_questions)

    
    
def ranking_middle(current_question_key):
    """
    Processa o ranking da pergunta atual, calculando a opção mais votada e o tempo médio de resposta,
    e atualiza as informações no Redis.
    
    A função recupera os dados de votos e tempos de resposta armazenados no Redis para a pergunta 
    especificada, calcula a opção mais votada e o tempo médio de resposta, e armazena essas informações 
    no ranking da pergunta correspondente.

    Args:
        current_question_key (str): A chave do Redis que representa a pergunta atual no formato 
                                     `quiz:{quiz_id}:{quiz_session_id}:question:{question_id}`.

    Returns:
        None
    """
    redis_client = get_redis_connection()

    try:
        print("Passando pelo ranking middle")
        
        # Obtém a opção mais votada utilizando o comando ZREVRANGE para pegar o item com maior score
        top_option = redis_client.zrevrange(f"{current_question_key}:votes", 0, 0, withscores=True)
        redis_client.hset(f"{current_question_key}:ranking", "opcao_mais_votada", top_option[0][0])
        
        # Calcula o tempo médio de resposta
        response_times = redis_client.zrange(f"{current_question_key}:response_time", 0, -1, withscores=True)
        total_time = sum(time for _, time in response_times)  # Soma os tempos de resposta
        num_users = len(response_times)  # Número de usuários que responderam
        average_time = round(total_time / num_users, 2) if num_users > 0 else 0  # Calcula a média
        redis_client.hset(f"{current_question_key}:ranking", "tempo_medio_resposta", average_time)
        
    except Exception as e:
        print(f"Error in process_question_ranking: {e}")



def handle_player_join(quiz_id, data):
    """
    Lida com o evento de um jogador ingressando em um quiz. A função verifica se o nome de usuário 
    fornecido é válido, se já não foi utilizado por outro jogador e, em seguida, registra o jogador 
    no Redis.

    Args:
        quiz_id (str): O ID do quiz em que o jogador deseja ingressar.
        data (dict): Dados enviados pelo jogador, incluindo o nome de usuário ('username').

    Returns:
        Response: Retorna uma resposta JSON com uma mensagem de sucesso ou erro, dependendo da situação.
    """
    redis_client = get_redis_connection()

    # Recupera o nome de usuário da requisição
    username = data.get('username')
    
    # Recupera o ID da sessão do quiz atual
    quiz_session_id = redis_client.get(f"quiz:{quiz_id}:current_quiz_session_id")
    quiz_session_id = quiz_session_id.decode('utf-8')
    
    print(f"handle_player_join : {quiz_session_id}")
    
    # Verifica se o nome de usuário foi fornecido
    if not username:
        return jsonify({"error": "Username is required"}), 400

    # Define a chave para o conjunto de jogadores no Redis
    players_key = f"quiz:{quiz_id}:{quiz_session_id}:players"
    
    # Verifica se o nome de usuário já está em uso
    if redis_client.sismember(players_key, username):
        return jsonify({"error": "Username is already taken"}), 400

    # Adiciona o nome de usuário ao conjunto de jogadores no Redis
    redis_client.sadd(players_key, username)
    
    # Armazena o nome de usuário na sessão do servidor
    session['username'] = username
    
    # Retorna uma mensagem de sucesso
    return jsonify({"message": "Successfully joined the quiz"}), 200


def submit_player_answer(quiz_id, data):
    """
    Submete a resposta de um jogador para a pergunta atual do quiz. A função valida os dados recebidos 
    (nome de usuário, opção escolhida, tempo de resposta, etc.), registra a resposta do jogador no Redis, 
    e atualiza as estatísticas de votos, tempo de resposta e correção da resposta.

    Args:
        quiz_id (str): O ID do quiz em que o jogador está participando.
        data (dict): Dados enviados pelo jogador, contendo as informações sobre a resposta, incluindo:
            - 'username': Nome de usuário do jogador.
            - 'option': A opção escolhida pelo jogador, que é um dicionário com 'nm_answer_option' e 'is_correct'.
            - 'question_id': ID da pergunta.
            - 'time_taken': O tempo que o jogador levou para responder a pergunta.

    Returns:
        Response: Retorna uma resposta JSON com uma mensagem de sucesso ou erro, dependendo do processamento.
    """
    redis_client = get_redis_connection()
    quiz_session_id = redis_client.get(f"quiz:{quiz_id}:current_quiz_session_id")
    quiz_session_id = quiz_session_id.decode('utf-8')
    
    try:
        # Recupera os dados da requisição
        username = data.get('username')
        option = data.get('option')
        question_id = data.get('question_id')
        time_taken = data.get('time_taken')
        
        # Verifica se os campos obrigatórios foram fornecidos
        if not all([username, option, question_id]):
            return jsonify({"error": "Username, option, and question_id are required"}), 400

        # Garantir que 'option' seja um dicionário
        if isinstance(option, str):
            try:
                option = json.loads(option)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid option format"}), 400

        # Extraí os dados da opção e valida
        nm_answer_option = option.get('nm_answer_option')
        is_correct = option.get('is_correct')

        if not nm_answer_option or is_correct is None:
            return jsonify({"error": "Option must include nm_answer_option and is_correct"}), 400

        # Define as chaves do Redis para registrar os dados
        current_question_key = f"quiz:{quiz_id}:{quiz_session_id}:question:{question_id}"
        redis_keys = {
            "votes": f"{current_question_key}:votes",
            "voters": f"{current_question_key}:voters",
            "responses": f"quiz:{quiz_id}:{quiz_session_id}:responses",
            "response_time": f"{current_question_key}:response_time",
            "correct_responses": f"{current_question_key}:correct_responses",
            "global_correct_responses": f"quiz:{quiz_id}:{quiz_session_id}:global:correct_responses",
            "global_responses_time": f"quiz:{quiz_id}:{quiz_session_id}:global:responses_time",
            "ranking": f"{current_question_key}:ranking"
        }

        # Verifica se o usuário já votou
        if redis_client.sismember(redis_keys["voters"], username):
            return jsonify({"error": "User has already voted"}), 400

        # Registra a resposta do jogador no Redis
        redis_client.hset(redis_keys["responses"], f"{question_id}:{username}", json.dumps({
            "nm_answer_option": nm_answer_option,
            "is_correct": is_correct,
            "timestamp": time.time()
        }))

        # Incrementa os votos para a opção escolhida
        redis_client.zincrby(redis_keys["votes"], 1.0, nm_answer_option)

        # Processa o tempo de resposta e a correção da resposta
        if time_taken and isinstance(time_taken, (int, float)):
            redis_client.zadd(redis_keys["response_time"], {username: time_taken})
            redis_client.zincrby(redis_keys["global_responses_time"], time_taken, username)

            if is_correct == 'True':  # 'True' indica que a resposta está correta
                redis_client.zadd(redis_keys["correct_responses"], {username: time_taken})
                redis_client.hincrbyfloat(redis_keys["global_correct_responses"], f"{username}:response_time", time_taken)
                redis_client.hincrby(redis_keys["global_correct_responses"], f"{username}:correct_responses", 1)
                redis_client.hincrby(redis_keys["ranking"], "qtd_acertos", 1)
        else:
            print(f"Invalid time_taken value: {time_taken}. Expected a number.")

        # Marca o usuário como votante e atualiza a contagem de abstenções
        redis_client.sadd(redis_keys["voters"], username)
        redis_client.hincrby(redis_keys["ranking"], "qtd_abstencoes", -1)

        # Retorna uma mensagem de sucesso
        return jsonify({"message": "Answer submitted successfully"}), 200

    except Exception as e:
        # Registra o erro para depuração
        print(f"Error in submit_answer: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500


def ranking_final(quiz_id):
    """
    Recupera e processa os rankings e resultados de um quiz.

    Esta função calcula os rankings dos alunos com base em suas respostas, 
    tempos de resposta e a precisão de suas respostas. Também gera rankings 
    para as questões com base no número de respostas corretas e abstenções. 
    Os resultados são armazenados no Redis para referência futura.

    Args:
        quiz_id (str): O ID do quiz para o qual processar os resultados.

    Returns:
        dict: Um dicionário contendo os rankings finais e resultados, incluindo:
            - 'students_ranking': Uma lista de alunos classificados por pontuação e tempo de resposta.
            - 'top_students_correct_answer': Uma lista de alunos classificados pelo número de respostas corretas.
            - 'fastest_students': Uma lista de alunos classificados pelo tempo de resposta.
            - 'question_ranking': Rankings brutos para cada questão.
            - 'question_ranking_top_correct_question': Ranking das questões com base no número de respostas corretas.
            - 'question_ranking_top_abstention_question': Ranking das questões com base no número de abstenções.
        
        Caso ocorra um erro, a função retornará um dicionário com a mensagem de erro.

    Raises:
        Exception: Se ocorrer alguma exceção durante o processamento, será retornada uma mensagem de erro.
    """
    redis_client = get_redis_connection()
    try:
        # Recupera o ID da sessão atual do quiz e o proprietário do quiz
        quiz_session_id = redis_client.get(f"quiz:{quiz_id}:current_quiz_session_id")
        quiz_session_id = quiz_session_id.decode('utf-8')
        quiz_owner = redis_client.hget(f"quiz:{quiz_id}:{quiz_session_id}:info", "quiz_owner")
        quiz_owner = quiz_owner.decode('utf-8')
        
        # Recupera os dados globais de respostas corretas do Redis
        correct_responses_key = f"quiz:{quiz_id}:{quiz_session_id}:global:correct_responses"
        all_data = redis_client.hgetall(correct_responses_key)
        all_data = {key.decode('utf-8'): value.decode('utf-8') for key, value in all_data.items()}

        # Processa os dados dos usuários para o ranking
        users_data = {}
        for key, value in all_data.items():
            user_id, attribute = key.split(":")
            users_data.setdefault(user_id, {"user_id": user_id, "response_time": 0, "correct_responses": 0})
            if attribute == "response_time":
                users_data[user_id]["response_time"] = float(value)
            elif attribute == "correct_responses":
                users_data[user_id]["correct_responses"] = int(value)

        # Cria uma lista de usuários com seus dados
        users_list = list(users_data.values())
        
        # Classifica os alunos por pontuação (respostas corretas) e tempo de resposta
        ranked_students = sorted(users_list, key=lambda x: (-x["correct_responses"], x["response_time"]))
        ranked_students_with_positions = [
            {**student, "rank": index + 1} for index, student in enumerate(ranked_students)
        ]

        # Classifica os alunos pelo número de respostas corretas
        top_students = sorted(users_list, key=lambda x: -x["correct_responses"])
        ranked_top_students = [
            {**student, "rank": index + 1} for index, student in enumerate(top_students)
        ] 
        
        # Classifica os alunos pelo tempo de resposta (alunos mais rápidos)
        responses_time_key = f"quiz:{quiz_id}:{quiz_session_id}:global:responses_time"
        top_fastest = redis_client.zrange(responses_time_key, 0, -1, withscores=True)
        ranked_fastest_users = [
            {
                "rank": i + 1,
                "user_id": member.decode('utf-8') if isinstance(member, bytes) else member,
                "response_time": round(score, 2),
            }
            for i, (member, score) in enumerate(top_fastest)
        ]

        # Recupera o ranking de cada questão
        question_ids = json.loads(redis_client.hget(f"quiz:{quiz_id}:{quiz_session_id}:info", "question_ids"))
        question_rank = [
            {
                key.decode('utf-8'): value.decode('utf-8')
                for key, value in redis_client.hgetall(f"quiz:{quiz_id}:{quiz_session_id}:question:{q}:ranking").items()
            }
            for q in question_ids
        ]
        
        # Ranking das questões com mais respostas corretas
        ranked_questions = sorted(
            question_rank,
            key=lambda x: int(x["qtd_acertos"]),
            reverse=True
        )
        question_ranking_top_correct_question = [
            {
                "qtd_acertos": question["qtd_acertos"],
                "question_order": question["question_order"],
                "question_text": question["question_text"],
                "rank": index + 1
            }
            for index, question in enumerate(ranked_questions)
        ]
        
        # Ranking das questões com mais abstenções
        ranked_questions = sorted(
            question_rank,
            key=lambda x: int(x["qtd_abstencoes"]),
            reverse=True
        )
        question_ranking_top_abstention_question = [
            {
                "qtd_abstencoes": question["qtd_abstencoes"],
                "question_order": question["question_order"],
                "question_text": question["question_text"],
                "rank": index + 1
            }
            for index, question in enumerate(ranked_questions)
        ]

        # Compila os resultados finais
        results = {
            "students_ranking": ranked_students_with_positions,
            "top_students_correct_answer": ranked_top_students,
            "fastest_students": ranked_fastest_users,
            "question_ranking": question_rank,
            "question_ranking_top_correct_question": question_ranking_top_correct_question,
            "question_ranking_top_abstention_question": question_ranking_top_abstention_question
        }
        
        # Salva os resultados no Redis
        redis_client.hset(f"quiz:{quiz_id}:hist_rankings", quiz_session_id, json.dumps(results))
        redis_client.expire(f"quiz:{quiz_id}:hist_rankings", EXPIRATION_TIME)
        
        # Limpeza de dados da sessão
        redis_client.delete(f"quiz:{quiz_id}:current_quiz_session_id")
        redis_client.delete(f"quiz:{quiz_owner}")

        return results

    except Exception as e:
        return {"error ranking": str(e)}, 500
