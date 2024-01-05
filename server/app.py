from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO
from flask_cors import CORS
import os
import uuid
import whisper
import io
from pydub import AudioSegment

app = Flask(__name__, static_folder='../app/build')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000"])
CORS(app)

# TODO: Automatically detect if GPU is available
use_fp16 = False

# Initialize whisper model
model = whisper.load_model('tiny.en')

if not os.path.exists('audio'):
    os.makedirs('audio')

# Dictionary to keep track of audio files for each client
client_audio_files = {}

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    print(f'Client disconnected: {client_id}')
    # Close the audio file when the client disconnects
    end_current_file(client_id)

from pydub import AudioSegment

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    client_id = request.sid

    if client_id not in client_audio_files:
        start_new_file(client_id)

    audio_file_info = client_audio_files[client_id]
    audio_file_path = audio_file_info['file_name']

    # Append new audio data to the file
    with open(audio_file_path, 'ab') as audio_file:
        audio_file.write(data)

    # Load the audio file as an AudioSegment
    audio = AudioSegment.from_file(audio_file_path)

    # Only analyze the last 3 seconds of the audio
    if len(audio) > 3000:  # AudioSegment.length is in milliseconds
        last_3_seconds = audio[-3000:]  # Get the last 3 seconds

        temp_filename = f"temp_recent_audio_{client_id}.wav"
        last_3_seconds.export(temp_filename, format="wav")

        # Use Whisper to transcribe/analyze the last 3 seconds of audio
        partial_transcription = model.transcribe(temp_filename, fp16=use_fp16)
        os.remove(temp_filename)  # Clean up the temporary file

        print('PARTIAL: ' + partial_transcription['text'])

        if not partial_transcription['text'].strip():  # If the recent audio is silent
            print('Silence detected')
            end_current_file(client_id)
            start_new_file(client_id)
        else:
            full_transcription = model.transcribe(audio_file_path, fp16=use_fp16)
            print('FULL: ' + full_transcription['text'])
            socketio.emit('transcription', full_transcription['text'], room=client_id)
    else:
        print("File too short for analysis.")

def start_new_file(client_id):
    unique_id = str(uuid.uuid4())
    audio_file_name = f'audio/audio_file_{client_id}_{unique_id}.wav'
    client_audio_files[client_id] = {
        'file_name': audio_file_name
    }

def end_current_file(client_id):
    if client_id in client_audio_files:
        del client_audio_files[client_id]

@app.route('/start_recording', methods=['POST'])
def start_recording():
    client_id = request.json['clientId']
    start_new_file(client_id)
    return {'uniqueId': client_audio_files[client_id]['file_name']}

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    client_id = request.json['clientId']
    end_current_file(client_id)
    return {'status': 'success'}

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5555)
