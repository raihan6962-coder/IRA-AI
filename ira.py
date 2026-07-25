import asyncio
import os
import sys
import tempfile
import webbrowser
from groq import Groq
import speech_recognition as sr
import edge_tts
import pygame
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class IraAI:
    def __init__(self):
        if not GROQ_API_KEY:
            print("Error: GROQ_API_KEY not found in .env file")
            sys.exit(1)
        self.client = Groq(api_key=GROQ_API_KEY)
        self.recognizer = sr.Recognizer()
        self.is_running = True
        pygame.mixer.init()

    def speak(self, text):
        voice = "en-US-JennyNeural"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            cache_path = f.name
        try:
            asyncio.run(edge_tts.Communicate(text, voice).save(cache_path))
            pygame.mixer.music.load(cache_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
        except Exception as e:
            print(f"Speech error: {e}")
        finally:
            if os.path.exists(cache_path):
                os.unlink(cache_path)

    def listen(self):
        with sr.Microphone() as source:
            print("Listening...")
            try:
                audio = self.recognizer.listen(source)
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")
                return text.lower()
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                print(f"Google STT error: {e}")
                return None
            except Exception as e:
                print(f"Error: {e}")
                return None

    def chat(self, message):
        try:
            response = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "You are Ira, a friendly, sweet, highly interactive, and funny female AI assistant. You talk like a close friend. Keep your responses short and casual."},
                    {"role": "user", "content": message}
                ],
                max_tokens=100,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Groq error: {e}")
            return None

    def process_command(self, command):
        if not command:
            return
        if "search on youtube" in command:
            query = command.replace("search on youtube", "").strip()
            if query:
                webbrowser.open(f"https://www.youtube.com/search?q={query}")
                self.speak(f"Searching YouTube for {query}")
        elif "search on google" in command:
            query = command.replace("search on google", "").strip()
            if query:
                webbrowser.open(f"https://www.google.com/search?q={query}")
                self.speak(f"Searching Google for {query}")
        elif "go to sleep" in command or "goodbye" in command:
            self.is_running = False
            self.speak("Goodbye! See you later!")
            self.cleanup()
        else:
            response = self.chat(command)
            if response:
                self.speak(response)

    def cleanup(self):
        pygame.mixer.quit()
        sys.exit(0)

    def run(self):
        print("Ira is ready!")
        while self.is_running:
            command = self.listen()
            if command:
                self.process_command(command)


if __name__ == "__main__":
    IraAI().run()
