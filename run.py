from app import create_app, socketio
from app.services.websocket import handle_connect, handle_disconnect

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True)
