import requests
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from config import TTS_API_KEY, OUTPUT_AUDIO_FILE

# Initialize pygame mixer for audio playback (will fail silently on headless servers like Render)
try:
    pygame.mixer.init()
except pygame.error:
    print("[Warning: Audio device not found. Local speaker output disabled.]")

def speak(text):
    """
    Convert JARVIS response text into speech and immediately play the audio.
    Uses ElevenLabs API for a cinematic voice.
    """
    print("\r[SPEAKING]                ")
    
    if not TTS_API_KEY:
        print(f"JARVIS (Text Only): {text}")
        print("[Warning: TTS_API_KEY is not set. Audio disabled.]")
        return

    # ElevenLabs API configuration
    # Voice ID for "George" or "Brian" - deep cinematic voices. 
    # 'nPczCjzI2devNBz1zQrb' is Brian (Deep, British-ish).
    VOICE_ID = "nPczCjzI2devNBz1zQrb" 
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    
    headers = {
        "xi-api-key": TTS_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5", # Turbo model is faster for lower latency
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            # Save the audio file
            with open(OUTPUT_AUDIO_FILE, "wb") as f:
                f.write(response.content)
            
            # Play the audio
            pygame.mixer.music.load(OUTPUT_AUDIO_FILE)
            pygame.mixer.music.play()
            
            # Wait for audio to finish playing
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
            # Cleanup
            pygame.mixer.music.unload()
            if os.path.exists(OUTPUT_AUDIO_FILE):
                os.remove(OUTPUT_AUDIO_FILE)
        else:
            print(f"JARVIS (Text Only): {text}")
            print(f"[TTS Error: {response.text}]")
    except Exception as e:
        print(f"JARVIS (Text Only): {text}")
        print(f"[Audio Playback Error: {e}]")

def generate_audio(text):
    """
    Generate audio bytes without playing them. Useful for the web frontend.
    """
    if not TTS_API_KEY:
        return None

    VOICE_ID = "nPczCjzI2devNBz1zQrb"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    
    headers = {
        "xi-api-key": TTS_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"[TTS Generation Error: {e}]")
    return None
