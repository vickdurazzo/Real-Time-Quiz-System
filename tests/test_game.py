import requests
import random
import time
from threading import Thread
from socketio import Client
import json

# Configurações gerais
QUIZ_ID = '46ba8128-e3a3-4b53-9a39-c5c64d9eacab'  # ID do quiz

USERS = ['user1', 'user2', 'user3', 'user4', 'user5']  # Usuários simulados
SERVER_URL = 'http://localhost:5000'  # URL do servidor
WEBSOCKET_URL = f"{SERVER_URL}/socket.io"  # URL do WebSocket

# Função para simular a participação de um usuário
def simulate_user(username):
    session = requests.Session()
    try:
        join_url = f"{SERVER_URL}/quiz/{QUIZ_ID}/join"
        join_response = session.post(join_url, json={"username": username})
        
        if join_response.status_code == 200:
            print(f"[{username}] Join response: {join_response.json()['message']}")
        else:
            print(f"[{username}] Failed to join: {join_response.json()['error']}")
            return

        socket = Client()
        quiz_started = False

        @socket.on('quiz_started')
        def on_quiz_started(data):
            nonlocal quiz_started
            print(f"[{username}] Quiz started")
            quiz_started = True

        @socket.on('new_question')
        def on_new_question(data):
            if not quiz_started:
                return
            print(f"[{username}] New question received")
            question_received_time = time.time()
            question_id = data['question']['question_id']
            answer_options = json.loads(data['question']['alternatives'])
            random_delay = random.uniform(1,10)
            time.sleep(random_delay)
            chosen_answer = random.choice(answer_options)
            print(f"[{username}] Chosen answer: {chosen_answer}")

            submit_url = f"{SERVER_URL}/quiz/{QUIZ_ID}/submit_answer"
            submit_response = session.post(submit_url, json={
                "username": username,
                "option": chosen_answer,
                "question_id": question_id,
                "time_taken": time.time() - question_received_time
            })

            if submit_response.status_code == 200:
                print(f"[{username}] Answer submitted: {submit_response.json()['message']}")
            else:
                print(f"[{username}] Failed to submit answer: {submit_response.json()['error']}")

        @socket.on('quiz_finished')
        def on_quiz_finished(data):
            print(f"[{username}] Quiz finished: {data['message']}")
            socket.disconnect()

        websocket_query = f"?quiz_id={QUIZ_ID}&username={username}"
        socket.connect(WEBSOCKET_URL + websocket_query)
        print(f"[{username}] Connected to WebSocket.")
        socket.wait()

    except Exception as e:
        print(f"[{username}] Error: {e}")

# Função para buscar resultados do quiz
def fetch_results():
    try:
        results_url = f"{SERVER_URL}/{QUIZ_ID}/results"
        response = requests.get(results_url)
        if response.status_code == 200:
            data = response.json()
            print("Ranking".center(80, "="))
            print("")
            print("Alternativas Mais Votadas".center(80))
            print("")
            for question in data["ranking"]["question_ranking"]:
                print(f"{question['question_order']}.{question['question_text']} : {question['opcao_mais_votada']}".center(80))
                
            print("")
            print("Questões mais acertadas".center(80))
            print("")   
            for question in data["ranking"]["question_ranking_top_correct_question"]:
                print(f"{question['rank']}.{question['question_text']} : {question['qtd_acertos']}".center(80))
                
            print("")
            print("Questões com mais abstenções".center(80))
            print("")   
            for question in data["ranking"]["question_ranking_top_abstention_question"]:
                print(f"{question['rank']}.{question['question_text']} : {question['qtd_abstencoes']}".center(80))

            print("")
            print("Tempo médio de resposta por questão".center(80))
            print("")   
            ranked_questions = sorted(
                data["ranking"]["question_ranking"], 
                key=lambda x: float(x["tempo_medio_resposta"]) if x["tempo_medio_resposta"] != "0" else float('inf')
            )

            for rank, question in enumerate(ranked_questions, start=1):
                print(f"{rank}.{question['question_text']} : {question['tempo_medio_resposta']}".center(80))  


            print("")
            print("Alunos com maior acerto e mais rápidos".center(80))
            print("")
            for question in data["ranking"]["students_ranking"]:
                print(f"{question['rank']}.{question['user_id']} : {question['correct_responses']} acertos em {round(question['response_time'],2)} segundos".center(80))

            print("")
            print("Alunos com maior acerto".center(80))
            print("")
            for question in data["ranking"]["top_students_correct_answer"]:
                print(f"{question['rank']}.{question['user_id']} : {question['correct_responses']} acertos em {round(question['response_time'],2)} segundos".center(80))



            print("")
            print("Alunos mais rápidos".center(80))
            print("")
            for question in data["ranking"]["fastest_students"]:
                print(f"{question['rank']}.{question['user_id']} : {round(question['response_time'],2)} segundos".center(80))
                
            print("=" * 80)  # Linha de separação ao final

        else:
            print(f"Failed to fetch results: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Error fetching results: {e}")

# Simular os usuários participando do quiz
def run_test():
    print("Starting test simulation...")
    threads = []

    for username in USERS:
        thread = Thread(target=simulate_user, args=(username,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    print("Test simulation completed.")
    fetch_results()  # Buscar os resultados após a simulação

# Executar o teste
if __name__ == "__main__":
    run_test()
