from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO
from flask_cors import CORS
import os
import uuid

app = Flask(__name__, static_folder='../app/build')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000"])
CORS(app)

if not os.path.exists('audio'):
    os.makedirs('audio')

# Dictionary to keep track of audio files for each client
client_audio_files = {}

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')
    # Close the audio file when the client disconnects
    if request.sid in client_audio_files:
        client_audio_files[request.sid].close()
        del client_audio_files[request.sid]

# New endpoint to start recording
@app.route('/start_recording', methods=['POST'])
def start_recording():
    client_id = request.json['clientId']
    unique_id = str(uuid.uuid4())
    audio_file_name = f'audio/audio_file_{client_id}_{unique_id}.wav'
    client_audio_files[client_id] = open(audio_file_name, 'wb')
    return {'uniqueId': unique_id}

# Modified handle_audio_chunk function
@socketio.on('audio_chunk')
def handle_audio_chunk(data, unique_id):
    client_id = request.sid
    audio_file_name = f'audio/audio_file_{client_id}_{unique_id}.wav'
    client_audio_files[client_id].write(data)

# New endpoint to stop recording
@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    client_id = request.json['clientId']
    if client_id in client_audio_files:
        client_audio_files[client_id].close()
        del client_audio_files[client_id]
    return {'status': 'success'}

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5555)