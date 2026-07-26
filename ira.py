import os
import sys
import re
import tempfile
import webbrowser
import random
import time
from groq import Groq
import speech_recognition as sr
import edge_tts
import pygame
import asyncio


def load_env():
    path = ".env"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip("\"'")


load_env()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("এরে! API key টা দিতে ভুলে গেছো! .env ফাইলে বসাও আগে!")
    sys.exit(1)

WAKE_WORDS = ["ira", "ইরা"]
GOODBYE_WORDS = ["sleep", "ঘুম", "bye", "বাই", "বিদায়", "থাম"]
SEARCH_YOUTUBE = ["youtube", "ইউটিউব"]
SEARCH_GOOGLE = ["google", "গুগল"]


class IraAI:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.5
        self.recognizer.energy_threshold = 300
        self.is_running = True
        self.is_awake = False
        self.chat_history = []
        pygame.mixer.init()

    def speak_natural(self, text):
        """Speak with natural human-like pacing and pauses."""
        segments = re.split(r'(?<=[।,?!])\s*', text)
        segments = [s.strip() for s in segments if s.strip()]
        if not segments:
            return
        for i, segment in enumerate(segments):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                cache_path = f.name
            try:
                tts = edge_tts.Communicate(segment, "bn-BD-NabanitaNeural", rate="+5%")
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
            if i < len(segments) - 1:
                time.sleep(random.uniform(0.2, 0.6))

    def speak(self, text):
        self.speak_natural(text)

    def listen_once(self, timeout=5, phrase_limit=8):
        with sr.Microphone() as source:
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
                text = self.recognizer.recognize_google(audio, language="bn-BD")
                return text.lower().strip()
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

    def contains_wake_word(self, text):
        if not text:
            return False
        for ww in WAKE_WORDS:
            if ww in text:
                return True
        return False

    def contains_goodbye(self, text):
        if not text:
            return False
        for gw in GOODBYE_WORDS:
            if gw in text:
                return True
        return False

    def chat_with_context(self, user_msg):
        self.chat_history.append({"role": "user", "content": user_msg})
        messages = [
            {
                "role": "system",
                "content": (
                    "তোমার নাম ইরা। তুমি আমার সবচেয়ে কাছের বন্ধু। "
                    "তুমি শুধু বাংলায় (বাংলাদেশ) কথা বলবে। বন্ধুর মতো অত্যন্ত ক্যাজুয়াল ও স্বাভাবিক ভাষায় কথা বলবে। "
                    "উত্তর খুব ছোট হবে, ১-২ লাইনের বেশি নয়। "
                    "প্রতিটি উত্তরের শুরুতে আরে, উমম, হাহা, ধুর, আরে বাবা, ওহ, আচ্ছা এরকম একটি ফিলার শব্দ দেবে। "
                    "বাক্যের মাঝে কমা (,) ব্যবহার করবে, যাতে স্বাভাবিক বিরতি তৈরি হয়। "
                    "আগের কথোপকথন মনে রাখবে এবং তার সাথে সামঞ্জস্য রেখে উত্তর দেবে। "
                    "একদম রোবটের মতো নয়, পুরোপুরি হিউম্যান ফিলিংস সহ কথা বলবে। "
                    "যদি কিছু বুঝতে না পারো, তাহলে সেটা খোলাখুলি বলবে। ভুল উত্তর দেবে না।"
                ),
            }
        ]
        messages.extend(self.chat_history[-20:])
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=120,
                temperature=0.8,
            )
            reply = response.choices[0].message.content.strip()
            self.chat_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            print(f"Groq error: {e}")
            err = "আরে বাবা! আমার ব্রেনটা একটু খারাপ করছে মনে হয়! একটু পর আবার চেষ্টা করো, দোস্ত!"
            self.chat_history.append({"role": "assistant", "content": err})
            return err

    def wait_for_wake_word(self):
        print("[ঘুম mode] 'ইরা' বলো আমাকে ডাকতে...")
        while self.is_running:
            text = self.listen_once(timeout=5, phrase_limit=3)
            if text == "__TIMEOUT__":
                continue
            if text and self.contains_wake_word(text):
                return text
            if text and self.contains_goodbye(text):
                self.is_running = False
                return None

    def run(self):
        print("ইরা রেডি! 'ইরা' বলে ডাকো!")
        self.speak("হ্যালো! আমি ইরা, তোমার বন্ধু। 'ইরা' বলে ডাকলেই আমি শুনতে পাবো!")
        while self.is_running:
            result = self.wait_for_wake_word()
            if not result:
                break
            self.is_awake = True
            self.speak("হুমম, বলো!")
            self.chat_history = []
            idle_count = 0
            while self.is_running and self.is_awake:
                text = self.listen_once(timeout=10, phrase_limit=10)
                if text is None:
                    continue
                if text == "__TIMEOUT__":
                    idle_count += 1
                    if idle_count >= 3:
                        self.speak("আচ্ছা, তাহলে আমি আবার ঘুমাই! দরকার হলে 'ইরা' বলে ডেকো!")
                        self.is_awake = False
                        self.chat_history = []
                    else:
                        msgs = [
                            "আরে! কী বলবে বলো না!",
                            "হ্যালো! আমি এখানেই আছি! কিছু বলবে?",
                            "বলো বলো, শুনছি!",
                        ]
                        self.speak(random.choice(msgs))
                    continue
                idle_count = 0
                if self.contains_goodbye(text):
                    self.speak("আচ্ছা তাহলে! আমি ঘুমাতে যাচ্ছি! পরে দেখা হবে, 'ইরা' বলে ডেকো!")
                    self.is_awake = False
                    self.chat_history = []
                    continue
                if any(w in text for w in SEARCH_YOUTUBE):
                    query = text
                    for w in SEARCH_YOUTUBE + ["search", "সার্চ", "খুঁজ"]:
                        query = query.replace(w, "")
                    query = query.strip()
                    if query:
                        webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
                        self.speak(f"ইউটিউবে {query} খুঁজছি! এই নাও!")
                    continue
                if any(w in text for w in SEARCH_GOOGLE):
                    query = text
                    for w in SEARCH_GOOGLE + ["search", "সার্চ", "খুঁজ"]:
                        query = query.replace(w, "")
                    query = query.strip()
                    if query:
                        webbrowser.open(f"https://www.google.com/search?q={query}")
                        self.speak(f"গুগলে {query} খুঁজছি! এই দেখো!")
                    continue
                reply = self.chat_with_context(text)
                self.speak_natural(reply)
        self.cleanup()

    def cleanup(self):
        pygame.mixer.quit()
        sys.exit(0)


if __name__ == "__main__":
    IraAI().run()
