from queue import Queue
import threading
import time
import uuid

import requests
from pydub import AudioSegment
import whisper
from audio_utils import is_silent, ends_with_major_pause
from log_utils import log_performance_decorator, log_performance_metric
import fasttext
import aiohttp
import asyncio
import os

TRANSCRIPTION_MODEL = whisper.load_model('base') # CUDA
# TRANSCRIPTION_MODEL = whisper.load_model('tiny.en') # CPU
LANGUAGE_DETECTION_MODEL = fasttext.load_model('lid.176.ftz')


# TODO: Automatically detect if GPU is available
use_fp16 = True

""" A Phrase is a subsection of a transcription. 
Contains the transcribed text and a path to the audio file

Attributes:
    text (str): The transcribed text
    full_audio_file_path_webm (str): The path to the full audio file (webm)
    phrase_audio_file_path_wav (str): The path to the phrase audio file (wav)
    start_time (float): The time in seconds relative to the start of the full audio file
    transcription_id (str): A unique id for the transcription
    index (int): The index of the phrase in the transcription
"""
class Phrase:
    def __init__(self, text, full_audio_file_path_webm, phrase_audio_file_path_wav, transcription_id, start_time=0, index=0):
        self.text = text
        self.full_audio_file_path_webm = full_audio_file_path_webm
        self.phrase_audio_file_path_wav = phrase_audio_file_path_wav
        self.start_time = start_time
        self.index = index
        self.transcription_id = transcription_id
        self.detected_language = None
        self.translation = None


    # Construct a phrase given the client_id. Generates file paths.
    # Used for the first phrase in a transcription.
    @classmethod
    def create_first_phrase(cls, client_id):
        text = ''
        index = 0
        transcription_id = str(uuid.uuid4())
        full_audio_file_path_webm = f'audio/audio_file_{client_id}_{transcription_id}.webm'
        phrase_audio_file_path_wav = f'audio/audio_file_{client_id}_{transcription_id}_{index}.wav'
        start_time = 0
        return cls(text, full_audio_file_path_webm, phrase_audio_file_path_wav, transcription_id, start_time, index)

    # Construct a phrase given the client_id, full audio file path, and start time.
    # Used when starting a new phrase from an existing audio file.
    @classmethod
    def create_subsequent_phrase(cls, client_id, full_audio_file_path_webm, start_time, index, transcription_id):
        text = ''
        index = index
        transcription_id = transcription_id
        full_audio_file_path_webm = full_audio_file_path_webm
        phrase_audio_file_path_wav = f'audio/audio_file_{client_id}_{transcription_id}_{index}.wav'
        start_time = start_time

        return cls(text, full_audio_file_path_webm, phrase_audio_file_path_wav, transcription_id, start_time, index)
            
    """Writes the given audio chunk to the phrase audio file and the full audio file."""
    def write_audio_chunk(self, audio_chunk):
        # Append the audio chunk to the full webm audio file
        with open(self.full_audio_file_path_webm, 'ab') as audio_file:
            audio_file.write(audio_chunk)

        # Take the full audio file and slice it to get the phrase audio file then save it as a .wav
        webm_audio = AudioSegment.from_file(self.full_audio_file_path_webm, format="webm")
        sliced_webm_audio = webm_audio[self.start_time * 1000:]
        wav_audio = sliced_webm_audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        wav_audio.export(self.phrase_audio_file_path_wav, format="wav")

    def get_duration(self):
        wav_audio = AudioSegment.from_file(self.phrase_audio_file_path_wav, format="wav")
        return wav_audio.duration_seconds

    @log_performance_decorator(log_performance_metric)
    def transcribe(self):
        self.text =  TRANSCRIPTION_MODEL.transcribe(self.phrase_audio_file_path_wav, fp16=use_fp16)["text"]

    """Detects the language of the phrase and translates it to English if necessary."""
    def detect_language_and_translate(self, translation_callback, start_translation_callback):
        self.detected_language = self.detect_language(self.text)
        print(f'Detected language: {self.detected_language}')
        if self.detected_language != 'en':
            start_translation_callback({'index': self.index})  # Emit event before starting translation
            self.translation = self.translate_text(self.text)  # Synchronous call
            print(f'Translation: {self.translation}')
            translation_callback({'index': self.index, 'translation': self.translation})  # Emit event after translation


    """Detects the language of the given text using the fasttext model."""
    def detect_language(self, text):
        predictions = LANGUAGE_DETECTION_MODEL.predict(text)
        return predictions[0][0].replace("__label__", "")

    """Translates the given text to English using the DeepL API."""
    def translate_text(self, text):
        # Convert this method to a synchronous version
        deepl_auth_key = os.getenv('DEEPL_AUTH_KEY')
        if not deepl_auth_key:
            raise ValueError("DeepL auth key not found in environment variables")
        
        # Use requests or another synchronous HTTP client
        response = requests.post('https://api-free.deepl.com/v2/translate', data={
            'auth_key': deepl_auth_key,
            'text': text,
            'target_lang': 'EN'
        })
        result = response.json()
        return result['translations'][0]['text']
    
class TranscriptionProcessor:
    def __init__(self, client_id, transcription_callback, start_translation_callback, translation_callback):
        self.client_id = client_id
        self.processing_audio_queue = False
        self.phrases = [Phrase.create_first_phrase(client_id)]
        self.transcription_callback = transcription_callback
        self.start_translation_callback = start_translation_callback
        self.translation_callback = translation_callback
        self.audio_queue_timeout = 60 # seconds
        self.audio_queue_time_without_audio = 0 # seconds
        self.audio_queue = TranscriptionAudioQueue()

    def current_phrase(self):
        return self.phrases[-1]

    def stop_transcription(self):
        self.stop_process_audio_queue()

        # clean up audio files
        # for phrase in self.phrases:
        #     try:
        #         os.remove(phrase.phrase_audio_file_path_wav)
        #         os.remove(phrase.full_audio_file_path_webm)
        #     except FileNotFoundError as e:
        #         print(e)
        #         print('No file not found for cleanup, skipping')
        #         continue

        return

    def queue_audio(self, audio_data):
        self.audio_queue.add_audio(audio_data)

    """Appends the audio_data (webm, 16khz) to the current phrase file,
    creating a new file if necessary (wav, 16khz).
    """
    def append_audio(self, audio_chunk):
        self.current_phrase().write_audio_chunk(audio_chunk)

        if not is_silent(self.current_phrase().phrase_audio_file_path_wav):
            print('Not silent, transcribing')
            self.current_phrase().transcribe()
            # TODO (performance): Keep track of full transcription on client as well so we don't have to always send the whole thing
            self.transcription_callback(self.full_transcription())
        else:
            print('Silent audio chunk detected, skipping transcription')

        # Decide whether we should start a new phrase
        # We won't even consider starting a new phrase if the current phrase is too short
        if self.current_phrase().get_duration() > 5:
            # Try to start a new phrase on a major pause by checking the current audio chunk
            # After a certain timeout, start a new phrase regardless of pause
            if ends_with_major_pause(self.current_phrase().phrase_audio_file_path_wav) or self.current_phrase().get_duration() > 20:    
                translation_thread = threading.Thread(target=self.current_phrase().detect_language_and_translate,
                                                    args=(self.translation_callback, self.start_translation_callback))
                translation_thread.start()
                self.start_new_phrase()

    def full_transcription(self):
        return {'transcriptions': [{'text': phrase.text} for phrase in self.phrases]}

    def start_new_phrase(self):
        # Start a new audio file for the next phrase
        current_phrase = self.current_phrase()

        self.phrases.append(Phrase.create_subsequent_phrase(
            self.client_id,
            current_phrase.full_audio_file_path_webm,
            current_phrase.start_time + current_phrase.get_duration(),
            current_phrase.index + 1,
            current_phrase.transcription_id))
    
    # Start processing the audio queue. Intended to be run continuously in a separate thread.
    def start_process_audio_queue(self):
        self.thread = threading.Thread(target=self.process_audio_queue)
        self.thread.start()

    def process_audio_queue(self):
        self.processing_audio_queue = True
        while self.processing_audio_queue and self.audio_queue_time_without_audio < self.audio_queue_timeout:
            if not self.audio_queue.is_empty():
                self.audio_queue_time_without_audio = 0
                audio_data = self.audio_queue.get_audio()
                self.append_audio(audio_data)
            else:
                self.audio_queue_time_without_audio += 0.1
                time.sleep(0.1)
        self.stop_process_audio_queue()

    def stop_process_audio_queue(self):
        self.processing_audio_queue = False
        self.audio_queue_time_without_audio = 0

class TranscriptionManager:
    def __init__(self):
        self.processors = {}
        self.lock = threading.Lock()

    def get_processor(self, client_id):
        with self.lock:
            return self.processors.get(client_id)

    def set_processor(self, client_id, processor):
        with self.lock:
            self.processors[client_id] = processor

    def remove_processor(self, client_id):
        with self.lock:
            if client_id in self.processors:
                del self.processors[client_id]

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