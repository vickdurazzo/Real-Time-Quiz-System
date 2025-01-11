## Configuration settings (e.g., database URI)
import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://admin:1234@localhost:5432/questionredis')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
