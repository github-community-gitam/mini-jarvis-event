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
    
    # CLI uses the same authenticated identity as the web app.
    from getpass import getpass
    from security import authenticate, owner_context
    code = os.getenv('JARVIS_ACCESS_CODE') or getpass('Personal access code: ')
    owner_context.set(authenticate(code))
    # Initialize conversation
    conversation_id = memory.create_conversation(title="Voice Session")
    if conversation_id:
        print(f"\n[Conversation Initialized: {conversation_id}]")
    else:
        raise RuntimeError("Database unavailable")
    
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
                jarvis_response, tool_call = generate_response(user_text, conversation_id=conversation_id)
                if tool_call:
                    import json
                    print(json.dumps(tool_call['arguments'], indent=2))
                    approved = input('Approve this action? [y/N] ').strip().lower() == 'y'
                    confirmation = {k: tool_call[k] for k in ('tool_name', 'arguments', 'action_id')}
                    confirmation['approved'] = approved
                    jarvis_response, _ = generate_response('', conversation_id=conversation_id, tool_execution=confirmation)
            
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
