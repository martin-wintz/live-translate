from __future__ import annotations
from queue import Queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable
import contextlib
import warnings
import requests
from pydub import AudioSegment
import whisper
from audio_utils import ends_with_major_pause, is_silent
from log_utils import log_performance_decorator, log_performance_metric
import fasttext
import os
from concurrent.futures import ThreadPoolExecutor
import torch

warnings.filterwarnings('ignore', category=FutureWarning, module='whisper')

print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"Using GPU: {torch.cuda.get_device_name()}")
    TRANSCRIPTION_MODEL = whisper.load_model('base').cuda() # CUDA
    use_fp16 = True
else:
    print("Using CPU with tiny.en model. Translation feature won't work.")
    TRANSCRIPTION_MODEL = whisper.load_model('tiny.en') # CPU
    use_fp16 = False

LANGUAGE_DETECTION_MODEL = fasttext.load_model('lid.176.ftz')

MIN_PHRASE_LENGTH_SECONDS = 3
MAX_PHRASE_LENGTH_SECONDS = 20
PAUSE_LENGTH_THRESHOLD = 0.7



"""Thread safe manager for transcription processors."""
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

"""A simple queue for audio data."""
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
        self.translation_pool = ThreadPoolExecutor(max_workers=2)  # Limit concurrent translations

    """Start processing the audio queue in a separate thread."""
    def start_process_audio_queue(self):
        self.thread = threading.Thread(target=self.process_audio_queue)
        self.thread.start()

    """Processes audio chunks from the queue until the queue is empty for the timeout period."""
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
        try:
            self.processing_audio_queue = False
            self.audio_queue_time_without_audio = 0
            time.sleep(1) # Wait for files to release
            self.transcription.cleanup_audio_files()

            # Clean up threads
            self.translation_pool.shutdown(wait=True)
            
            if (hasattr(self, 'thread') and 
                self.thread.is_alive() and 
                self.thread != threading.current_thread()):
                self.thread.join(timeout=5)
                if self.thread.is_alive():
                    print(f"Warning: Audio processing thread for client {self.client_id} did not terminate within timeout")
        finally:
            if not self.translation_pool._shutdown:
                self.translation_pool.shutdown(wait=False)

    def queue_audio(self, audio_data):
        self.audio_queue.add_audio(audio_data)

    """Appends the given audio chunk to the transcription and performs transcription and translation as needed."""
    def append_audio(self, audio_chunk):
        self.transcription.append_audio_and_transcribe(audio_chunk)
        if self.transcription.last_phrase().transcription != '':
            self.transcription_callback(self.transcription.last_phrase().serialize())

        # When the phrase is complete, attempt to translate it and start a new phrase
        if self.transcription.phrase_complete():
            self.translation_pool.submit(
                self.transcription.last_phrase().detect_language_and_translate, 
                self.translation_callback
            )
            self.transcription.add_phrase()
            self.transcription_callback(self.transcription.last_phrase().serialize())

"""Represents a transcription.
Attributes:
    unique_id (str): The unique ID of the transcription.
    client_id (str): The ID of the client that initiated the transcription.
    phrases (list): A list of phrases in the transcription.
    full_audio_file_path_webm (str): The path to the full audio file in webm format.
"""
@dataclass
class Transcription:
    client_id: str
    unique_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    phrases: List[Phrase] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.phrases:
            self.phrases.append(self.create_phrase())

    @property
    def audio_path(self) -> Path:
        return Path('audio') / f'audio_file_{self.client_id}_{self.unique_id}.webm'

    """Appends the given audio chunk to the full audio file and transcribes the last phrase."""
    def append_audio_and_transcribe(self, audio_chunk: bytes) -> None:
        self.write_audio_chunk(audio_chunk)
        self.last_phrase().write_phrase_audio_file(self.audio_path)

        # Don't bother transcribing silence
        if self.last_phrase().phrase_audio_started:
            self.last_phrase().transcribe()

    """Returns True if the last phrase is complete. A phrase is complete if it is at least 3 seconds long and ends with a major pause.
    or if it is at least 20 seconds long."""
    def phrase_complete(self):
        return self.last_phrase().get_duration() >= MIN_PHRASE_LENGTH_SECONDS and \
            (self.last_phrase().ends_with_major_pause() or self.last_phrase().get_duration() >= MAX_PHRASE_LENGTH_SECONDS)

    def create_phrase(self, start_time=0):
        index = len(self.phrases)
        return Phrase(self.unique_id, start_time, index)

    def add_phrase(self):
        self.phrases.append(self.create_phrase(start_time=self.last_phrase().start_time + self.last_phrase().get_duration()))

    def last_phrase(self):
        return self.phrases[-1]

    def write_audio_chunk(self, audio_chunk: bytes) -> None:
        with open(self.audio_path, 'ab') as audio_file:
            audio_file.write(audio_chunk)

    def ends_with_major_pause(self):
        return self.last_phrase().ends_with_major_pause()

    def cleanup_audio_files(self):
        with contextlib.suppress(FileNotFoundError):
            self.audio_path.unlink()

        for phrase in self.phrases:
            phrase.cleanup_audio_file()

    def serialize(self):
        return {
            'uniqueId': self.unique_id,
            'timestamp': self.timestamp,
            'phrases': [phrase.serialize() for phrase in self.phrases]
        }
    

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
@dataclass
class Phrase:
    transcription_id: str
    start_time: float = 0
    index: int = 0
    transcription: str = ''
    detected_language: Optional[str] = None
    translation: Optional[str] = None
    phrase_audio_started: bool = False
    timestamp: float = field(default_factory=time.time)

    @property
    def audio_path(self) -> Path:
        # return Path('audio') / f'audio_file_{self.transcription_id}_{self.index}.wav'
         return Path('audio').joinpath(f'audio_file_{self.transcription_id}_{self.index}.wav').as_posix()

    def write_phrase_audio_file(self, full_audio_path: Path) -> None:
        with contextlib.suppress(FileNotFoundError):
            webm_audio = AudioSegment.from_file(full_audio_path, format="webm")
            sliced_audio = webm_audio[self.start_time * 1000:]
            wav_audio = (sliced_audio
                        .set_frame_rate(16000)
                        .set_channels(1)
                        .set_sample_width(2))
            
            wav_audio.export(self.audio_path, format="wav")
            
            # Skip initial silence
            if is_silent(self.audio_path) and not self.phrase_audio_started:
                self.start_time += wav_audio.duration_seconds
                Path(self.audio_path).unlink()
            else:
                self.phrase_audio_started = True

    def get_duration(self):
        if not os.path.exists(self.audio_path):
            return 0
        wav_audio = AudioSegment.from_file(self.audio_path, format="wav")
        return wav_audio.duration_seconds

    def ends_with_major_pause(self):
        return ends_with_major_pause(self.audio_path, pause_length_threshold=PAUSE_LENGTH_THRESHOLD)

    @log_performance_decorator(log_performance_metric)
    def transcribe(self) -> None:
        self.transcription = TRANSCRIPTION_MODEL.transcribe(
            str(self.audio_path), 
            fp16=use_fp16
        )["text"]

    def detect_language_and_translate(self, translation_callback):
        self.detected_language = self.detect_language(self.transcription)
        print(f"Detected language: {self.detected_language}", flush=True)
        if self.detected_language != 'en':
            self.translation = self.translate_text(self.transcription)
            translation_callback(self.serialize())

    def detect_language(self, text):
        predictions = LANGUAGE_DETECTION_MODEL.predict(text)
        return predictions[0][0].replace("__label__", "")

    def translate_text(self, text):
        deepl_auth_key = os.getenv('DEEPL_AUTH_KEY')
        if not deepl_auth_key:
            raise ValueError("DeepL auth key not found in environment variables")
        
        response = requests.post('https://api-free.deepl.com/v2/translate', data={
            'auth_key': deepl_auth_key,
            'text': text,
            'target_lang': 'EN'
        })
        result = response.json()
        return result['translations'][0]['text']

    def cleanup_audio_file(self):
        with contextlib.suppress(FileNotFoundError):
            Path(self.audio_path).unlink()


    def serialize(self):
        return {
            'transcriptionId': self.transcription_id,
            'transcription': self.transcription,
            'startTime': self.start_time,
            'index': self.index,
            'detectedLanguage': self.detected_language,
            'translation': self.translation,
            'timestamp': self.timestamp
        }