import time
import json
import threading
import urllib.parse
import os
import subprocess
import requests
import pyaudio
import pyautogui
import speech_recognition as sr
from vosk import Model, KaldiRecognizer
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, Dict, Any

class AssistantEngine(QObject):
    state_changed = pyqtSignal(str, str) # state, message
    command_received = pyqtSignal(str) # command text
    
    def __init__(self) -> None:
        super().__init__()
        
        # 1. Offline Wake Word Detection (Vosk)
        model_path = os.path.join(os.path.dirname(__file__), "model")
        if not os.path.exists(model_path):
            print(f"[Engine] WARNING: Vosk model not found at {model_path}. Wake word may be slow.")
            self.vosk_model = None
        else:
            self.vosk_model = Model(model_path)
        
        # 2. High accuracy recognizer for commands
        self.google_recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        
        self.command_received.connect(self.process_command)
        
        self.is_running = False
        self.expecting_command: bool = False

        # Adjust for ambient noise on startup
        with self.mic as source:
            print("[Engine] Adjusting for ambient noise...")
            self.google_recognizer.adjust_for_ambient_noise(source, duration=1)
            print("[Engine] Ready.")

    def start(self) -> None:
        self.is_running = True
        self.state_changed.emit("idle", "")
        # Start the background listening thread
        threading.Thread(target=self._listen_loop, daemon=True).start()
        print("[Engine] Background listener started.")

    def _listen_loop(self) -> None:
        """Main loop that switches between Vosk (wake word) and Google (command)."""
        while self.is_running:
            if not self.expecting_command:
                self._detect_wake_word_offline()
            else:
                self._capture_command_online()

    def _detect_wake_word_offline(self) -> None:
        """Uses Vosk to listen for 'hello goofy' locally."""
        if not self.vosk_model:
            # Fallback to Google STT for wake word if Vosk is missing
            with self.mic as source:
                try:
                    audio = self.google_recognizer.listen(source, timeout=5, phrase_time_limit=3)
                    text = self.google_recognizer.recognize_google(audio).lower()
                    if "hello goofy" in text or "hey goofy" in text:
                        self._trigger_wake()
                except:
                    pass
            return

        # Vosk local detection
        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
            stream.start_stream()
            
            rec = KaldiRecognizer(self.vosk_model, 16000)
            print("[Engine] Listening for wake word (offline)...")
            
            while not self.expecting_command and self.is_running:
                data = stream.read(4000, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").lower()
                    if "hello" in text and "goofy" in text:
                        self._trigger_wake()
                        break
            
            stream.stop_stream()
            stream.close()
        finally:
            p.terminate()

    def _trigger_wake(self) -> None:
        print("[Engine] Wake word detected!")
        self.expecting_command = True
        self.state_changed.emit("listening", "Listening...")
        # Small sleep to allow Vosk stream to fully release before Google STT starts
        time.sleep(0.3)

    def _capture_command_online(self) -> None:
        """Uses Google STT to capture the actual command for high accuracy."""
        try:
            with self.mic as source:
                # Listen for the command
                audio = self.google_recognizer.listen(source, timeout=5, phrase_time_limit=10)
                self.state_changed.emit("processing", "Processing...")
                text = self.google_recognizer.recognize_google(audio).lower()
                print(f"[Engine] Captured Command: {text}")
                self.command_received.emit(text)
        except sr.WaitTimeoutError:
            self._timeout_listening()
        except sr.UnknownValueError:
            self.state_changed.emit("error", "Didn't catch that.")
            time.sleep(2)
            self.state_changed.emit("idle", "")
        except Exception as e:
            print(f"[Engine] Command capture error: {e}")
            self.state_changed.emit("error", "Error occurred.")
        finally:
            self.expecting_command = False

    def _timeout_listening(self) -> None:
        self.expecting_command = False
        self.state_changed.emit("error", "Timed out.")
        time.sleep(2)
        self.state_changed.emit("idle", "")

    def speak(self, text: str) -> None:
        """Asynchronously speak text using native PowerShell TTS."""
        if not text:
            return
        safe_text = text.replace("'", "''")
        cmd = f"Add-Type -AssemblyName System.speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}')"
        try:
            subprocess.Popen(["powershell", "-NoProfile", "-Command", cmd])
        except Exception as e:
            print(f"[Engine] TTS error: {e}")

    def process_command(self, text: str) -> None:
        self.state_changed.emit("processing", f'"{text}"')
        print(f"[Engine] Processing command: {text}")
        
        parsed_command: Optional[Dict[str, Any]] = None
        # Use an environment variable or default for backend URL
        backend_url = os.getenv("GOOFY_BACKEND_URL", "http://127.0.0.1:8000")
        try:
            res = requests.post(f"{backend_url}/api/v1/commands/parse", json={"transcript": text}, timeout=10)
            res.raise_for_status()
            data = res.json()
            if data.get("intent"):
                parsed_command = data
                print(f"[Engine] Backend parsed intent: {parsed_command.get('intent')}")
        except Exception as e:
            print(f"[Engine] Backend error: {e}")

        success = False
        if parsed_command:
            intent = parsed_command.get("intent")
            params = parsed_command.get("parameters", {})
            
            if intent == "system.open_app":
                app_name = params.get("app_name")
                if app_name:
                    # Secure execution using subprocess instead of os.system
                    try:
                        subprocess.Popen(["cmd", "/c", "start", "", app_name], shell=False)
                        success = True
                    except Exception as e:
                        print(f"[Engine] Launch error: {e}")
            elif intent == "system.screenshot":
                try:
                    filename = f"screenshot_{int(time.time())}.png"
                    pyautogui.screenshot(filename)
                    print(f"[Engine] Screenshot saved: {filename}")
                    success = True
                except Exception as e:
                    print(f"[Engine] Screenshot failed: {e}")
            elif intent == "system.type":
                text_to_type = params.get("text")
                if text_to_type:
                    pyautogui.write(text_to_type, interval=0.01)
                    success = True
            elif intent == "system.press":
                key = params.get("key")
                if key:
                    pyautogui.press(key)
                    success = True
            elif intent == "system.volume":
                action = params.get("action")
                if action == "up":
                    pyautogui.press("volumeup", presses=5)
                    success = True
                elif action == "down":
                    pyautogui.press("volumedown", presses=5)
                    success = True
                elif action in ["mute", "unmute"]:
                    pyautogui.press("volumemute")
                    success = True
            elif intent == "search.google":
                query = params.get("query")
                if query:
                    # Secure URL opening
                    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                    try:
                        subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
                        success = True
                    except Exception as e:
                        print(f"[Engine] Search error: {e}")
            elif intent == "system.run_powershell":
                script = params.get("script")
                if script:
                    try:
                        subprocess.Popen(["powershell", "-NoProfile", "-Command", script])
                        success = True
                    except Exception as e:
                        print(f"[Engine] Powershell error: {e}")
            elif intent == "conversation.chat":
                success = True
        else:
            # Fallback to very basic hardcoded matches if backend is down
            success = self.execute_fallback_command(text)

        if success:
            self.state_changed.emit("success", "Done!")
            if parsed_command and parsed_command.get("response"):
                self.speak(parsed_command.get("response"))
        else:
            self.state_changed.emit("error", "Command failed.")
            
        time.sleep(2)
        self.state_changed.emit("idle", "")

    def execute_fallback_command(self, text: str) -> bool:
        """Basic offline fallback for critical commands."""
        text = text.lower()
        try:
            if "screenshot" in text:
                pyautogui.screenshot(f"screenshot_{int(time.time())}.png")
                return True
            elif "volume up" in text:
                pyautogui.press("volumeup", presses=5)
                return True
            elif "volume down" in text:
                pyautogui.press("volumedown", presses=5)
                return True
            return False
        except:
            return False

