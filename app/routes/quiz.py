# Quiz-related routes
from flask import Blueprint, jsonify, session, request, render_template
from app.models import Quiz, Question, Answer, db
from app.services.redis_service import delete_quiz_from_redis, redis_stop_quiz, redis_active_quiz, check_quiz_session, check_user_quiz_session

################# Funções Auxiliares ################

# Função auxiliar para responder erros
def handle_error(message, code=500):
    """
    Função para retornar uma resposta de erro formatada.
    
    Args:
        message (str): A mensagem de erro a ser retornada.
        code (int): O código de status HTTP (default: 500).

    Returns:
        response: Um objeto JSON com a mensagem de erro e o código de status.
    """
    return jsonify({"message": message}), code

# Função auxiliar para buscar um quiz pelo ID
def get_quiz_by_id(quiz_id, user_specific=True):
    """
    Função para buscar um quiz pelo ID. Opcionalmente, filtra o quiz pelo usuário.
    
    Args:
        quiz_id (str): O ID do quiz a ser buscado.
        user_specific (bool): Se True, filtra o quiz pelo ID do usuário atual (default: True).
    
    Returns:
        Quiz: O objeto Quiz correspondente, ou None se não encontrado.
    """
    filters = {"quiz_id": quiz_id}
    if user_specific:
        filters["user_id"] = session['user_id']
    return Quiz.query.filter_by(**filters).first()

# Função auxiliar para formatar dados de quiz
def format_quiz_data(quiz):
    """
    Formata os dados do quiz para o formato JSON de resposta.
    
    Args:
        quiz (Quiz): O objeto Quiz a ser formatado.

    Returns:
        dict: Um dicionário contendo as informações do quiz e suas questões.
    """
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

########################################################

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route('/quiz', methods=['GET', 'POST'])
def quiz_route():
    """
    Rota para criar um novo quiz ou exibir o formulário de criação de quiz.
    
    Métodos:
    - GET: Exibe o formulário para criar um novo quiz (HTML) ou uma mensagem JSON com a descrição da rota.
    - POST: Cria um novo quiz no banco de dados com base nos dados fornecidos no corpo da requisição JSON.

    Retorna:
        - Para GET: Exibe o formulário HTML ou mensagem JSON.
        - Para POST: Retorna uma mensagem JSON confirmando a criação do quiz ou um erro em caso de falha.
    """
    if request.method == 'GET':
        # Retorna uma mensagem de descrição da rota ou exibe o formulário de criação do quiz
        if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({"message": "Rota para form do quiz"}), 200
        return render_template("create_quiz.html")

    if request.method == 'POST':
        try:
            # Extrai os dados do corpo da requisição
            data = request.get_json()
            quiz_title = data.get('quiz_title')
            questions = data.get('questions', [])

            # Cria um novo quiz no banco de dados
            new_quiz = Quiz(user_id=session['user_id'], title=quiz_title, is_active=False)
            db.session.add(new_quiz)
            db.session.commit()

            # Adiciona as questões e respostas ao quiz
            for question in questions:
                new_question = Question(quiz_id=new_quiz.quiz_id, question_text=question['question_text'])
                db.session.add(new_question)
                db.session.flush()  # Garante que o ID da questão seja gerado

                # Adiciona as respostas de cada questão
                for answer in question['answers']:
                    new_answer = Answer(
                        question_id=new_question.question_id,
                        answer_text=answer['answer_text'],
                        is_correct=answer['is_correct'],
                        nm_answer_option=answer['nm_answer_option']
                    )
                    db.session.add(new_answer)

            # Commit das alterações no banco de dados
            db.session.commit()
           
            # Retorna uma resposta de sucesso
            return jsonify({"message": "Quiz Created successfully!"}), 200

        except Exception as e:
            # Em caso de erro, faz o rollback e retorna a mensagem de erro
            db.session.rollback()
            return handle_error(f"Error: {str(e)}")


@quiz_bp.route('/quiz/<quiz_id>', methods=['GET', 'PUT', 'DELETE'])
def specific_quiz_route(quiz_id):
    """
    Rota para obter, atualizar ou excluir um quiz específico pelo seu ID.
    
    Métodos:
    - GET: Retorna os dados de um quiz específico ou exibe um formulário de atualização.
    - PUT: Atualiza um quiz existente, incluindo suas questões e respostas.
    - DELETE: Exclui um quiz e suas questões/respostas associadas.
    
    Args:
        quiz_id (str): O ID do quiz a ser manipulado.
    
    Retorna:
        - Para GET: Exibe os dados do quiz (JSON ou HTML) ou uma mensagem de erro.
        - Para PUT: Atualiza o quiz e retorna os dados do quiz atualizado ou uma mensagem de erro.
        - Para DELETE: Exclui o quiz e retorna uma mensagem de sucesso ou erro.
    """
    
    if request.method == 'GET':
        try:
            # Busca o quiz pelo ID
            quiz = get_quiz_by_id(quiz_id, user_specific=False)
            if not quiz:
                return handle_error("Quiz não encontrado", 404)

            # Formata os dados do quiz para retornar
            quiz_data = format_quiz_data(quiz)

            # Verifica se a solicitação espera resposta em JSON ou HTML
            if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
                return jsonify({"quiz": quiz_data}), 200

            # Retorna o formulário HTML para atualizar o quiz
            return render_template('update_quiz.html', quiz_data=quiz_data)

        except Exception as e:
            return handle_error(f"Erro: {str(e)}")

    if request.method == 'PUT':
        try:
            # Extrai os dados da requisição
            data = request.get_json()
            quiz = get_quiz_by_id(quiz_id)
            if not quiz:
                return handle_error("Quiz não encontrado ou não autorizado a atualizar", 404)

            # Atualiza o título do quiz
            quiz.title = data.get('quiz_title', quiz.title)
            updated_questions = data.get('questions', [])
            existing_questions = {q.question_id: q for q in Question.query.filter_by(quiz_id=quiz_id).all()}

            # Atualiza as questões e respostas do quiz
            for question_data in updated_questions:
                question_id = question_data.get('question_id')
                question_text = question_data.get('question_text')
                answers = question_data.get('answers', [])

                if question_id in existing_questions:
                    # Atualiza uma questão existente
                    question = existing_questions.pop(question_id)
                    question.question_text = question_text

                    # Atualiza ou adiciona as respostas da questão
                    existing_answers = {a.answer_id: a for a in Answer.query.filter_by(question_id=question.question_id).all()}
                    for answer_data in answers:
                        answer_id = answer_data.get('answer_id')

                        if answer_id in existing_answers:
                            # Atualiza uma resposta existente
                            answer = existing_answers.pop(answer_id)
                            answer.answer_text = answer_data.get('answer_text')
                            answer.is_correct = answer_data.get('is_correct')
                            answer.nm_answer_option = answer_data.get('nm_answer_option')
                        else:
                            # Adiciona uma nova resposta
                            new_answer = Answer(
                                question_id=question.question_id,
                                answer_text=answer_data.get('answer_text'),
                                is_correct=answer_data.get('is_correct'),
                                nm_answer_option=answer_data.get('nm_answer_option')
                            )
                            db.session.add(new_answer)

                    # Exclui respostas que não estão mais associadas à questão
                    for leftover_answer in existing_answers.values():
                        db.session.delete(leftover_answer)
                else:
                    # Adiciona uma nova questão
                    new_question = Question(quiz_id=quiz_id, question_text=question_text)
                    db.session.add(new_question)
                    db.session.flush()

                    # Adiciona as respostas da nova questão
                    for answer_data in answers:
                        new_answer = Answer(
                            question_id=new_question.question_id,
                            answer_text=answer_data.get('answer_text'),
                            is_correct=answer_data.get('is_correct'),
                            nm_answer_option=answer_data.get('nm_answer_option')
                        )
                        db.session.add(new_answer)

            # Exclui questões que não estão mais associadas ao quiz
            for leftover_question in existing_questions.values():
                Answer.query.filter_by(question_id=leftover_question.question_id).delete()
                db.session.delete(leftover_question)

            db.session.commit()

            # Retorna os dados do quiz atualizado
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

            return jsonify({"message": "Quiz atualizado com sucesso!", "quiz": quiz_data}), 200

        except Exception as e:
            db.session.rollback()
            return handle_error(f"Erro: {str(e)}")

    if request.method == 'DELETE':
        try:
            # Busca o quiz pelo ID e verifica se o usuário é o proprietário
            quiz = Quiz.query.filter_by(quiz_id=quiz_id, user_id=session['user_id']).first()
            if not quiz:
                return jsonify({"message": "Quiz não encontrado ou não autorizado a excluir"}), 404

            # Exclui questões e respostas associadas
            questions = Question.query.filter_by(quiz_id=quiz_id).all()
            for question in questions:
                Answer.query.filter_by(question_id=question.question_id).delete()
                db.session.delete(question)

            # Exclui o quiz
            db.session.delete(quiz)
            db.session.commit()

            # Remove o quiz do Redis
            delete_quiz_from_redis(quiz_id)

            return jsonify({"message": "Quiz excluído com sucesso!"}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Erro: {str(e)}"}), 500


@quiz_bp.route('/quiz/<quiz_id>/active', methods=['GET'])
def active_quiz(quiz_id):
    """
    Rota para ativar um quiz específico, iniciando a sessão do quiz para os usuários participarem.

    Método:
    - GET: Ativa o quiz, verificando se ele pode ser iniciado e se o usuário ou o quiz não estão envolvidos em uma sessão ativa.

    Args:
        quiz_id (str): O ID do quiz a ser ativado.

    Retorna:
        - Se o quiz não for encontrado ou o usuário não for autorizado a iniciar, retorna uma mensagem de erro 404.
        - Se já houver uma sessão ativa para o quiz ou para o usuário, retorna uma mensagem de erro específica (401 ou 405).
        - Se o quiz for ativado com sucesso, retorna uma mensagem de sucesso com o ID do quiz.
    """
    
    # Busca o quiz pelo ID
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        return handle_error("Quiz não encontrado ou não autorizado a iniciar", 404)
    
    # Verifica se já existe uma sessão ativa para o quiz
    if check_quiz_session(quiz_id):
        return jsonify({'message': 'Quiz com um jogo já em andamento'}), 401
    
    # Verifica se o usuário já está participando de outro quiz ativo
    if check_user_quiz_session(session['user_id']):
        return jsonify({'message': 'Já existe um quiz seu em andamento'}), 405

    # Formata os dados do quiz para retornar
    quiz_data = format_quiz_data(quiz)
    
    # Ativa o quiz na sessão do Redis
    redis_active_quiz(quiz_id, quiz_data, session['user_id'])
    
    
    
    return jsonify({'message': 'Quiz Ativado', 'quiz_id': str(quiz.quiz_id)}), 200






@quiz_bp.route('/stop-quiz', methods=['POST'])
def stop_quiz():
    """
    Rota para desativar o quiz em andamento, permitindo que um novo jogo seja iniciado.

    Método:
    - POST: Verifica se o usuário está participando de um quiz ativo e, caso positivo, desativa o quiz.

    Retorna:
        - Se o usuário estiver participando de um quiz ativo, retorna uma mensagem de sucesso e desativa o quiz.
        - Se o usuário não tiver nenhum quiz ativo, retorna uma mensagem de erro indicando que não há quiz ativo no momento.
    """
    
    # Verifica se o usuário está participando de um quiz ativo
    if check_user_quiz_session(session['user_id']):
        try:
            # Chama a função para parar o quiz no Redis
            redis_stop_quiz(session['user_id'])
            return jsonify({"message": "Quiz desativado, pronto para novo jogo"}), 200
        except Exception as e:
            # Caso ocorra um erro, retorna a mensagem de erro
            return jsonify({"message": f"Erro: {str(e)}"}), 500
    else:
        # Caso não haja quiz ativo, retorna mensagem de erro
        return jsonify({"message": "Nenhum jogo ativo no momento"}), 500
      
    
    