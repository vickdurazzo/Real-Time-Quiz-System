from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import os
from sqlalchemy import text
from flask_migrate import Migrate
app = Flask(__name__)

# Configure uma chave secreta para a sessão
app.secret_key = os.urandom(12)

# Configure PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://admin:1234@localhost:5432/questionredis"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the User model
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

# Routes
@app.route('/test_db')
def test_db_connection():
    try:
        result = db.session.execute(text("SELECT 1")).scalar()
        if result == 1:
            return "Database connection successful!"
        else:
            return "Database connection failed!"
    except Exception as e:
        return f"Database connection error: {str(e)}"

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            print(data)
            username = data.get('username')
            password = data.get('password')
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            print(hashed_password)
            try:
                new_user = User(
                    nm_user=username,
                    des_user_passwd=hashed_password
                )
                db.session.add(new_user)
                db.session.commit()
                return jsonify({"message": "User registered successfully!"}), 200
            except Exception as e:
                db.session.rollback()
                print(f"Error: {str(e)}")
                return jsonify({"message": f"Error: {str(e)}"}), 500
    
    if request.method == 'GET':
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])  # Convert to dict and return as JSON
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                username = data.get('username')
                password = data.get('password')
                user = User.query.filter_by(nm_user=username).first()
                if user and check_password_hash(user.des_user_passwd, password):
                    session['user_id'] = user.user_id
                    print(session['user_id'])
                    return jsonify({"message": "Login successful!"}), 200
                else:
                    return jsonify({"message": "Invalid credentials"}), 401
            else:
                return jsonify({"message": "Request must be JSON"}), 415
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500
    return render_template('login.html')

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/create_quiz', methods=['GET', 'POST'])
def create_quiz():
    if 'user_id' not in session:
        return redirect(url_for('login'))

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

    return render_template('create_quiz.html')

@app.route('/quiz/<quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

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

@app.route('/<user_id>/quiz', methods=['GET'])
def get_user_quizzes(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        quizzes = Quiz.query.filter_by(user_id=user_id).all()  # Fetch all quizzes for the user
        if not quizzes:
            return jsonify({"message": "You don't have any quizzes yet"}), 404
        
        quizzes_data = [quiz.to_dict() for quiz in quizzes]  # Convert each quiz to a dictionary

        return jsonify(quizzes_data), 200

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/quiz/<quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

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

@app.route('/quiz/<quiz_id>', methods=['PUT'])
def update_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        data = request.get_json()
        quiz = Quiz.query.filter_by(quiz_id=quiz_id, user_id=session['user_id']).first()
        if not quiz:
            return jsonify({"message": "Quiz not found or not authorized to update"}), 404

        quiz_title = data.get('quiz_title')
        is_active = data.get('is_active')
        if quiz_title is not None:
            quiz.title = quiz_title
        if is_active is not None:
            quiz.is_active = is_active

        db.session.commit()
        return jsonify({"message": "Quiz updated successfully!"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
