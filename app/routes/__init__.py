from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'  # Replace with your DB URI
    db.init_app(app)

    # Import blueprints and register
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    return app
