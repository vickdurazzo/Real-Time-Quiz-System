
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User,Quiz,Question,Answer

quiz_bp = Blueprint('quiz', __name__)


@quiz_bp.route('/quiz', methods=['GET','POST'])
def quiz_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    #Return Quizzes
    if request.method == 'GET':
        try:
            quizzes = Quiz.query.filter_by(user_id=session['user_id']).all()  # Fetch all quizzes for the user
            if not quizzes:
                return jsonify({"message": "You don't have any quizzes yet"}), 404
            
            quizzes_data = [quiz.to_dict() for quiz in quizzes]  # Convert each quiz to a dictionary

            return jsonify(quizzes_data), 200

        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500
    #Create Quiz
    if request.method == 'POST':
        try:
            data = request.get_json()
            quiz_title = data.get('quiz_title')
            questions = data.get('questions')

            new_quiz = Quiz(
                user_id=session['user_id'],
                title=quiz_title,
                is_active = 0
            )
            db.session.add(new_quiz)
            db.session.commit()

            for question in questions:
                new_question = Question(
                    quiz_id=new_quiz.quiz_id,
                    question_text=question['question_text']
                )
                db.session.add(new_question)
                db.session.commit()

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
            return jsonify({"message": f"Error: {str(e)}"}), 500
        
# Specific quiz
@quiz_bp.route('/quiz/<quiz_id>', methods=['GET','PUT','DELETE']) #Get specific quiz data
def specific_quiz_route(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    #Return Quiz Data
    if request.method == 'GET':
        try:
            quiz = Quiz.query.filter_by(quiz_id=quiz_id).first()
            if not quiz:
                return jsonify({"message": "Quiz not found"}), 404

            questions = Question.query.filter_by(quiz_id=quiz.quiz_id).all()
            quiz_data = quiz.to_dict()
            quiz_data['questions'] = []

            for question in questions:
                question_data = question.to_dict()
                answers = Answer.query.filter_by(question_id=question.question_id).all()
                question_data['answers'] = [answer.to_dict() for answer in answers]
                quiz_data['questions'].append(question_data)

            return jsonify(quiz_data), 200

        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500
       
    # Update Quiz
    if request.method == 'PUT':
        try:
            data = request.get_json()
            quiz = Quiz.query.filter_by(quiz_id=quiz_id, user_id=session['user_id']).first()
            if not quiz:
                return jsonify({"message": "Quiz not found or not authorized to update"}), 404

            # Update quiz title and is_active status
            quiz_title = data.get('quiz_title')
            is_active = data.get('is_active')
            if quiz_title is not None:
                quiz.title = quiz_title
            if is_active is not None:
                quiz.is_active = is_active

            # Update questions and answers
            updated_questions = data.get('questions', [])
            existing_questions = {q.question_id: q for q in Question.query.filter_by(quiz_id=quiz_id).all()}

            for question_data in updated_questions:
                question_id = question_data.get('question_id')
                question_text = question_data.get('question_text')
                answers = question_data.get('answers', [])

                if question_id in existing_questions:
                    # Update existing question
                    question = existing_questions.pop(question_id)
                    question.question_text = question_text

                    # Update answers for the question
                    existing_answers = {a.answer_id: a for a in Answer.query.filter_by(question_id=question.question_id).all()}
                    for answer_data in answers:
                        answer_id = answer_data.get('answer_id')
                        answer_text = answer_data.get('answer_text')
                        is_correct = answer_data.get('is_correct')
                        nm_answer_option = answer_data.get('nm_answer_option')

                        if answer_id in existing_answers:
                            # Update existing answer
                            answer = existing_answers.pop(answer_id)
                            answer.answer_text = answer_text
                            answer.is_correct = is_correct
                            answer.nm_answer_option = nm_answer_option
                        else:
                            # Add new answer
                            new_answer = Answer(
                                question_id=question.question_id,
                                answer_text=answer_text,
                                is_correct=is_correct,
                                nm_answer_option=nm_answer_option
                            )
                            db.session.add(new_answer)

                    # Remove any leftover answers
                    for leftover_answer in existing_answers.values():
                        db.session.delete(leftover_answer)
                else:
                    # Add new question and its answers
                    new_question = Question(
                        quiz_id=quiz_id,
                        question_text=question_text
                    )
                    db.session.add(new_question)
                    db.session.flush()  # Ensure new_question has an ID

                    for answer_data in answers:
                        new_answer = Answer(
                            question_id=new_question.question_id,
                            answer_text=answer_data.get('answer_text'),
                            is_correct=answer_data.get('is_correct'),
                            nm_answer_option=answer_data.get('nm_answer_option')
                        )
                        db.session.add(new_answer)

            # Remove any leftover questions
            for leftover_question in existing_questions.values():
                Answer.query.filter_by(question_id=leftover_question.question_id).delete()
                db.session.delete(leftover_question)

            db.session.commit()
            return jsonify({"message": "Quiz updated successfully!"}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Error: {str(e)}"}), 500
        
    #Delete Quiz
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