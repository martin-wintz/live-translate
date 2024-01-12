import uuid
from flask import Flask, send_from_directory, request, session
from flask_socketio import SocketIO, join_room
from flask_cors import CORS
import os
from pydub import AudioSegment
from queue import Queue
import threading
from transcription import TranscriptionManager, TranscriptionAudioQueue
from pydub import AudioSegment

app = Flask(__name__, static_folder='../app/build')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000"])
CORS(app)

if not os.path.exists('audio'):
    os.makedirs('audio')

transcription = None
audio_queue = TranscriptionAudioQueue()

# ----------------- Socket.io -----------------
@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    join_room(request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    global transcription
    if transcription is not None:
        transcription.stop_process_audio_queue()
        transcription = None
    print(f'Client disconnected: {client_id}')

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    audio_queue.add_audio(data)

def transcription_callback(text):
    socketio.emit('transcription', text)

# ----------------- API -----------------
@app.route('/start_recording', methods=['POST'])
def start_recording():
    global transcription
    transcription = TranscriptionManager(session['client_id'], transcription_callback)
    thread = threading.Thread(target=transcription.start_process_audio_queue, args=(audio_queue,))
    thread.start()
    return {'status': 'success'}

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global transcription
    if transcription is not None:
        transcription.stop_process_audio_queue()
        transcription = None
    return {'status': 'success'}

@app.route('/init_session', methods=['POST'])
def init_session():
    # Generate a random client id and store it in the session
    if 'client_id' not in session:
        session['client_id'] = str(uuid.uuid4())
        print(f"********** Client id created: {session['client_id']}")
    return {'client_id': session['client_id']}

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5555)
