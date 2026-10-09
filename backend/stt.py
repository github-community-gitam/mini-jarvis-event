import sounddevice as sd
import soundfile as sf
import keyboard
import time
import numpy as np
from groq import Groq
from config import GROQ_API_KEY

def record_audio(filename):
    """
    Records audio from the microphone while the SPACE bar is pressed.
    """
    print("\n[Hold SPACE to speak...]")
    # Wait until space is pressed
    while not keyboard.is_pressed('space'):
        time.sleep(0.05)

    print("\r[LISTENING]               ", end="")
    
    samplerate = 44100
    channels = 1
    recording = []
    
    def callback(indata, frames, time_info, status):
        recording.append(indata.copy())

    # Record while space is held down
    with sd.InputStream(samplerate=samplerate, channels=channels, callback=callback):
        while keyboard.is_pressed('space'):
            time.sleep(0.05)

    print("\r[PROCESSING]              ", end="")

    # Save to wav file
    if recording:
        audio_data = np.concatenate(recording, axis=0)
        sf.write(filename, audio_data, samplerate)

def transcribe_audio(filename):
    """
    Transcribes the recorded audio file using Groq Whisper.
    """
    if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY is not set."
        
    client = Groq(api_key=GROQ_API_KEY)
    
    try:
        with open(filename, "rb") as file:
            transcription = client.audio.transcriptions.create(
              file=(filename, file.read()),
              model="whisper-large-v3",
            )
        return transcription.text.strip()
    except Exception as e:
        return f"Transcription error: {e}"
