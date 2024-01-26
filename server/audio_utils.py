import wave
import webrtcvad


"""Returns True if the audio file is silent.
Parameters:
    wav_file_path (str): The path to the wav file to check.
    speech_frame_threshold (int): The number of speech frames required to consider the audio file not silent. Vad is very sensitive even on the highest aggressiveness level, so false positive frames are common. Defaults to 10.
"""
def is_silent(wav_file_path, speech_frame_threshold=10):
    vad = webrtcvad.Vad(3)  # Use a higher aggressiveness level
    frame_duration = 30  # Duration of a frame in milliseconds
    sample_rate = 16000  # Assumed sample rate of the audio
    n_frames = int(sample_rate * frame_duration / 1000)
    num_speech_frames = 0

    with wave.open(wav_file_path, 'rb') as f:
        frames = list(wave_read_frames(f, n_frames))

    for frame in frames:
        try:
            if vad.is_speech(frame, sample_rate):
                num_speech_frames += 1
                if num_speech_frames >= speech_frame_threshold:
                    return False  # Not silent, as we have enough speech frames
        except Exception as e:
            print(f'VadError: Skipping frame {e}')

    return True 

"""Returns True if the last pause_length_threshold seconds of the audio file are silent.

Parameters:
    wav_file_path (str): The path to the wav file to check.
    speech_frame_threshold (int): The number of speech frames required to consider the audio file not silent. Vad is very sensitive even on the highest aggressiveness level, so false positive frames are common. Defaults to 5.
    pause_length_threshold (int): The length of the pause in seconds. Defaults to 1.6.
"""
def ends_with_major_pause(wav_file_path, speech_frame_threshold=5, pause_length_threshold=1.6):
    vad = webrtcvad.Vad(3)  # Create a VAD. 3 is the highest aggressiveness mode.
    frame_duration = 0.03  # Duration of a frame in seconds.
    num_speech_frames = 0  # Number of frames in the current pause.

    with wave.open(wav_file_path, 'rb') as f:
        sample_width = f.getsampwidth()
        rate = f.getframerate()
        n_frames = int(rate * frame_duration)
        frames = list(wave_read_frames(f, n_frames))

        # Get the last pause_length_threshold seconds' worth of frames
        frames = frames[-int(pause_length_threshold / frame_duration):]

    for frame in frames:  
        try:
            num_speech_frames += vad.is_speech(frame, rate)
        except Exception as e:
            print(f'VadError: Skipping frame {e}')

    return num_speech_frames < speech_frame_threshold

"""A generator that yields frames from a wave file."""
def wave_read_frames(wave_file, n_frames):
    while True:
        frames = wave_file.readframes(n_frames)
        if not frames:
            break
        yield frames
