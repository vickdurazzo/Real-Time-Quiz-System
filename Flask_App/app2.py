from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit

# Inicializando o Flask e o SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta'
socketio = SocketIO(app)

# Rota padrão para renderizar a página inicial
@app.route('/')
def index():
    return render_template('index.html')

# Evento para mensagens
@socketio.on('message')
def handle_message(msg):
    print(f"Mensagem recebida: {msg}")
    send(f"Mensagem recebida: {msg}", broadcast=True)

# Evento customizado
@socketio.on('custom_event')
def handle_custom_event(data):
    print(f"Dados recebidos no evento customizado: {data}")
    emit('response', {'data': 'Evento customizado processado!'}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
