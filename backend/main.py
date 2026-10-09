import sys
import os
import time
from config import TEMP_AUDIO_FILE
from stt import record_audio, transcribe_audio
from brain import generate_response
from tts import speak
from commands import check_for_commands

def print_header():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("========================================")
    print("              J A R V I S               ")
    print("========================================")

def cleanup():
    if os.path.exists(TEMP_AUDIO_FILE):
        try:
            os.remove(TEMP_AUDIO_FILE)
        except:
            pass

import memory

def main():
    print_header()
    
    # Initialize conversation
    conversation_id = memory.create_conversation(title="Voice Session")
    if conversation_id:
        print(f"\n[Conversation Initialized: {conversation_id}]")
    else:
        print("\n[Warning: Supabase not connected. Using local memory.]")
    
    while True:
        try:
            # 1. Listen to microphone
            record_audio(TEMP_AUDIO_FILE)
            
            # 2. Transcribe audio to text
            user_text = transcribe_audio(TEMP_AUDIO_FILE)
            
            if not user_text:
                continue
                
            print(f"\n\nUSER:\n{user_text}\n")
            
            # 3. Check for local computer actions
            command_response = check_for_commands(user_text)
            
            if command_response:
                jarvis_response = command_response
            else:
                # 4. Generate JARVIS AI response
                jarvis_response = generate_response(user_text, conversation_id=conversation_id)
            
            print(f"\nJARVIS:\n{jarvis_response}\n")
            
            # 5. Play response through speaker
            speak(jarvis_response)
            
            if "Goodbye, sir. Shutting down systems." in jarvis_response:
                break
                
        except KeyboardInterrupt:
            print("\nShutting down, sir.")
            break
        except Exception as e:
            print(f"\n[Error: {e}]")
            time.sleep(1)

    cleanup()

if __name__ == "__main__":
    main()
