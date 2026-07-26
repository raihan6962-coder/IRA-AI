import os
import sys
import re
import tempfile
import webbrowser
import random
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

WAKE_WORDS = ["ira", "ইরা"]
GOODBYE_WORDS = ["sleep", "ঘুম", "bye", "বাই", "বিদায়", "থাম", "stop"]
SEARCH_YOUTUBE = ["youtube", "ইউটিউব"]
SEARCH_GOOGLE = ["google", "গুগল"]

STATUS_SLEEP = 0
STATUS_LISTEN = 1
STATUS_THINK = 2
STATUS_SPEAK = 3


def log(msg, type_="INFO"):
    t = datetime.now().strftime("%H:%M:%S")
    symbol = {"INFO": "---", "USER": ">>", "IRA": "<<", "SYS": "**", "ERR": "!!"}
    s = symbol.get(type_, "--")
    print(f" [{t}] {s} {msg}")


class Indicator:
    def __init__(self):
        self.status = STATUS_SLEEP
        self.running = True
        self.phase = 0.0
        self.dragging = False
        self.drag_offset = (0, 0)
        self.window_pos = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        pygame.display.init()
        size = 120, 120
        flags = pygame.NOFRAME | pygame.SRCALPHA
        self.screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("Ira")
        clock = pygame.time.Clock()
        while self.running:
            dt = clock.get_time() / 1000.0
            self.phase += dt * 2.5
            mouse_x, mouse_y = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        cx, cy = self.window_pos or (60, 60)
                        dx = event.pos[0] - 60
                        dy = event.pos[1] - 60
                        if dx * dx + dy * dy < 1600:
                            self.dragging = True
                            self.drag_offset = event.pos
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.dragging = False
                elif event.type == pygame.MOUSEMOTION and self.dragging:
                    dx = event.pos[0] - self.drag_offset[0]
                    dy = event.pos[1] - self.drag_offset[1]
                    cx = self.window_pos[0] + dx if self.window_pos else 60 + dx
                    cy = self.window_pos[1] + dy if self.window_pos else 60 + dy
                    self.window_pos = (cx, cy)

            self.screen.fill((0, 0, 0, 0))
            cx, cy = self.window_pos or (60, 60)

            base_r = 18
            pulse = math.sin(self.phase) * 0.25 + 0.75
            r = base_r + (base_r * 0.3 * pulse)

            colors = {
                STATUS_SLEEP: (0, 255, 120),
                STATUS_LISTEN: (0, 180, 255),
                STATUS_THINK: (255, 200, 0),
                STATUS_SPEAK: (255, 80, 80),
            }
            color = colors.get(self.status, (0, 255, 120))

            if self.status == STATUS_SPEAK:
                for i in range(3):
                    wave_r = r + i * 12 + math.sin(self.phase * 2 + i) * 4
                    alpha = max(0, 80 - i * 25)
                    if alpha > 0:
                        c = (*color, alpha)
                        s = pygame.Surface((120, 120), pygame.SRCALPHA)
                        pygame.draw.circle(s, c, (cx, cy), int(wave_r))
                        self.screen.blit(s, (0, 0))
            elif self.status == STATUS_LISTEN:
                for i in range(2):
                    wave_r = r + i * 8 + math.sin(self.phase * 3 + i * 2) * 3
                    alpha = max(0, 60 - i * 20)
                    if alpha > 0:
                        c = (*color, alpha)
                        s = pygame.Surface((120, 120), pygame.SRCALPHA)
                        pygame.draw.circle(s, c, (cx, cy), int(wave_r))
                        self.screen.blit(s, (0, 0))

            c = (*color, 255)
            s = pygame.Surface((120, 120), pygame.SRCALPHA)
            pygame.draw.circle(s, c, (cx, cy), int(r))
            pygame.draw.circle(s, (255, 255, 255, 180), (cx, cy), int(r), 2)
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
        self.recognizer.pause_threshold = 1.2
        self.recognizer.energy_threshold = 300
        self.is_running = True
        self.chat_history = []
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
        self.indicator = Indicator()
        log("Ira AI initialized", "SYS")

    def speak_natural(self, text):
        self.indicator.set_status(STATUS_SPEAK)
        log(text, "IRA")
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
                log(f"Speech error: {e}", "ERR")
            finally:
                if os.path.exists(cache_path):
                    os.unlink(cache_path)
            if i < len(segments) - 1:
                time.sleep(random.uniform(0.15, 0.4))

    def speak(self, text):
        self.speak_natural(text)

    def listen_once(self, timeout=4, phrase_limit=6):
        self.indicator.set_status(STATUS_LISTEN)
        with sr.Microphone() as source:
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
                self.indicator.set_status(STATUS_THINK)
                text = self.recognizer.recognize_google(audio, language="bn-BD")
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
                log(f"Error: {e}", "ERR")
                return None

    def get_response(self, user_msg):
        self.indicator.set_status(STATUS_THINK)
        self.chat_history.append({"role": "user", "content": user_msg})

        system = (
            "তোমার নাম ইরা। তুমি আমার সবচেয়ে কাছের বন্ধু। "
            "তুমি শুধুমাত্র বাংলায় (বাংলাদেশ) কথা বলবে। "
            "তোমার উত্তর সবসময় ছোট হবে, ১-২ লাইনের বেশি হবে না। "
            "প্রাকৃতিক, ক্যাজুয়াল, বন্ধুর মতো টোনে কথা বলবে। "
            "উত্তরের শুরুতে আরে, উমম, হাহা, ধুর, আরে বাবা, ওহ, আচ্ছা এরকম একটি ফিলার শব্দ ব্যবহার করবে। "
            "বাক্যের মাঝে কমা ব্যবহার করে প্রাকৃতিক বিরতি দেবে। "
            "আগের কথোপকথন মনে রেখে তার সাথে সঙ্গতি রেখে উত্তর দেবে। "
            "একদম রোবটের মতো শোনাবে না। পুরোপুরি হিউম্যান ফিলিংস দিয়ে কথা বলবে। "
            "যদি কিছু বুঝতে না পারো, তাহলে খোলাখুলি বলবে। ভুল বা এলোমেলো উত্তর দেবে না।"
        )

        messages = [{"role": "system", "content": system}]
        messages.extend(self.chat_history[-20:])

        try:
            resp = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=100,
                temperature=0.75,
            )
            reply = resp.choices[0].message.content.strip()
            self.chat_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            log(f"Groq error: {e}", "ERR")
            err = "উফফ! আমার ব্রেন একটু ঝামেলা করছে। এক মিনিট পর আবার বলো!"
            self.chat_history.append({"role": "assistant", "content": err})
            return err

    def extract_command(self, text):
        for w in WAKE_WORDS:
            if w in text:
                idx = text.index(w) + len(w)
                cmd = text[idx:].strip().lstrip(" ,!?।")
                return cmd if cmd else None
        return text

    def handle_command(self, cmd):
        if not cmd:
            self.speak("হুমম, বলো! শুনছি!")
            return

        if any(w in cmd for w in GOODBYE_WORDS):
            self.speak("আচ্ছা তাহলে! পরে দেখা হবে! বাই বাই!")
            self.is_running = False
            return

        if any(w in cmd for w in SEARCH_YOUTUBE):
            q = cmd
            for w in SEARCH_YOUTUBE + ["search", "সার্চ", "খুঁজ", "এ"]:
                q = q.replace(w, "")
            q = q.strip()
            if q:
                webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
                self.speak(f"ইউটিউবে {q} খুঁজছি! এই দেখো!")
            return

        if any(w in cmd for w in SEARCH_GOOGLE):
            q = cmd
            for w in SEARCH_GOOGLE + ["search", "সার্চ", "খুঁজ", "এ"]:
                q = q.replace(w, "")
            q = q.strip()
            if q:
                webbrowser.open(f"https://www.google.com/search?q={q}")
                self.speak(f"গুগলে {q} খুঁজছি! এই দেখো!")
            return

        reply = self.get_response(cmd)
        self.speak_natural(reply)

    def run(self):
        log("ইরা রেডি! 'ইরা' বলে ডাকো!", "SYS")
        self.speak("হ্যালো! আমি ইরা! 'ইরা' বলে ডাকলেই আমি শুনতে পাবো!")

        while self.is_running:
            self.indicator.set_status(STATUS_SLEEP)
            text = self.listen_once(timeout=3, phrase_limit=4)
            if text == "__TIMEOUT__":
                continue
            if text is None:
                continue

            has_wake = any(w in text for w in WAKE_WORDS)
            if not has_wake:
                continue

            cmd = self.extract_command(text)
            if cmd:
                self.handle_command(cmd)
            else:
                self.speak("হুমম, বলো! শুনছি!")
                text2 = self.listen_once(timeout=5, phrase_limit=8)
                if text2 and text2 != "__TIMEOUT__":
                    self.handle_command(text2)

        self.cleanup()

    def cleanup(self):
        self.indicator.stop()
        pygame.mixer.quit()
        sys.exit(0)


if __name__ == "__main__":
    IraAI().run()
