from flask import Blueprint, jsonify, session, request, render_template
from app.services.redis_service import get_redis_connection, handle_player_join, initialize_quiz, check_quiz_session, broadcast_question, ranking_final, submit_player_answer

# Criação do Blueprint para o grupo de rotas relacionadas ao jogo
game_bp = Blueprint('game', __name__)

# Rota para iniciar o quiz
@game_bp.route('/start_quiz/<quiz_id>', methods=['GET','POST'])  # INICIAR O QUIZ
def start_quiz(quiz_id):
    """
    Inicia a dinâmica do quiz e transmite as questões em tempo real.
    
    Dependendo do método HTTP (GET ou POST), realiza diferentes ações:
    - GET: Inicializa o quiz e retorna uma mensagem.
    - POST: Inicia o quiz em andamento e transmite as perguntas em tempo real para os jogadores.
    """
    
    if request.method == 'GET':
        # Inicia o quiz chamando a função 'initialize_quiz' passando o ID do quiz.
        game_started = initialize_quiz(quiz_id)
        
        # Retorna uma resposta com a mensagem indicando se o quiz foi iniciado com sucesso.
        return jsonify({"message": game_started})
    
    if request.method == 'POST':
        try:
            # Verifica se já existe uma sessão de quiz ativa com o ID fornecido
            if check_quiz_session(quiz_id):
                
                # Se houver uma sessão ativa, transmite as questões aos jogadores em tempo real.
                broadcast_question(quiz_id)
                
                # Retorna uma resposta indicando que o quiz foi iniciado e as questões estão sendo enviadas.
                return jsonify({"message": "Quiz started and questions are being sent"}), 200
            else:
                # Caso não haja um quiz em andamento, retorna uma mensagem de erro.
                return jsonify({"message": "Nenhum jogo em andamento"}), 404
        except Exception as e:
            # Em caso de erro, retorna a mensagem de erro.
            return jsonify({"error": str(e)}), 500

        

@game_bp.route('/quiz/<quiz_id>/join', methods=['GET', 'POST'])  # Jogadores entram e se cadastram
def join_quiz(quiz_id):
    """
    Permite que um jogador entre em um quiz existente e se cadastre para participar.
    
    Dependendo do método HTTP (GET ou POST), realiza diferentes ações:
    - GET: Exibe a tela de entrada para o jogador se registrar no quiz.
    - POST: Recebe os dados do jogador e realiza o cadastro no quiz.
    
    Args:
        quiz_id (str): ID único do quiz que o jogador deseja entrar.
    
    Retorna:
        - GET: Renderiza a página HTML de entrada para o jogo.
        - POST: Processa o cadastro do jogador e retorna a resposta com sucesso ou erro.
    """
    
    if request.method == 'GET':
        # Retorna uma mensagem de descrição da rota ou exibe o formulário para entrar no quiz
        if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({"message": "Rota para entrar no quiz"}), 200
        # Renderiza a página HTML de entrada onde o jogador pode se cadastrar no quiz.
        return render_template('join_quiz.html', quiz_id=quiz_id)
    
    if request.method == 'POST':
        # Chama a função 'handle_player_join' para processar o cadastro do jogador com os dados recebidos.
        return handle_player_join(quiz_id, request.json)



@game_bp.route('/quiz/<quiz_id>/<username>/game')
def game(quiz_id, username, methods=['GET']):
    """
    Exibe a página de jogo para um jogador específico dentro de um quiz.

    Esta rota renderiza a página HTML de jogo, fornecendo o `quiz_id` e o `username` como parâmetros para personalizar a experiência do jogador.

    Args:
        quiz_id (str): O ID único do quiz que o jogador está participando.
        username (str): O nome de usuário do jogador, usado para personalizar a página de jogo.

    Retorna:
        - Renderiza a página `game.html`, passando o `quiz_id` e o `username` como variáveis para a página.
    """
    # Retorna uma mensagem de descrição da rota ou exibe a pagina do jogo
    if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({"message": "Rota do jogo"}), 200
    return render_template('game.html', quiz_id=quiz_id, username=username)


@game_bp.route('/quiz/<quiz_id>/submit_answer', methods=['POST'])
def submit_answer(quiz_id):
    """
    Submete uma resposta para a pergunta atual no quiz.

    Esta rota é chamada quando um jogador envia uma resposta para uma pergunta durante o jogo. A resposta é processada e verificada para determinar se está correta ou não.

    Args:
        quiz_id (str): O ID único do quiz em que o jogador está participando.
    
    Retorna:
        - Em caso de sucesso: A resposta é processada, e o resultado da operação é retornado.
        - Em caso de erro: Um erro é retornado com uma mensagem apropriada.
    """
    try:
        # Imprime uma mensagem no console para indicar que a resposta foi enviada
        print("Resposta enviada")

        # Chama a função `submit_player_answer` que processa a resposta enviada pelo jogador
        return submit_player_answer(quiz_id, request.json)
    
    except Exception as e:
        # Em caso de erro durante o processo, retorna um erro 500 com a mensagem de exceção
        return jsonify({"error": str(e)}), 500



@game_bp.route('/<quiz_id>/results', methods=['GET'])  
def ranking(quiz_id):
    """
    Retorna o ranking dos jogadores no quiz.

    Esta rota é chamada para obter a classificação dos jogadores com base no desempenho no quiz. O ranking é calculado considerando as respostas dos jogadores e suas pontuações no jogo.

    Args:
        quiz_id (str): O ID único do quiz para o qual o ranking é solicitado.
    
    Retorna:
        - Em caso de sucesso: Um objeto JSON contendo o ranking dos jogadores.
        - Em caso de erro: Um objeto JSON contendo uma mensagem de erro.
    """
    try:
        # Chama a função `ranking_final` que calcula e retorna o ranking dos jogadores do quiz
        data = ranking_final(quiz_id)

        # Processa os dados do ranking
        ranking_response = {
            "ranking": {
                "alternativas_mais_votadas": [
                    {
                        "question_order": question["question_order"],
                        "question_text": question["question_text"],
                        "opcao_mais_votada": question["opcao_mais_votada"]
                    }
                    for question in data["question_ranking"]
                ],
                "questoes_mais_acertadas": [
                    {
                        "rank": question["rank"],
                        "question_text": question["question_text"],
                        "qtd_acertos": question["qtd_acertos"]
                    }
                    for question in data["question_ranking_top_correct_question"]
                ],
                "questoes_com_mais_abstencao": [
                    {
                        "rank": question["rank"],
                        "question_text": question["question_text"],
                        "qtd_abstencoes": question["qtd_abstencoes"]
                    }
                    for question in data["question_ranking_top_abstention_question"]
                ],
                "tempo_medio_resposta_por_questao": [
                    {
                        "rank": idx + 1,
                        "question_text": question["question_text"],
                        "tempo_medio_resposta": float(question["tempo_medio_resposta"]) if question["tempo_medio_resposta"] != "0" else float('inf')
                    }
                    for idx, question in enumerate(sorted(data["question_ranking"], key=lambda x: float(x["tempo_medio_resposta"]) if x["tempo_medio_resposta"] != "0" else float('inf')))
                ],
                "alunos_com_maior_acerto_e_mais_rapidos": [
                    {
                        "rank": student["rank"],
                        "user_id": student["user_id"],
                        "correct_responses": student["correct_responses"],
                        "response_time": round(student["response_time"], 2)
                    }
                    for student in data["students_ranking"]
                ],
                "alunos_com_maior_acerto": [
                    {
                        "rank": student["rank"],
                        "user_id": student["user_id"],
                        "correct_responses": student["correct_responses"],
                        "response_time": round(student["response_time"], 2)
                    }
                    for student in data["top_students_correct_answer"]
                ],
                "alunos_mais_rapidos": [
                    {
                        "rank": student["rank"],
                        "user_id": student["user_id"],
                        "response_time": round(student["response_time"], 2)
                    }
                    for student in data["fastest_students"]
                ]
            }
        }

        

        return jsonify(ranking_response), 200

    except Exception as e:
        # Em caso de erro ao calcular o ranking, retorna um erro 500 com a mensagem de exceção
        return jsonify({"error api": str(e)}), 500


                    