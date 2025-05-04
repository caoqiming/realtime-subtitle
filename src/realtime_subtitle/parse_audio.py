import wave
import os
import numpy as np


def parse_audio(file_path: str, speaker_num: int = -1):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Open the audio file
    with wave.open(file_path, "rb") as wav_file:
        # Check audio properties
        num_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frame_rate = wav_file.getframerate()
        num_frames = wav_file.getnframes()

        # Ensure the audio is mono
        if num_channels != 1:
            raise ValueError("Only mono audio is supported.")

        # Read raw audio frames
        raw_data = wav_file.readframes(num_frames)

        # Convert raw data to numpy array
        dtype = np.int16 if sample_width == 2 else np.uint8
        audio_data = np.frombuffer(raw_data, dtype=dtype)

        # Resample to 16000 Hz if necessary
        if frame_rate != 16000:
            num_samples = int(len(audio_data) * 16000 / frame_rate)
            audio_data = np.interp(
                np.linspace(0, len(audio_data), num_samples, endpoint=False),
                np.arange(len(audio_data)),
                audio_data,
            ).astype(np.int16)

        # Convert to bytes
        current_buffer: bytes = audio_data.tobytes()
        from realtime_subtitle import RealtimeSubtitle
        rs = RealtimeSubtitle()
        rs.audio_buffer = current_buffer
        rs.handle_once()
        rs.export(speaker_num=speaker_num)
    return
