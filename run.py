from app import create_app, socketio
from app.services.websocket import handle_connect, handle_disconnect

app = create_app()

# Certifique-se de que o modo de depuração está ativado
app.config['DEBUG'] = True
app.config['ENV'] = 'development'

if __name__ == '__main__':
    socketio.run(app,host="0.0.0.0", debug=True)
