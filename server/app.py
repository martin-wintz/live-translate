import uuid
from flask import Flask, send_from_directory, request, session
from flask_socketio import SocketIO, join_room
from flask_cors import CORS
import os
from pydub import AudioSegment
from queue import Queue
import threading
from transcription import TranscriptionManager, TranscriptionProcessor, TranscriptionAudioQueue
from pydub import AudioSegment

app = Flask(__name__, static_folder='../app/build')
app.config['SECRET_KEY'] = 'secret!'
# app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = False # Dev only
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000"])
CORS(app, supports_credentials=True)

if not os.path.exists('audio'):
    os.makedirs('audio')

transcription = None
transcription_manager = TranscriptionManager()

# ----------------- Socket.io -----------------
@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    join_room(request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    print(f'Client disconnected: {client_id}')

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    client_id = data['clientId']
    audio_data = data['arrayBuffer']

    processor = transcription_manager.get_processor(client_id)
    if processor:
        processor.queue_audio(audio_data)
    else:
        print(f'No processor found for client {client_id}')
        pass

def transcription_callback(transcriptions):
    socketio.emit('transcription', transcriptions)

def translation_callback(phrase):
    socketio.emit('translation', phrase)

# ----------------- API -----------------
@app.route('/start_recording', methods=['POST'])
def start_recording():
    processor = TranscriptionProcessor(session['client_id'], transcription_callback, translation_callback)
    processor.start_process_audio_queue()
    transcription_manager.set_processor(session['client_id'], processor)
    return {'status': 'success'}

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    processor = transcription_manager.get_processor(session['client_id'])
    if processor is not None:
        processor.stop_process_audio_queue()
        processor = None
    return {'status': 'success'}

@app.route('/init_session', methods=['POST'])
def init_session():
    # Generate a random client id and store it in the session
    if 'client_id' not in session:
        session['client_id'] = str(uuid.uuid4())
    return {'client_id': session['client_id']}

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5555)
