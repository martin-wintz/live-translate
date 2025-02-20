import uuid
from flask import Flask, send_from_directory, request, session
from flask_socketio import SocketIO, join_room
from flask_cors import CORS
import os
from transcription import TranscriptionManager, TranscriptionProcessor
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='../app/build')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_SESSION_COOKIE_SECURE', 'False').lower() == 'true'
socketio = SocketIO(app, cors_allowed_origins=[os.getenv('CORS_ORIGIN')])
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
    return {'transcription': processor.transcription.serialize(), 'status': 'success'}

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    processor = transcription_manager.get_processor(session['client_id'])
    if processor is not None:
        processor.stop_process_audio_queue()
        processor = None
    return {'status': 'success'}

@app.route('/transcriptions', methods=['GET'])
def get_transcriptions():
    transcriptions = transcription_manager.get_transcriptions_dict(session['client_id'])
    return {'transcriptions': transcriptions}

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
    socketio.run(
        app,
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
        port=int(os.getenv('FLASK_PORT', 5555)),
        ssl_context=(
            os.getenv('SSL_CERT_PATH'),
            os.getenv('SSL_KEY_PATH')
        ) if os.getenv('SSL_CERT_PATH') and os.getenv('SSL_KEY_PATH') else None
    )
