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


# Thread safe manager for transcription processors.
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


# Simple queue for audio data.
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


# Data class for Transcription: just holds data and a serialize method.
@dataclass
class Transcription:
    client_id: str
    unique_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    phrases: List[Phrase] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.phrases:
            # Initialize with a default phrase
            self.phrases.append(Phrase(transcription_id=self.unique_id, start_time=0, index=0))

    def serialize(self):
        return {
            'uniqueId': self.unique_id,
            'timestamp': self.timestamp,
            'phrases': [phrase.serialize() for phrase in self.phrases]
        }


# Data class for Phrase: only holds data with a serialize method.
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


# TranscriptionProcessor handles all responsibilities: file I/O, audio slicing, transcription, language detection,
# translation, and phrase management.
class TranscriptionProcessor:
    def __init__(self, client_id: str, transcription_callback: Callable, translation_callback: Callable):
        self.client_id = client_id
        self.transcription = Transcription(client_id)
        self.transcription_callback = transcription_callback
        self.translation_callback = translation_callback
        self.audio_queue_timeout = 60  # seconds
        self.audio_queue_time_without_audio = 0  # seconds
        self.audio_queue = TranscriptionAudioQueue()
        self.translation_pool = ThreadPoolExecutor(max_workers=2)  # Limit concurrent translations
        self.processing_audio_queue = False

    # Compute full audio file path.
    def get_full_audio_path(self) -> str:
        return Path('audio').joinpath(f'audio_file_{self.client_id}_{self.transcription.unique_id}.webm').as_posix()

    # Compute phrase audio file path.
    def get_phrase_audio_path(self, phrase: Phrase) -> str:
        return Path('audio').joinpath(f'audio_file_{phrase.transcription_id}_{phrase.index}.wav').as_posix()

    # Append incoming audio chunk to the full audio file.
    def append_audio_chunk_to_full_file(self, audio_chunk: bytes):
        full_path = self.get_full_audio_path()
        with open(full_path, 'ab') as f:
            f.write(audio_chunk)

    # Process current phrase audio by slicing from the full audio file and exporting to WAV.
    def process_phrase_audio(self, phrase: Phrase):
        full_path = self.get_full_audio_path()
        phrase_path = self.get_phrase_audio_path(phrase)
        try:
            webm_audio = AudioSegment.from_file(full_path, format="webm")
            # Slice audio starting from the phrase's start time.
            sliced_audio = webm_audio[phrase.start_time * 1000:]
            wav_audio = (sliced_audio
                         .set_frame_rate(16000)
                         .set_channels(1)
                         .set_sample_width(2))
            wav_audio.export(phrase_path, format="wav")
            # If the exported phrase audio is silent and hasn't started, update start time and remove file.
            if is_silent(phrase_path) and not phrase.phrase_audio_started:
                phrase.start_time += wav_audio.duration_seconds
                os.remove(phrase_path)
            else:
                phrase.phrase_audio_started = True
        except FileNotFoundError:
            pass

    # Return the duration of the phrase audio.
    def get_phrase_duration(self, phrase: Phrase) -> float:
        phrase_path = self.get_phrase_audio_path(phrase)
        if not os.path.exists(phrase_path):
            return 0
        audio = AudioSegment.from_file(phrase_path, format="wav")
        return audio.duration_seconds

    # Check if the phrase audio ends with a major pause.
    def phrase_ends_with_major_pause(self, phrase: Phrase) -> bool:
        phrase_path = self.get_phrase_audio_path(phrase)
        return ends_with_major_pause(phrase_path, pause_length_threshold=PAUSE_LENGTH_THRESHOLD)

    # Transcribe the phrase audio file.
    @log_performance_decorator(log_performance_metric)
    def transcribe_phrase(self, phrase: Phrase):
        phrase_path = self.get_phrase_audio_path(phrase)
        if os.path.exists(phrase_path) and phrase.phrase_audio_started:
            result = TRANSCRIPTION_MODEL.transcribe(phrase_path, fp16=use_fp16)
            phrase.transcription = result["text"]

    # Detect language and translate the phrase if needed.
    def detect_language_and_translate_phrase(self, phrase: Phrase):
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
            # Notify translation callback with the updated phrase.
            self.translation_callback(phrase.serialize())

    # Main method to process an incoming audio chunk.
    def process_audio_chunk(self, audio_chunk: bytes):
        # 1. Append audio chunk to the full audio file.
        self.append_audio_chunk_to_full_file(audio_chunk)
        
        # 2. Get the current phrase (the last phrase in the transcription).
        current_phrase = self.transcription.phrases[-1]
        
        # 3. Process the phrase audio: slice the full audio and export the current phrase to WAV.
        self.process_phrase_audio(current_phrase)
        
        # 4. If the phrase audio has started, transcribe and update the callback.
        if current_phrase.phrase_audio_started:
            self.transcribe_phrase(current_phrase)
            if current_phrase.transcription.strip():
                self.transcription_callback(current_phrase.serialize())
            
            # 5. Check if the phrase is complete based on duration and pauses.
            duration = self.get_phrase_duration(current_phrase)
            if duration >= MIN_PHRASE_LENGTH_SECONDS and (
                self.phrase_ends_with_major_pause(current_phrase) or duration >= MAX_PHRASE_LENGTH_SECONDS
            ):
                # If there is transcription text, schedule language detection/translation.
                if current_phrase.transcription.strip():
                    self.translation_pool.submit(self.detect_language_and_translate_phrase, current_phrase)
                # 6. Start a new phrase with updated start time and index.
                new_phrase = Phrase(
                    transcription_id=self.transcription.unique_id,
                    start_time=current_phrase.start_time + duration,
                    index=len(self.transcription.phrases)
                )
                self.transcription.phrases.append(new_phrase)
                self.transcription_callback(new_phrase.serialize())

    # Continuously process audio chunks from the queue until a timeout.
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
        self.stop_process_audio_queue()

    # Remove all audio files related to this transcription.
    def cleanup_audio_files(self):
        full_path = self.get_full_audio_path()
        if os.path.exists(full_path):
            os.remove(full_path)
        for phrase in self.transcription.phrases:
            phrase_path = self.get_phrase_audio_path(phrase)
            if os.path.exists(phrase_path):
                os.remove(phrase_path)

    # Stop processing the audio queue and clean up resources.
    def stop_process_audio_queue(self):
        try:
            self.processing_audio_queue = False
            self.audio_queue_time_without_audio = 0
            time.sleep(1)  # Allow time for file release.
            self.cleanup_audio_files()
            self.translation_pool.shutdown(wait=True)
            if hasattr(self, 'thread') and self.thread.is_alive() and self.thread != threading.current_thread():
                self.thread.join(timeout=5)
                if self.thread.is_alive():
                    print(f"Warning: Audio processing thread for client {self.client_id} did not terminate within timeout")
        finally:
            if not self.translation_pool._shutdown:
                self.translation_pool.shutdown(wait=False)

    # Start processing the audio queue in a separate thread.
    def start_process_audio_queue(self):
        self.thread = threading.Thread(target=self.process_audio_queue)
        self.thread.start()

    # Add an audio chunk to the processing queue.
    def queue_audio(self, audio_chunk: bytes):
        self.audio_queue.add_audio(audio_chunk)
