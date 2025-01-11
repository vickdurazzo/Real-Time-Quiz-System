# Socket.IO handlers
from flask import request
from flask_socketio import join_room, leave_room
from app import socketio



# SocketIO Event Listener (ouvindo o evento de conexão)
@socketio.on('connect')
def handle_connect():
    """Quando um cliente se conecta, entra na room do quiz"""
    quiz_id = request.args.get('quiz_id')  # Pegando o quiz_id da URL de conexão
    username = request.args.get('username')  # Pegando o quiz_id da URL de conexão
    if quiz_id:
        join_room(quiz_id)  # Adicionando o cliente à room do quiz
        print("#################################################")
        print(f'Cliente {username} conectado ao quiz: {quiz_id}')
        print("#################################################")

@socketio.on('disconnect')
def handle_disconnect():
    """Quando o cliente desconectar, ele sai da room"""
    quiz_id = request.args.get('quiz_id')
    username = request.args.get('username')  # Pegando o quiz_id da URL de conexão
    if quiz_id:
        leave_room(quiz_id)  # Removendo o cliente da room do quiz
        print("#################################################")
        print(f'Cliente {username} desconectado do quiz: {quiz_id}')
        print("#################################################")