from __future__ import annotations
from queue import Queue
import threading
import time
import uuid
from dataclasses import dataclass, field
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
    TRANSCRIPTION_MODEL = whisper.load_model('base').cuda()  # CUDA
    use_fp16 = True
else:
    print("Using CPU with tiny.en model. Translation feature won't work.")
    TRANSCRIPTION_MODEL = whisper.load_model('tiny.en')  # CPU
    use_fp16 = False

LANGUAGE_DETECTION_MODEL = fasttext.load_model('lid.176.ftz')

MIN_PHRASE_LENGTH_SECONDS = 3
MAX_PHRASE_LENGTH_SECONDS = 20
PAUSE_LENGTH_THRESHOLD = 0.7

@dataclass
class Transcription:
    client_id: str
    unique_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    phrases: List[Phrase] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.phrases:
            # Start with a default phrase.
            self.phrases.append(Phrase(transcription_id=self.unique_id, start_time=0, index=0))

    def serialize(self):
        return {
            'uniqueId': self.unique_id,
            'timestamp': self.timestamp,
            'phrases': [phrase.serialize() for phrase in self.phrases]
        }


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


"""Handles everything related to audio files for a specific transcription."""
class AudioFileHandler:
    def __init__(self, client_id: str, transcription_id: str):
        self.client_id = client_id
        self.transcription_id = transcription_id
        self.full_audio_path = Path('audio').joinpath(f'audio_file_{client_id}_{transcription_id}.webm').as_posix()

    def append_audio_chunk(self, audio_chunk: bytes):
        with open(self.full_audio_path, 'ab') as f:
            f.write(audio_chunk)

    def get_phrase_audio_path(self, phrase: Phrase) -> str:
        return Path('audio').joinpath(f'audio_file_{phrase.transcription_id}_{phrase.index}.wav').as_posix()

    # Because whisper works with wav files, we need to slice a piece of our webm file to transcribe the phrase.
    # Maybe there's a better way to do this that doesn't require writing an intermediate file to disk,
    # but in any case, this affects performance very little relative to the actual transcription.
    def process_phrase_audio(self, phrase: Phrase):
        phrase_path = self.get_phrase_audio_path(phrase)
        try:
            webm_audio = AudioSegment.from_file(self.full_audio_path, format="webm")
            # Slice the audio starting from the phrase's start time.
            sliced_audio = webm_audio[phrase.start_time * 1000:]
            wav_audio = (sliced_audio
                         .set_frame_rate(16000)
                         .set_channels(1)
                         .set_sample_width(2))
            wav_audio.export(phrase_path, format="wav")
            # If audio is silent (and we haven't yet started the phrase), skip the silence.
            if is_silent(phrase_path) and not phrase.phrase_audio_started:
                phrase.start_time += wav_audio.duration_seconds
                os.remove(phrase_path)
            else:
                phrase.phrase_audio_started = True
        except FileNotFoundError:
            print(f"File not found when processing phrase audio: {self.full_audio_path}")
            pass

    def get_phrase_duration(self, phrase: Phrase) -> float:
        phrase_path = self.get_phrase_audio_path(phrase)
        if not os.path.exists(phrase_path):
            return 0
        audio = AudioSegment.from_file(phrase_path, format="wav")
        return audio.duration_seconds

    def cleanup_files(self, transcription: Transcription):
        if os.path.exists(self.full_audio_path):
            os.remove(self.full_audio_path)
        for phrase in transcription.phrases:
            phrase_path = self.get_phrase_audio_path(phrase)
            if os.path.exists(phrase_path):
                os.remove(phrase_path)


"""Handles the transcription of a phrase. Encapsulates the whisper model."""
class TranscriptionService:
    @log_performance_decorator(log_performance_metric)
    def transcribe(self, phrase: Phrase, phrase_audio_path: str):
        if os.path.exists(phrase_audio_path) and phrase.phrase_audio_started:
            result = TRANSCRIPTION_MODEL.transcribe(phrase_audio_path, fp16=use_fp16)
            phrase.transcription = result["text"]


"""Handles the detection and translation of a phrase. Encapsulates the fasttext model and deepl api."""
class TranslationService:
    def detect_and_translate(self, phrase: Phrase):
        predictions = LANGUAGE_DETECTION_MODEL.predict(phrase.transcription)
        detected_language = predictions[0][0].replace("__label__", "")
        phrase.detected_language = detected_language
        print(f"Detected language: {detected_language}", flush=True)
        if detected_language != 'en':
            deepl_auth_key = os.getenv('DEEPL_AUTH_KEY')
            if not deepl_auth_key:
                raise ValueError("DeepL auth key not found in environment variables")
            response = requests.post('https://api-free.deepl.com/v2/translate', data={
                'auth_key': deepl_auth_key,
                'text': phrase.transcription,
                'target_lang': 'EN'
            })
            result = response.json()
            phrase.translation = result['translations'][0]['text']


"""Handles the audio queue for a specific transcription."""
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

""" Thread safe manager for transcription processors. """
class TranscriptionManager:
    def __init__(self):
        self.controllers = {}
        self.lock = threading.Lock()

    def get_controller(self, client_id):
        with self.lock:
            return self.controllers.get(client_id)

    def set_controller(self, client_id, controller):
        with self.lock:
            self.controllers[client_id] = controller

    def remove_controller(self, client_id):
        with self.lock:
            if client_id in self.controllers:
                del self.controllers[client_id]


"""Main class that orchestrates the transcription and translation of a transcription in a separate thread."""
class TranscriptionController:
    def __init__(self, client_id: str, transcription_callback: Callable, translation_callback: Callable):
        self.client_id = client_id
        self.transcription = Transcription(client_id)
        self.transcription_callback = transcription_callback
        self.translation_callback = translation_callback
        self.audio_queue_timeout = 60  # seconds
        self.audio_queue_time_without_audio = 0
        self.translation_pool = ThreadPoolExecutor(max_workers=2)
        self.processing_audio_queue = False

        # Services
        self.audio_queue = TranscriptionAudioQueue()
        self.audio_handler = AudioFileHandler(client_id, self.transcription.unique_id)
        self.transcription_service = TranscriptionService()
        self.translation_service = TranslationService()

    def start_processing(self):
        self.thread = threading.Thread(target=self.process_audio_queue)
        self.thread.start()

    def process_audio_queue(self):
        self.processing_audio_queue = True
        while self.processing_audio_queue and self.audio_queue_time_without_audio < self.audio_queue_timeout:
            if not self.audio_queue.is_empty():
                self.audio_queue_time_without_audio = 0
                audio_chunk = self.audio_queue.get_audio()
                self.process_audio_chunk(audio_chunk)
            else:
                self.audio_queue_time_without_audio += 0.1
                time.sleep(0.1)
        self.stop_processing()

    def queue_audio(self, audio_chunk: bytes):
        self.audio_queue.add_audio(audio_chunk)

    def stop_processing(self):
        try:
            self.processing_audio_queue = False
            self.audio_queue_time_without_audio = 0
            time.sleep(1)  # Allow time for file release.
            self.audio_handler.cleanup_files(self.transcription)
            self.translation_pool.shutdown(wait=True)
        finally:
            if not self.translation_pool._shutdown:
                self.translation_pool.shutdown(wait=False)

    """Main audio processing logic."""
    def process_audio_chunk(self, audio_chunk: bytes):
        self.audio_handler.append_audio_chunk(audio_chunk)
        current_phrase = self.transcription.phrases[-1]
        self.audio_handler.process_phrase_audio(current_phrase)
        phrase_audio_path = self.audio_handler.get_phrase_audio_path(current_phrase)

        # If phrase audio has started, transcribe and callback.
        if current_phrase.phrase_audio_started:
            self.transcription_service.transcribe(current_phrase, phrase_audio_path)
            if current_phrase.transcription.strip():
                self.transcription_callback(current_phrase.serialize())

            # If the phrase is complete, translate and callback.
            duration = self.audio_handler.get_phrase_duration(current_phrase)
            if self.is_phrase_complete(current_phrase, phrase_audio_path, duration):
                if current_phrase.transcription.strip():
                    # Schedule translation in a separate thread.
                    self.translation_pool.submit(lambda: self._translate_and_callback(current_phrase))
                
                # Start a new phrase.
                new_phrase = self.create_new_phrase(current_phrase, duration)
                self.transcription.phrases.append(new_phrase)
                self.transcription_callback(new_phrase.serialize())

    def _translate_and_callback(self, phrase: Phrase):
        self.translation_service.detect_and_translate(phrase)
        self.translation_callback(phrase.serialize())

    def is_phrase_complete(self, phrase: Phrase, phrase_audio_path: str, duration: float) -> bool:
        return duration >= MIN_PHRASE_LENGTH_SECONDS and (
            ends_with_major_pause(phrase_audio_path, pause_length_threshold=PAUSE_LENGTH_THRESHOLD) or duration >= MAX_PHRASE_LENGTH_SECONDS
        )

    def create_new_phrase(self, current_phrase: Phrase, duration: float) -> Phrase:
        new_start_time = current_phrase.start_time + duration
        new_index = len(self.transcription.phrases)
        return Phrase(transcription_id=self.transcription.unique_id, start_time=new_start_time, index=new_index)


