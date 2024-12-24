from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import redis


db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    
    db.init_app(app)
    migrate.init_app(app, db)
    # Initialize Redis using redis-py
    app.redis_client = redis.StrictRedis.from_url(app.config['REDIS_URL'], decode_responses=True)

    from app.routes.auth import auth_bp
    from app.routes.quiz import quiz_bp
    from app.routes.game import game_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(game_bp)
    
    return app
