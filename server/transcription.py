from queue import Queue
import threading
import time
import uuid

import requests
from pydub import AudioSegment
import whisper
from audio_utils import ends_with_major_pause, is_silent
from log_utils import log_performance_decorator, log_performance_metric
import fasttext
import os
from tinydb import TinyDB, Query

db = TinyDB('db.json')

TRANSCRIPTION_MODEL = whisper.load_model('base') # CUDA
# TRANSCRIPTION_MODEL = whisper.load_model('tiny.en') # CPU
LANGUAGE_DETECTION_MODEL = fasttext.load_model('lid.176.ftz')

MIN_PHRASE_LENGTH_SECONDS = 3
MAX_PHRASE_LENGTH_SECONDS = 20
PAUSE_LENGTH_THRESHOLD = 0.7


# TODO: Automatically detect if GPU is available
use_fp16 = True

"""Represents a phrase in a transcription.
Attributes:
    transcription_id (str): The unique ID of the transcription.
    transcription (str): The transcription of the phrase.
    phrase_audio_file_path_wav (str): The path to the .wav file of the phrase audio.
    start_time (float): The start time of the phrase in the full audio file.
    index (int): The index of the phrase in the transcription.
    detected_language (str): The language detected in the phrase.
    translation (str): The translation of the phrase to English.
    phrase_audio_started (bool): True if the phrase audio file has started being written.
"""
class Phrase:
    def __init__(self, transcription_id, phrase_audio_file_path_wav, start_time=0, index=0):
        self.transcription_id = transcription_id
        self.transcription = ''
        self.phrase_audio_file_path_wav = phrase_audio_file_path_wav
        self.start_time = start_time
        self.index = index
        self.detected_language = None
        self.translation = None
        self.phrase_audio_started = False
        self.timestamp = time.time()

    """Writes the phrase audio file to disk as a .wav file by slicing the full audio file from the start time."""
    def write_phrase_audio_file(self, full_audio_file_path_webm):
        webm_audio = AudioSegment.from_file(full_audio_file_path_webm, format="webm")
        sliced_webm_audio = webm_audio[self.start_time * 1000:]
        wav_audio = sliced_webm_audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        wav_audio.export(self.phrase_audio_file_path_wav, format="wav")
        if is_silent(self.phrase_audio_file_path_wav) and not self.phrase_audio_started:
            self.start_time += wav_audio.duration_seconds
            os.remove(self.phrase_audio_file_path_wav)
        else:
            self.phrase_audio_started = True

    """Returns the duration of the phrase audio file in seconds."""
    def get_duration(self):
        if not os.path.exists(self.phrase_audio_file_path_wav):
            return 0
        wav_audio = AudioSegment.from_file(self.phrase_audio_file_path_wav, format="wav")
        return wav_audio.duration_seconds

    """Returns True if the phrase audio file ends with a major pause."""
    def ends_with_major_pause(self):
        return ends_with_major_pause(self.phrase_audio_file_path_wav, pause_length_threshold=PAUSE_LENGTH_THRESHOLD)

    """Transcribes the phrase using the whisper model."""
    @log_performance_decorator(log_performance_metric)
    def transcribe(self):
        self.transcription =  TRANSCRIPTION_MODEL.transcribe(self.phrase_audio_file_path_wav, fp16=use_fp16)["text"]

    """Detects the language of the phrase and translates it to English if necessary."""
    def detect_language_and_translate(self, translation_callback):
        self.detected_language = self.detect_language(self.transcription)
        if self.detected_language != 'en':
            self.translation = self.translate_text(self.transcription)
            translation_callback(self.serialize())

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

    """Serializes the phrase to a dictionary."""
    def serialize(self):
        return {
            'transcription_id': self.transcription_id,
            'transcription': self.transcription,
            'start_time': self.start_time,
            'index': self.index,
            'detected_language': self.detected_language,
            'translation': self.translation,
            'timestamp': self.timestamp,
            'phrase_audio_file_path_wav': self.phrase_audio_file_path_wav
        }

    @classmethod
    def deserialize(cls, phrase_dict):
        """
        Creates a Phrase instance from a serialized dictionary.
        """
        # Create a new Phrase instance with basic attributes
        phrase = cls(
            transcription_id=phrase_dict['transcription_id'],
            phrase_audio_file_path_wav=phrase_dict['phrase_audio_file_path_wav'],
            start_time=phrase_dict.get('start_time', 0),
            index=phrase_dict.get('index', 0)
        )
        # Set additional attributes
        phrase.transcription = phrase_dict.get('transcription', '')
        phrase.detected_language = phrase_dict.get('detected_language', None)
        phrase.translation = phrase_dict.get('translation', None)
        phrase.phrase_audio_started = phrase_dict.get('phrase_audio_started', False)
        
        return phrase

"""Represents a transcription.
Attributes:
    unique_id (str): The unique ID of the transcription.
    client_id (str): The ID of the client that initiated the transcription.
    phrases (list): A list of phrases in the transcription.
    full_audio_file_path_webm (str): The path to the full audio file in webm format.
"""
class Transcription:
    def __init__(self, client_id):
        self.unique_id = str(uuid.uuid4())
        self.client_id = client_id
        self.phrases = []
        self.phrases.append(self.create_phrase())
        self.full_audio_file_path_webm = f'audio/audio_file_{client_id}_{self.unique_id}.webm'
        self.timestamp = time.time()

    """Creates a new phrase with the given start time."""
    def create_phrase(self, start_time=0):
        index = len(self.phrases)
        phrase_audio_file_path_wav = f'audio/audio_file_{self.client_id}_{self.unique_id}_{index}.wav'
        return Phrase(self.unique_id, phrase_audio_file_path_wav, start_time, index)

    """Adds a new phrase to the transcription."""
    def add_phrase(self):
        self.phrases.append(self.create_phrase(start_time=self.last_phrase().start_time + self.last_phrase().get_duration()))

    """Returns the last phrase in the transcription."""
    def last_phrase(self):
        return self.phrases[-1]

    """Writes the given audio chunk to the full audio file."""
    def write_audio_chunk(self, audio_chunk):
        # Append the audio chunk to the full webm audio file
        with open(self.full_audio_file_path_webm, 'ab') as audio_file:
            audio_file.write(audio_chunk)

    """Appends the given audio chunk to the full audio file and transcribes the last phrase."""
    def append_audio_and_transcribe(self, audio_chunk):
        self.write_audio_chunk(audio_chunk)
        self.last_phrase().write_phrase_audio_file(self.full_audio_file_path_webm)

        if self.last_phrase().phrase_audio_started:
            self.last_phrase().transcribe()

    """Returns True if the last phrase is complete. A phrase is complete if it is at least 3 seconds long and ends with a major pause.
    or if it is at least 20 seconds long."""
    def phrase_complete(self):
        return self.last_phrase().get_duration() >= MIN_PHRASE_LENGTH_SECONDS and \
            (self.last_phrase().ends_with_major_pause() or self.last_phrase().get_duration() >= MAX_PHRASE_LENGTH_SECONDS)

    """Returns True if the last phrase ends with a major pause."""
    def ends_with_major_pause(self):
        return self.last_phrase().ends_with_major_pause()

    """Serializes the transcription to a dictionary."""
    def serialize(self):
        return {
            'unique_id': self.unique_id,
            'client_id': self.client_id,
            'timestamp': self.timestamp,
            'full_audio_file_path_webm': self.full_audio_file_path_webm,
            'phrases': [phrase.serialize() for phrase in self.phrases]
        }

    @classmethod
    def deserialize(cls, transcription_dict):
        """
        Creates a Transcription instance from a serialized dictionary.
        """
        client_id = transcription_dict['client_id']
        
        transcription = cls(client_id)
        transcription.unique_id = transcription_dict['unique_id']
        transcription.client_id = client_id
        transcription.full_audio_file_path_webm = transcription_dict['full_audio_file_path_webm']
        transcription.timestamp = transcription_dict['timestamp']
        
        # Clear the automatically added phrase and rebuild phrases from the serialized data
        transcription.phrases.clear()
        for phrase_data in transcription_dict['phrases']:
            phrase = Phrase.deserialize(phrase_data)
            transcription.phrases.append(phrase)
        
        return transcription

    """Saves the transcription to the database. If the transcription already exists, it is updated. Otherwise, it is inserted."""
    def save_to_db(self):
        TranscriptionDB = Query()
        existing_transcription = db.search(TranscriptionDB.unique_id == self.unique_id)
        if existing_transcription:
            db.update({'phrases': [phrase.serialize() for phrase in self.phrases]}, TranscriptionDB.unique_id == self.unique_id)
        else:
            db.insert(self.serialize())
    
"""Represents a transcription processor. Responsible for asynchronously processing audio chunks and transcribing them.
Attributes:
    client_id (str): The ID of the client that initiated the transcription.
    transcription (Transcription): The transcription being processed.
    processing_audio_queue (bool): True if the audio queue is being processed.
    transcription_callback (function): The callback function to call when a transcription is updated.
    translation_callback (function): The callback function to call when a phrase is translated.
    audio_queue_timeout (int): The maximum time to process the audio queue in seconds.
    audio_queue_time_without_audio (int): The time without audio in the audio queue in seconds.
    audio_queue (TranscriptionAudioQueue): The audio queue.
"""
class TranscriptionProcessor:
    def __init__(self, client_id, transcription_callback, translation_callback):
        self.client_id = client_id
        self.transcription = Transcription(client_id)
        self.processing_audio_queue = False
        self.transcription_callback = transcription_callback
        self.translation_callback = translation_callback
        self.audio_queue_timeout = 60 # seconds
        self.audio_queue_time_without_audio = 0 # seconds
        self.audio_queue = TranscriptionAudioQueue()

    """Starts processing the audio queue."""
    def start_process_audio_queue(self):
        self.thread = threading.Thread(target=self.process_audio_queue)
        self.thread.start()

    """Processes the audio queue."""
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

    """Stops processing the audio queue."""
    def stop_process_audio_queue(self):
        self.transcription.save_to_db()
        self.processing_audio_queue = False
        self.audio_queue_time_without_audio = 0

    """Queues the given audio data."""
    def queue_audio(self, audio_data):
        self.audio_queue.add_audio(audio_data)

    """Appends the given audio chunk to the transcription and performs transcription and translation as needed."""
    def append_audio(self, audio_chunk):
        self.transcription.append_audio_and_transcribe(audio_chunk)
        self.transcription_callback(self.transcription.last_phrase().serialize())

        if self.transcription.phrase_complete():
            self.transcription.save_to_db()
            translation_thread = threading.Thread(target=self.transcription.last_phrase().detect_language_and_translate, args=(self.translation_callback,))
            translation_thread.start()
            self.transcription.add_phrase()
            self.transcription_callback(self.transcription.last_phrase().serialize())

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

    def get_transcriptions_dict(self, client_id):
        results = db.search(Query().client_id == client_id)
        return results


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