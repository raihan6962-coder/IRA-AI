import os
import sys
import tempfile
import webbrowser
import time
import math
import threading
from groq import Groq
import speech_recognition as sr
import edge_tts
import pygame
import asyncio
from datetime import datetime


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
    print("API key not found in .env file")
    sys.exit(1)

WAKE_WORDS = ["ira", "ইরা", "আইরা"]
GOODBYE_WORDS = ["sleep", "ঘুম", "bye", "বাই", "বিদায়", "থাম", "stop"]
SEARCH_YOUTUBE = ["youtube", "ইউটিউব"]
SEARCH_GOOGLE = ["google", "গুগল"]

STATUS_SLEEP = 0
STATUS_LISTEN = 1
STATUS_THINK = 2
STATUS_SPEAK = 3


def log(msg, type_="INFO"):
    t = datetime.now().strftime("%H:%M:%S")
    symbol = {"INFO": "•", "USER": "»", "IRA": "«", "SYS": "◆", "ERR": "✗"}
    s = symbol.get(type_, "•")
    print(f" {t} {s} {msg}")


class Indicator:
    def __init__(self):
        self.status = STATUS_SLEEP
        self.running = True
        self.phase = 0.0
        self.dragging = False
        self.drag_start = (0, 0)
        self.win_x, self.win_y = 0, 0
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        pygame.display.init()
        self.screen = pygame.display.set_mode((120, 120), pygame.NOFRAME | pygame.SRCALPHA)
        pygame.display.set_caption("Ira")
        clock = pygame.time.Clock()
        while self.running:
            dt = clock.get_time() / 1000.0
            self.phase += dt * 3.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    cx, cy = 60, 60
                    dx, dy = event.pos[0] - cx, event.pos[1] - cy
                    if dx * dx + dy * dy < 2500:
                        self.dragging = True
                        self.drag_start = (event.pos[0] - self.win_x, event.pos[1] - self.win_y)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.dragging = False
                elif event.type == pygame.MOUSEMOTION and self.dragging:
                    self.win_x = event.pos[0] - self.drag_start[0]
                    self.win_y = event.pos[1] - self.drag_start[1]

            colors = {
                STATUS_SLEEP: (0, 255, 120),
                STATUS_LISTEN: (0, 180, 255),
                STATUS_THINK: (255, 200, 0),
                STATUS_SPEAK: (255, 80, 80),
            }
            color = colors.get(self.status, (0, 255, 120))
            self.screen.fill((0, 0, 0, 0))

            cx, cy = 60 + self.win_x, 60 + self.win_y
            pulse = math.sin(self.phase) * 0.3 + 0.7
            r = int(18 + 8 * pulse)

            if self.status == STATUS_SPEAK:
                for i in range(4):
                    wr = r + i * 10 + math.sin(self.phase * 2 + i) * 5
                    alpha = max(0, 70 - i * 18)
                    if alpha > 0:
                        s = pygame.Surface((120, 120), pygame.SRCALPHA)
                        pygame.draw.circle(s, (*color, alpha), (cx, cy), int(wr))
                        self.screen.blit(s, (0, 0))
            elif self.status == STATUS_LISTEN:
                for i in range(2):
                    wr = r + i * 8 + math.sin(self.phase * 3 + i) * 3
                    alpha = max(0, 50 - i * 15)
                    if alpha > 0:
                        s = pygame.Surface((120, 120), pygame.SRCALPHA)
                        pygame.draw.circle(s, (*color, alpha), (cx, cy), int(wr))
                        self.screen.blit(s, (0, 0))

            s = pygame.Surface((120, 120), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, 255), (cx, cy), r)
            pygame.draw.circle(s, (255, 255, 255, 160), (cx, cy), r, 2)
            self.screen.blit(s, (0, 0))
            pygame.display.update()
            clock.tick(60)
        pygame.display.quit()

    def set_status(self, s):
        self.status = s

    def stop(self):
        self.running = False
        self.thread.join(timeout=2)


class IraAI:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self.recognizer.energy_threshold = 100
        self.recognizer.dynamic_energy_threshold = True
        self.is_running = True
        self.chat_history = []
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
        self.indicator = Indicator()
        log("Ira ready!", "SYS")

    def speak(self, text):
        self.indicator.set_status(STATUS_SPEAK)
        log(text, "IRA")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            path = f.name
        try:
            tts = edge_tts.Communicate(text, "bn-BD-NabanitaNeural", rate="+0%")
            asyncio.run(tts.save(path))
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
        except Exception as e:
            log(f"Speech error: {e}", "ERR")
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def listen(self, timeout=4, limit=5):
        self.indicator.set_status(STATUS_LISTEN)
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=limit)
                self.indicator.set_status(STATUS_THINK)
                try:
                    text = self.recognizer.recognize_google(audio, language="bn-BD")
                except sr.UnknownValueError:
                    text = self.recognizer.recognize_google(audio, language="en-US")
                log(text, "USER")
                return text.lower().strip()
            except sr.WaitTimeoutError:
                return "__TIMEOUT__"
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                log(f"STT error: {e}", "ERR")
                return None
            except Exception as e:
                return None

    def get_reply(self, msg):
        self.indicator.set_status(STATUS_THINK)
        self.chat_history.append({"role": "user", "content": msg})
        system = (
            "তুমি ইরা। তুমি আমার বন্ধু। খুব ছোট করে উত্তর দাও, মাত্র ১ লাইন। "
            "সবসময় বাংলায় বলো। স্বাভাবিক, ক্যাজুয়াল টোনে বলো। "
            "প্রতিবার উত্তরের শুরুতে একটি ফিলার শব্দ দাও: আরে, উমম, হাহা, ধুর, আচ্ছা, ওহ।"
        )
        msgs = [{"role": "system", "content": system}]
        msgs.extend(self.chat_history[-10:])
        try:
            resp = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=msgs,
                max_tokens=80,
                temperature=0.7,
            )
            reply = resp.choices[0].message.content.strip()
            self.chat_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            log(f"Groq error: {e}", "ERR")
            return "উফ! একটু সমস্যা হচ্ছে। আবার বলো তো?"

    def run(self):
        self.speak("হ্যালো! আমি ইরা! ইরা বলে ডাকলেই শুনবো!")
        while self.is_running:
            self.indicator.set_status(STATUS_SLEEP)
            text = self.listen(timeout=3, limit=4)
            if text == "__TIMEOUT__" or text is None:
                continue

            found_wake = False
            rest = text
            for w in WAKE_WORDS:
                if w in text:
                    idx = text.index(w) + len(w)
                    rest = text[idx:].strip().lstrip(" ,!?।")
                    found_wake = True
                    break

            if not found_wake:
                continue

            if not rest:
                self.speak("হুম, বলো!")
                rest = self.listen(timeout=4, limit=8)
                if rest == "__TIMEOUT__" or rest is None:
                    continue

            if any(w in rest for w in GOODBYE_WORDS):
                self.speak("আচ্ছা, পরে দেখা হবে! বাই!")
                self.is_running = False
                break

            if any(w in rest for w in SEARCH_YOUTUBE):
                q = rest
                for w in SEARCH_YOUTUBE + ["search", "সার্চ", "খুঁজ"]:
                    q = q.replace(w, "")
                q = q.strip()
                if q:
                    webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
                    self.speak(f"ইউটিউবে {q} খুঁজছি!")
                continue

            if any(w in rest for w in SEARCH_GOOGLE):
                q = rest
                for w in SEARCH_GOOGLE + ["search", "সার্চ", "খুঁজ"]:
                    q = q.replace(w, "")
                q = q.strip()
                if q:
                    webbrowser.open(f"https://www.google.com/search?q={q}")
                    self.speak(f"গুগলে {q} খুঁজছি!")
                continue

            reply = self.get_reply(rest)
            self.speak(reply)
        self.cleanup()

    def cleanup(self):
        self.indicator.stop()
        pygame.mixer.quit()
        sys.exit(0)


if __name__ == "__main__":
    IraAI().run()
