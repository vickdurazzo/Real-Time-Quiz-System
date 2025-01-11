#This file will set up the Flask app, extensions, and Blueprints.
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_migrate import Migrate
from app.config import Config

db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'sua_chave_secreta'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:1234@localhost:5432/questionredis'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Desativa warnings desnecessários


    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.home import home_bp
    from app.routes.quiz import quiz_bp
    from app.routes.game import game_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(game_bp)

    return app
