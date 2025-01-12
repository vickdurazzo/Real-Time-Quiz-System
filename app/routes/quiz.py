# Quiz-related routes
from flask import Blueprint, jsonify,session,request,render_template

from app.models import Quiz,Question,Answer,db
from app.services.redis_service import delete_quiz_from_redis, redis_stop_quiz,redis_active_quiz,check_quiz_session,check_user_quiz_session




################# Funções Auxilares ################

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

########################################################

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route('/quiz', methods=['GET', 'POST'])
def quiz_route():
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

@quiz_bp.route('/quiz/<quiz_id>', methods=['GET', 'PUT', 'DELETE'])
def specific_quiz_route(quiz_id):
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
            delete_quiz_from_redis(quiz_id)
            return jsonify({"message": "Quiz deleted successfully!"}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Error: {str(e)}"}), 500


@quiz_bp.route('/quiz/<quiz_id>/active', methods=['GET']) #ATIVAR O QUIZ
def active_quiz(quiz_id):
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        return handle_error("Quiz not found or not authorized to start", 404)
    
    if check_quiz_session(quiz_id):
        return jsonify({'message': 'Quiz com um jogo já em andamento'}),401
    
    if check_user_quiz_session(session['user_id']):
        return jsonify({'message': 'Já existe um quiz seu em andamento'}),405
   

    quiz_data = format_quiz_data(quiz)
    
    
    redis_active_quiz(quiz_id,quiz_data,session['user_id'])
       
    #quiz.is_active = True
    #db.session.commit()
    return jsonify({'message': 'Quiz Ativado', 'quiz_id': str(quiz.quiz_id)}), 200

@quiz_bp.route('/stop-quiz',methods=['POST'])
def stop_quiz():
    if check_user_quiz_session(session['user_id']):
        try:
            redis_stop_quiz(session['user_id'])
            return jsonify({"message":"Quiz desativado, pronto para novo jogo"}),200
        except Exception as e:
            return jsonify({"message":f"Error: {str(e)}"}), 500
    else :
        return jsonify({"message":"Nenhum jogo ativo no momento"}),500
            
       
            
    
    