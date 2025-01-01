import redis

def connect_redis():
    return redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

def get_hash_field(redis_client, hash_key, field):
    # Obter o valor de um campo específico dentro de um hash
    value = redis_client.hget(hash_key, field)
    return value



def get_top_voted_option(redis_client,question_id,quiz_id):
    z_set_key = f"quiz:{quiz_id}:question:{question_id}:votes"
    
    #hash_key = f"quiz:{quiz_id}:question:{question_id}:info"
    #field = "question_text"  
    # Obter o valor do campo no hash
    #value = get_hash_field(redis_client, hash_key, field)
    # Obter o item com o maior valor (pontuação) do ZSET
    top_option = redis_client.zrevrange(z_set_key, 0, 0, withscores=True)
    
    return top_option
    """
    if top_option:
        # Retorna a chave e o valor (pontuação) do item com maior valor
        return f"A questão \"{value}\" teve a opção {top_option[0][0]} votada {top_option[0][1]} vezes"  # O primeiro item será a chave com maior pontuação
    else:
        return None  # Retorna None se o ZSET estiver vazio
    """
    

def get_set_cardinality(redis_client,question_id,quiz_id):
    
    key = f"quiz:{quiz_id}:question:{question_id}:correct_responses"
    hash_key = f"quiz:{quiz_id}:question:{question_id}:info"
    field = "question_text"  
    # Obter o valor do campo no hash
    value = redis_client.hget(hash_key, field)
    # Obter o número de elementos no set
    cardinality = redis_client.zcard(key)
    return f"A questão \"{value}\" teve {cardinality} acertos"  # O primeiro item será a chave com maior pontuação

def get_non_responders(redis_client, question_id, quiz_id):

    players_key = f"quiz:{quiz_id}:players"
    question_key = f"quiz:{quiz_id}:question:{question_id}:voters"
    
    hash_key = f"quiz:{quiz_id}:question:{question_id}:info"
    field = "question_text"  
    # Obter o valor do campo no hash
    value = get_hash_field(redis_client, hash_key, field)
    # Obter a diferença entre os sets players e voters
    non_responders = redis_client.sdiff(players_key, question_key)
    return f"A questão \"{value}\" teve {len(non_responders)} abstenções"  # O primeiro item será a chave com maior pontuação
    #return non_responders
    
def get_avg_response_time(redis_client,question_id,quiz_id):
    key = f"quiz:{quiz_id}:question:{question_id}:response_time"
    # Get all members and their response times from the sorted set
    response_times = redis_client.zrange(key, 0, -1, withscores=True)
    # Calculate the average response time
    total_time = sum(time for _, time in response_times)
    num_users = len(response_times)
    average_time = total_time / num_users if num_users > 0 else 0

    return f"Tempo médio de resposta: {round(average_time,2)} ms"

def get_ranking(redis_client,quiz_id):
    
    # Chave global
    global_key = f"quiz:{quiz_id}:global:correct_responses"
    # Obter todos os dados da chave global
    all_data = redis_client.hgetall(global_key)
    
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
    
    # Transformar em uma lista para ordenação
    users_list = list(users_data.values())
    
    # Ordenar por correct_responses (descendente) e response_time (ascendente)
    ranked_users = sorted(
        users_list,
        key=lambda x: (-x["correct_responses"], x["response_time"])
    )
    
    return ranked_users


# Função para obter os usuários com mais acertos
def get_top_users(redis_client):
    global_key=f"quiz:{quiz_id}:correct_responses"
    # Obter todos os dados da chave
    all_data = redis_client.hgetall(global_key)
    
    # Filtrar os campos relacionados a correct_responses
    correct_responses = {}
    for key, value in all_data.items():
        if "correct_responses" in key:
            user_id = key.split(":")[0]
            correct_responses[user_id] = int(value)
    
    # Encontrar o maior número de acertos
    max_correct = max(correct_responses.values(), default=0)
    
    # Encontrar os usuários com o maior número de acertos
    top_users = [user for user, score in correct_responses.items() if score == max_correct]
    
    return {
        "max_correct": max_correct,
        "top_users": top_users
    }

# Função para criar o ranking dos alunos mais rápidos
def get_fastest_users(redis_client):
    key = "quiz:global:responses_time"
    # Obter o ranking dos alunos com os menores tempos de resposta (menor é melhor)
    result_with_scores = redis_client.zrange(key, 0, -1, withscores=True)

    # A função zrange já retorna os elementos em ordem crescente do score (menor tempo de resposta vem primeiro)
    return result_with_scores
    

   


    


if __name__ == "__main__":
    r = connect_redis()
   
    quiz_id = "46ba8128-e3a3-4b53-9a39-c5c64d9eacab"  # Exemplo de quiz ID
    question_id = ["49", "50", "51", "52"]
    
    for q in question_id :
        print(get_top_voted_option(r, q, quiz_id))
        print(get_set_cardinality(r, q, quiz_id)) 
        print(get_non_responders(r, q, quiz_id))
        print(get_avg_response_time(r,q,quiz_id))
    
    # Exemplo de uso
    ranking = get_ranking(r)
    print("Ranking dos usuários:")
    for position, user in enumerate(ranking, start=1):
        print(f"{position}. {user['user_id']} - Correct: {user['correct_responses']}, Time: {round(user['response_time'],2)}s")
    
    # Exemplo de uso
    top_correct_ranking = get_top_users(r)
    print(f"alunos com mais acertos ({top_correct_ranking['max_correct']}): {', '.join(top_correct_ranking['top_users'])}")
    
    

    # Obter o top 3 alunos com os menores tempos de resposta
    # Imprimir os membros com seus scores
    top_fastest = get_fastest_users(r)
    print("Membros e scores do sorted set ordenados do menor para o maior:")
    for member, score in top_fastest:
        print(f"{member}: {score}")
    
        
        
    
    





