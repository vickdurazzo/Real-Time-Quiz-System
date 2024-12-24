from app import db
import uuid
from sqlalchemy.dialects.postgresql import UUID

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