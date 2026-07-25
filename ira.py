import requests
import json
import re
import webbrowser
import playsound
import tempfile
import threading
import queue
import os
import sys
from groq import Groq
import speech_recognition as sr
import edge_tts
import pygame
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class IraAI:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.recognizer = sr.Recognizer()
        self.is_running = True
        self.audio_queue = queue.Queue()
        pygame.mixer.init()

    def speak(self, text):
        try:
            voice = "en-US-JennyNeural"
            cache_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            cache_path = cache_file.name
            cache_file.close()

            async def speak_async():
                communicate = await edge_tts.Communicate(text, voice)
                await communicate.save(cache_path)

            import asyncio
            asyncio.run(speak_async())

            pygame.mixer.music.load(cache_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
            os.unlink(cache_path)
        except Exception as e:
            print(f"Error speaking: {e}")

    def listen(self):
        with sr.Microphone() as source:
            print("Listening...")
            audio = self.recognizer.listen(source)
            try:
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")
                return text.lower()
            except sr.UnknownValueError:
                print("Sorry, I couldn't understand that")
                return None
            except sr.RequestError as e:
                print(f"Error: {e}")
                return None

    def chat(self, message):
        try:
            response = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "You are Ira, a friendly, sweet, highly interactive, and funny female AI assistant. You talk like a close friend. Keep your responses short and casual. You make simple, direct responses with a warm, friendly tone. Use '!' instead of other punctuation if you need to add excitement."},
                    {"role": "user", "content": message}
                ],
                max_tokens=100,
                temperature=0.7
            )
            reply = response.choices[0].message.content
            return reply.strip()
        except Exception as e:
            print(f"Error in chat: {e}")
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

        elif "good morning" in command or "good evening" in command:
            self.speak("Morning/Aftonoo! What's on your mind?")

        elif "go to sleep" in command or "sleep" in command:
            self.is_running = False
            self.speak("Good Bye! See you later!")
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
    irai = IraAI()
    irai.run()
