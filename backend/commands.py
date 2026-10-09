import subprocess
import platform
import datetime
import os

def check_for_commands(text):
    """
    Checks if the user's input matches any predefined safe local computer actions.
    Returns JARVIS's response string if a command was executed, otherwise None.
    """
    text = text.lower()
    system = platform.system()
    
    if "open chrome" in text or "open browser" in text:
        try:
            if system == "Windows":
                os.startfile("chrome.exe")
            elif system == "Darwin":
                subprocess.Popen(["open", "-a", "Google Chrome"])
            else:
                subprocess.Popen(["google-chrome"])
            return "Opening Google Chrome, sir."
        except Exception:
            return "I attempted to open Chrome, sir, but encountered an error."

    elif "open vs code" in text or "open visual studio code" in text or "open code" in text:
        try:
            if system == "Windows":
                subprocess.Popen(["code", "."], shell=True)
            elif system == "Darwin":
                subprocess.Popen(["open", "-a", "Visual Studio Code"])
            else:
                subprocess.Popen(["code"])
            return "Opening Visual Studio Code, sir."
        except Exception:
            return "I could not locate Visual Studio Code, sir."

    elif "open my downloads" in text or "open downloads" in text:
        try:
            downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
            if system == "Windows":
                os.startfile(downloads_path)
            elif system == "Darwin":
                subprocess.Popen(["open", downloads_path])
            else:
                subprocess.Popen(["xdg-open", downloads_path])
            return "I have opened your Downloads folder."
        except Exception:
            return "I was unable to open the Downloads folder, sir."

    elif "current time" in text or "what time is it" in text:
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        return f"The current time is {time_str}, sir."
        
    elif "we're done" in text or "shut down" in text or "goodbye" in text:
        return "Goodbye, sir. Shutting down systems."

    return None
