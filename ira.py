import os
import re
import json
import random
import asyncio
import webbrowser
import subprocess
from datetime import datetime

import speech_recognition as sr
import edge_tts
import pygame
from groq import Groq

# ======================= CONFIG (এখানে বদলাতে পারবেন) =======================
GROQ_API_KEY = "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"
MODEL_NAME = "llama-3.1-8b-instant"
VOICE = "bn-BD-NabanitaNeural"
VOICE_RATE = "+5%"
WAKE_WORDS = ["ira", "ইরা", "আয়রা"]               # যেকোনো একটা বললেই সে সাড়া দেবে
SILENCE_TIMEOUT = 15                              # সেকেন্ড, এতক্ষণ চুপ থাকলে সে নিজে থেকে বলবে
MEMORY_FILE = "ira_memory.json"
LOG_FILE = "ira_log.txt"
# ==============================================================================

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = (
    "তোমার নাম ইরা। তুমি আমার বেস্ট ফ্রেন্ড। তুমি সবসময় বাংলায় কথা বলবে, "
    "তবে একদম আড্ডার ভাষায় (Casual/Informal), কোনোভাবেই বইয়ের ভাষায় বা রোবটের মতো নয়। "
    "কথা বলার সময় প্রচুর ইমোশন দেখাবে। বাক্যের মাঝে কমা (,) ব্যবহার করবে যাতে গলার স্বরে পজ আসে। "
    "মাঝে মাঝে 'আরে!', 'উমম...', 'হাহা', 'ধুর!' এই ধরনের শব্দ ব্যবহার করবে। "
    "উত্তর খুব ছোট রাখবে, ১-২ লাইনের মধ্যে।"
)

chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]
MAX_HISTORY_TURNS = 12  # এর বেশি পুরোনো কথা আর মনে রাখবে না (স্লো/ভারী হবে না)


# ------------------------- Logging -------------------------
def log(line: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {line}\n")
    except Exception:
        pass


# ------------------------- Memory (হালকা, লোকাল ফাইল) -------------------------
SENSITIVE_PATTERNS = [
    r"\b\d{10,16}\b",                 # ফোন নাম্বার/কার্ড নাম্বারের মতো লম্বা সংখ্যা
    r"\b\d{3}[- ]?\d{3}[- ]?\d{4}\b", # ফোন নাম্বার প্যাটার্ন
]

def redact(text: str) -> str:
    for pattern in SENSITIVE_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text)
    return text

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_memory_fact(fact: str):
    facts = load_memory()
    facts.append(redact(fact))
    facts = facts[-50:]  # সর্বোচ্চ ৫০টা ফ্যাক্ট রাখবে, ফাইল ছোট থাকবে
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(facts, f, ensure_ascii=False, indent=2)
    log(f"MEMORY SAVED: {fact}")

def inject_memory_into_prompt():
    facts = load_memory()
    if facts:
        memory_text = "এই কিছু জিনিস তুমি আগে থেকে মনে রেখেছো আমার সম্পর্কে: " + "; ".join(facts)
        chat_history.append({"role": "system", "content": memory_text})


# ------------------------- Voice output -------------------------
async def speak(text: str):
    print(f"Ira: {text}")
    log(f"IRA SAID: {text}")
    communicate = edge_tts.Communicate(text, VOICE, rate=VOICE_RATE)
    await communicate.save("voice.mp3")

    pygame.mixer.init()
    pygame.mixer.music.load("voice.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.quit()
    os.remove("voice.mp3")


# ------------------------- Voice input -------------------------
def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Ira is listening...")
        r.adjust_for_ambient_noise(source)
        try:
            audio = r.listen(source, timeout=SILENCE_TIMEOUT, phrase_time_limit=12)
            command = r.recognize_google(audio, language="bn-BD").lower()
            print(f"You said: {command}")
            log(f"USER SAID: {command}")
            return command
        except sr.WaitTimeoutError:
            return "SILENCE"
        except Exception:
            return "ERROR"


def strip_wake_word(text: str) -> str:
    """বাক্যের যেকোনো জায়গা থেকে wake word সরিয়ে বাকি কমান্ডটা রিটার্ন করে।"""
    cleaned = text
    for w in WAKE_WORDS:
        cleaned = cleaned.replace(w.lower(), "")
    return cleaned.strip(" ,।!.")


def contains_wake_word(text: str) -> bool:
    return any(w.lower() in text for w in WAKE_WORDS)


# ------------------------- Skills (মডুলার ফাংশন) -------------------------
def skill_youtube(query: str):
    query = query.replace("youtube", "").replace("ইউটিউব", "").replace("সার্চ", "").replace("search", "").strip()
    webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
    return "আচ্ছা, ইউটিউবে খুঁজছি! এক সেকেন্ড..."

def skill_google(query: str):
    query = query.replace("google", "").replace("গুগল", "").replace("সার্চ", "").replace("search", "").strip()
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return "ঠিক আছে, গুগলে সার্চ করছি!"

def skill_time(_):
    now = datetime.now().strftime("%I:%M %p")
    return f"এখন বাজে {now}।"

def skill_date(_):
    today = datetime.now().strftime("%d %B, %Y")
    return f"আজকে {today}।"

def skill_open_notepad(_):
    try:
        subprocess.Popen(["notepad.exe"])
        return "নোটপ্যাড খুলে দিলাম!"
    except Exception:
        return "নোটপ্যাড খুলতে পারলাম না, দুঃখিত।"

def skill_open_calculator(_):
    try:
        subprocess.Popen(["calc.exe"])
        return "ক্যালকুলেটর খুলে দিলাম!"
    except Exception:
        return "ক্যালকুলেটর খুলতে পারলাম না, দুঃখিত।"

def skill_remember(command: str):
    fact = command.replace("মনে রাখো", "").replace("মনে রেখো", "").strip(" ,।")
    if fact:
        save_memory_fact(fact)
        return "আচ্ছা, এটা আমি মনে রাখলাম!"
    return "কী মনে রাখতে হবে, সেটা বলো তো আবার।"


# কমান্ডের কীওয়ার্ড আর তার সাথের স্কিল ফাংশন
SKILLS = [
    (["youtube", "ইউটিউব"], skill_youtube),
    (["google", "গুগল"], skill_google),
    (["সময়", "কয়টা বাজে", "what time"], skill_time),
    (["তারিখ", "আজকে কী বার", "date"], skill_date),
    (["notepad", "নোটপ্যাড"], skill_open_notepad),
    (["calculator", "ক্যালকুলেটর"], skill_open_calculator),
    (["মনে রাখো", "মনে রেখো"], skill_remember),
]

EXIT_WORDS = ["ঘুমাও", "বিদায়", "bye", "sleep"]

PROACTIVE_MESSAGES = [
    "উমম..., এত চুপচাপ কেন? কিছু একটা বলো!",
    "আরে, তুমি কি আছো? নাকি ঘুমিয়ে পড়েছো? হাহা!",
    "বোরিং লাগছে তো! চলো, গল্প করি।",
]


async def handle_command(command: str):
    # প্রথমে কোনো নির্দিষ্ট স্কিল মেলে কিনা দেখা
    for keywords, skill_fn in SKILLS:
        if any(k in command for k in keywords):
            reply = skill_fn(command)
            await speak(reply)
            return

    # নাহলে সাধারণ কথাবার্তা (Groq AI)
    chat_history.append({"role": "user", "content": command})
    # পুরোনো হিস্টোরি বেশি বড় হলে ছেঁটে ফেলা (মেমোরি/স্পিড ঠিক রাখতে)
    if len(chat_history) > MAX_HISTORY_TURNS * 2:
        del chat_history[1:3]  # system prompt রেখে সবচেয়ে পুরোনো একটা টার্ন বাদ

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=chat_history,
            temperature=0.8,
            max_tokens=150,
        )
        response = completion.choices[0].message.content
        chat_history.append({"role": "assistant", "content": response})
        await speak(response)
    except Exception as e:
        log(f"ERROR: {e}")
        await speak("উফফ, আমার ব্রেইনে একটু সমস্যা হচ্ছে।")


async def main():
    inject_memory_into_prompt()
    await speak("আরে হ্যালো! আমি ইরা, তোমার বেস্ট ফ্রেন্ড। আমি রেডি, বলো কী খবর তোমার?")

    while True:
        raw = listen()

        if raw == "ERROR":
            continue

        if raw == "SILENCE":
            await speak(random.choice(PROACTIVE_MESSAGES))
            continue

        if any(w in raw for w in EXIT_WORDS):
            await speak("আচ্ছা, আমি এখন ঘুমাতে যাচ্ছি! দরকার হলে আবার ডেকো, বাই!")
            break

        # যেকোনো জায়গায় "ইরা" বললেই সাড়া দেবে
        if contains_wake_word(raw):
            command = strip_wake_word(raw)
            if not command:
                await speak("হ্যাঁ বলো, শুনছি!")
                continue
            await handle_command(command)
        else:
            # wake word ছাড়া বললেও সরাসরি রেসপন্স করবে (continuous-chat মোড)
            await handle_command(raw)


if __name__ == "__main__":
    asyncio.run(main())
