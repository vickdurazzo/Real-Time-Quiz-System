import requests
import random
import time
from threading import Thread
from socketio import Client
import json
import time  


# Configurações gerais
QUIZ_ID = '46ba8128-e3a3-4b53-9a39-c5c64d9eacab'  # ID do quiz

USERS = ['user1', 'user2', 'user3','user4','user5']  # Usuários simulados
SERVER_URL = 'http://localhost:5000'  # URL do servidor
WEBSOCKET_URL = f"{SERVER_URL}/socket.io"  # URL do WebSocket

# Opções de resposta simuladas
ANSWER_OPTIONS = [
    {"answer_id": "1", "answer_text": "Option A", "is_correct": "False", "nm_answer_option": "A"},
    {"answer_id": "2", "answer_text": "Option B", "is_correct": "True", "nm_answer_option": "B"},
    {"answer_id": "3", "answer_text": "Option C", "is_correct": "False", "nm_answer_option": "C"},
    {"answer_id": "4", "answer_text": "Option D", "is_correct": "False", "nm_answer_option": "D"}
]

# Função para simular a participação de um usuário
def simulate_user(username):
    try:
        # Etapa 1: Enviar requisição para a rota /quiz/<quiz_id>/join
        join_url = f"{SERVER_URL}/quiz/{QUIZ_ID}/join"
        join_response = requests.post(join_url, json={"username": username})
        
        if join_response.status_code == 200:
            print(f"[{username}] Join response: {join_response.json()['message']}")
        else:
            print(f"[{username}] Failed to join: {join_response.json()['error']}")
            return

        # Etapa 2: Conectar ao WebSocket
        socket = Client()

        # Variável para indicar se o quiz começou
        quiz_started = False

        # Escutar evento de início do quiz
        @socket.on('quiz_started')
        def on_quiz_started(data):
            nonlocal quiz_started
            print(f"[{username}] Quiz started: {data}")
            quiz_started = True

        # Escutar evento de nova questão e enviar resposta
        @socket.on('new_question')
        def on_new_question(data):
            if not quiz_started:
                return  # Ignorar questões se o quiz ainda não começou
            
            print(f"[{username}] New question received: {data}")
            print("###########################################")

            # Capture the timestamp when the question is received
            question_received_time = time.time()  # Unix timestamp in seconds

            question_id = data['question']['question_id']
            print(f"[{username}] ID DA QUESTAO: {question_id}")
            answer_options = json.loads(data['question']['alternatives'])

            # Simulate a random delay before choosing an answer
            min_delay = 1  # Minimum delay in seconds
            max_delay = 5  # Maximum delay in seconds
            random_delay = random.uniform(min_delay, max_delay)  # Generate a random delay between min_delay and max_delay
            time.sleep(random_delay)  # Simulate the user taking a random amount of time to answer


            chosen_answer = random.choice(answer_options)  # Escolhe uma resposta aleatória
            print(f"[{username}] RESPOSTA ESCOLHIDA : {chosen_answer}")

            
            

            # Enviar resposta
            submit_url = f"{SERVER_URL}/quiz/{QUIZ_ID}/submit_answer"
            submit_response = requests.post(submit_url, json={
                "username": username,
                "option": chosen_answer,  # Enviar o objeto completo da resposta
                "question_id": question_id,
                "time_taken": ((time.time()) - question_received_time)  # Include the time taken in the payload
            })

            
            if submit_response.status_code == 200:
                print(f"[{username}] Answer submitted: {submit_response.json()['message']}")
            else:
                print(f"[{username}] Failed to submit answer: {submit_response.json()['error']}")
        

        # Escutar evento de finalização do quiz
        @socket.on('quiz_finished')
        def on_quiz_finished(data):
            print(f"[{username}] Quiz finished: {data['message']}")
            socket.disconnect()

        # Conectar ao WebSocket com parâmetros de consulta na URL
        websocket_query = f"?quiz_id={QUIZ_ID}&username={username}"
        socket.connect(WEBSOCKET_URL + websocket_query)
        print(f"[{username}] Connected to WebSocket.")

        # Manter o WebSocket ativo até que seja desconectado
        socket.wait()

    except Exception as e:
        print(f"[{username}] Error: {e}")

# Simular dois usuários participando do quiz
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

# Executar o teste
if __name__ == "__main__":
    run_test()
