import io
import os
from queue import Queue
import time
import uuid
from pydub import AudioSegment
import whisper
import webrtcvad
import wave

model = whisper.load_model('base.en')
cheap_model = whisper.load_model('tiny.en')

# TODO: Automatically detect if GPU is available
use_fp16 = True

""" A Phrase is a subsection of a transcription. 
Contains the transcribed text and a path to the audio file
"""
class Phrase:
    def __init__(self, text, audio_file_path_wav, audio_file_path_webm):
        self.text = text
        self.audio_file_path_wav = audio_file_path_wav
        self.audio_file_path_webm = audio_file_path_webm

    # Construct a phrase given the client_id. Generates file paths.
    def __init__(self, client_id):
        self.text = ''
        unique_id = str(uuid.uuid4())
        self.audio_file_path_wav = f'audio/audio_file_{client_id}_{unique_id}.wav'
        self.audio_file_path_webm = f'audio/audio_file_{client_id}_{unique_id}.webm'

    def write_audio_chunk(self, audio_chunk):
        with open(self.audio_file_path_webm, 'ab') as audio_file:
            audio_file.write(audio_chunk)

        # Convert webm to wav for audio processing (keeping webm file around)
        webm_audio = AudioSegment.from_file(self.audio_file_path_webm, format="webm")
        wav_audio = webm_audio.set_frame_rate(16000).set_channels(1)
        wav_audio.export(self.audio_file_path_wav, format="wav")

    def get_duration(self):
        wav_audio = AudioSegment.from_file(self.audio_file_path_wav, format="wav")
        return wav_audio.duration_seconds

    def transcribe(self):
        self.text =  model.transcribe(self.audio_file_path_wav, fp16=use_fp16)["text"]


class TranscriptionManager:
    def __init__(self, client_id, transcription_callback):
        self.client_id = client_id
        self.processing_audio_queue = False
        self.phrases = [Phrase(client_id)]
        self.transcription_callback = transcription_callback

    def current_phrase(self):
        return self.phrases[-1]

    def stop_transcription(self):
        # TODO: Clean up
        return

    """Appends the audio_data (webm, 16khz) to the current phrase file,
    creating a new file if necessary (wav, 16khz).
    """
    def append_audio(self, audio_chunk):
        self.current_phrase().write_audio_chunk(audio_chunk)
        self.current_phrase().transcribe()

        # TODO (performance): Keep track of full transcription on client as well so we don't have to always send the whole thing
        self.transcription_callback(self.full_transcription())

        # Decide whether we should start a new phrase
        # We won't even consider starting a new phrase if the current phrase is less than 30 seconds
        if self.current_phrase().get_duration() > 30:
            # Try to start a new phrase on a major pause by checking the current audio chunk
            if self.is_major_pause(audio_chunk):
                self.start_new_phrase()
            # After a certain timeout, start a new phrase regardless of pause
            elif self.current_phrase().get_duration() > 120:
                self.start_new_phrase()

    def full_transcription(self):
        transcription = ''
        for phrase in self.phrases:
            transcription += phrase.text + ' '
        return transcription

    def start_new_phrase(self):
        print('Starting new phrase')
        # Start a new audio file for the next phrase
        self.phrases.append(Phrase(self.client_id))

    # Returns true if audio_chunk contains no speech
    def is_major_pause(self, audio_chunk):
        transcription = cheap_model.transcribe(audio_chunk, fp16=use_fp16)["text"]
        return transcription == ''

    
    # Start processing the audio queue. Intended to be run continuously in a separate thread.
    def start_process_audio_queue(self, audio_queue):
        self.processing_audio_queue = True
        while self.processing_audio_queue:
            if not audio_queue.is_empty():
                audio_data = audio_queue.get_audio()
                self.append_audio(audio_data)
                print('Processed audio')
            else:
                time.sleep(0.1)

    def stop_process_audio_queue(self):
        self.processing_audio_queue = False


class TranscriptionAudioQueue:
    def __init__(self):
        self.queue = Queue()

    def add_audio(self, audio_data):
        self.queue.put(audio_data)

    def get_audio(self):
        return self.queue.get()

    def is_empty(self):
        return self.queue.empty()

    def clear(self):
        self.queue = Queue()