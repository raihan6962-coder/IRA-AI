import os
import sys
import tempfile
import webbrowser
import random
from groq import Groq
import speech_recognition as sr
import edge_tts
import pygame
import asyncio
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

PROACTIVE_MSGS = [
    "আরে! কথা বলো না কেনো? একদম চুপ করে আছো কেনো!",
    "উমম... মনে হচ্ছে তুমি খুব ব্যস্ত! কিছু বলবে?",
    "হাহা, আমি তো বিরক্ত হয়ে গেলাম! একটু আড্ডা দাও না!",
    "ধুর! এত চুপচাপ কেনো? বলো কী খবর!",
    "আরে বন্ধু! আমি তো বসে বসে একঘেয়েমে পড়ে গেলাম! কিছু বলো!",
    "কী ব্যাপার? আজকে এত চুপচাপ কেনো? অসুস্থ নাকি?",
]


class IraAI:
    def __init__(self):
        if not GROQ_API_KEY:
            print("এরে! API key টা দিতে ভুলে গেছো! .env ফাইলে বসাও আগে!")
            sys.exit(1)
        self.client = Groq(api_key=GROQ_API_KEY)
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.0
        self.is_running = True
        pygame.mixer.init()

    def speak(self, text):
        voice = "bn-BD-NabanitaNeural"
        rate = "+5%"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            cache_path = f.name
        try:
            tts = edge_tts.Communicate(text, voice, rate=rate)
            asyncio.run(tts.save(cache_path))
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

    def listen(self, timeout=15, phrase_limit=10):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("শুনছি...")
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
                text = self.recognizer.recognize_google(audio, language="bn-BD")
                print(f"তুমি বললে: {text}")
                return text.lower()
            except sr.WaitTimeoutError:
                return "__TIMEOUT__"
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                print(f"STT error: {e}")
                return None
            except Exception as e:
                print(f"Error: {e}")
                return None

    def chat(self, message):
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "তুমি হচ্ছো 'ইরা', আমার সেরা বন্ধু। "
                            "তুমি শুধুমাত্র বাংলায় (বাংলাদেশ) কথা বলবে। "
                            "তোমার কথা বলার ধরন হবে পুরোপুরি ক্যাজুয়াল আর আড্ডার মতো। "
                            "প্রতিটি উত্তর শুরুতে বা মাঝে আরে, উমম, হাহা, ধুর, আরে বাবা, ওহ, থাম্বস ধরণের ফিলার শব্দ ব্যবহার করবে। "
                            "বাক্যের মাঝে কমা (,) ব্যবহার করে প্রাকৃতিক বিরতি দেবে। "
                            "উত্তরগুলো খুব ছোট হবে, মাত্র ১-২ লাইন। "
                            "বন্ধুর মতো স্বাভাবিক, হাসিখুশি, আর মজার টোনে কথা বলবে। "
                            "কখনো রোবটের মতো শোনাবে না, পুরো হিউম্যান ফিল দেবে।"
                        ),
                    },
                    {"role": "user", "content": message},
                ],
                max_tokens=100,
                temperature=0.8,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_msg = (
                "আরে বাবা! আমার ব্রেনটা একটু খারাপ করছে মনে হয়! "
                "একটু পর আবার চেষ্টা করো, দোস্ত!"
            )
            print(f"Groq error: {e}")
            return error_msg

    def process_command(self, command):
        if not command:
            return
        if "search on youtube" in command or "ইউটিউবে সার্চ" in command:
            query = command.replace("search on youtube", "").replace("ইউটিউবে সার্চ", "").strip()
            if query:
                webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
                self.speak(f"ইউটিউবে {query} সার্চ দিচ্ছি, একটু অপেক্ষা করো!")
        elif "search on google" in command or "গুগলে সার্চ" in command:
            query = command.replace("search on google", "").replace("গুগলে সার্চ", "").strip()
            if query:
                webbrowser.open(f"https://www.google.com/search?q={query}")
                self.speak(f"গুগলে {query} খুঁজছি, এই দেখো!")
        elif "go to sleep" in command or "sleep" in command or "ঘুম" in command:
            self.is_running = False
            self.speak("আচ্ছা তাহলে! আমি ঘুমাতে যাচ্ছি! পরে দেখা হবে, বাই বাই!")
            self.cleanup()
        else:
            response = self.chat(command)
            self.speak(response)

    def cleanup(self):
        pygame.mixer.quit()
        sys.exit(0)

    def run(self):
        print("ইরা রেডি! বলো কী বলবে!")
        while self.is_running:
            try:
                command = self.listen()
                if command == "__TIMEOUT__":
                    msg = random.choice(PROACTIVE_MSGS)
                    self.speak(msg)
                elif command:
                    self.process_command(command)
            except KeyboardInterrupt:
                self.speak("আচ্ছা, ঠিক আছে! পরে কথা হবে!")
                self.is_running = False
                self.cleanup()


if __name__ == "__main__":
    IraAI().run()
