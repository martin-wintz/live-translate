import uuid
from flask import Flask, send_from_directory, request, session
from flask_socketio import SocketIO, join_room
from flask_cors import CORS
import os
from transcription import TranscriptionManager, TranscriptionController
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='../app/build')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
socketio = SocketIO(app, cors_allowed_origins=[os.getenv('CORS_ORIGIN')])
CORS(app)

if not os.path.exists('audio'):
    os.makedirs('audio')

transcription_manager = TranscriptionManager()

@socketio.on('connect')
def handle_connect():
    client_id = str(uuid.uuid4())
    join_room(request.sid)
    print(f"Client connected: {client_id}")
    return {'client_id': client_id}

@socketio.on('start_recording')
def handle_start_recording():
    print("Starting recording for client", request.sid)
    client_id = request.sid

    def transcription_callback(transcriptions):
        socketio.emit('transcription', transcriptions, room=client_id)

    def translation_callback(phrase):
        socketio.emit('translation', phrase, room=client_id)

    controller = TranscriptionController(client_id, transcription_callback, translation_callback)
    controller.start_processing()
    transcription_manager.set_processor(client_id, controller)
    return {'transcription': controller.transcription.serialize(), 'status': 'success'}

@socketio.on('stop_recording')
def handle_stop_recording():
    print("Stopping recording for client", request.sid)
    client_id = request.sid
    controller = transcription_manager.get_processor(client_id)
    if controller:
        controller.stop_processing()
        transcription_manager.remove_processor(client_id)
    return {'status': 'success'}

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    client_id = request.sid
    controller = transcription_manager.get_processor(client_id)
    if controller:
        controller.queue_audio(data['arrayBuffer'])
    else:
        print(f'No processor found for client {client_id}')

@socketio.on('disconnect')
def handle_disconnect():
    print("Disconnecting client", request.sid)
    client_id = request.sid
    controller = transcription_manager.get_processor(client_id)
    if controller:
        controller.stop_processing()
        transcription_manager.remove_processor(client_id)

# Static file serving
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    socketio.run(app, 
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
        port=int(os.getenv('FLASK_PORT', 5555)),
        ssl_context=(
            os.getenv('SSL_CERT_PATH'),
            os.getenv('SSL_KEY_PATH')
        ) if os.getenv('SSL_CERT_PATH') and os.getenv('SSL_KEY_PATH') else None
    )
