import os
import speech_recognition as sr
import edge_tts
import pygame
import asyncio
from groq import Groq
import webbrowser
import random

# ⚠️ এখানে অবশ্যই আপনার আসল Groq API Key দিন
GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)

# ইরার পার্সোনালিটি (আড্ডার ভাষায়, ইমোশনসহ)
chat_history = [
    {"role": "system", "content": "তোমার নাম ইরা। তুমি আমার বেস্ট ফ্রেন্ড। তুমি সবসময় বাংলায় কথা বলবে, তবে একদম আড্ডার ভাষায় (Casual/Informal), কোনোভাবেই বইয়ের ভাষায় বা রোবটের মতো নয়। কথা বলার সময় প্রচুর ইমোশন দেখাবে। বাক্যের মাঝে কমা (,) ব্যবহার করবে যাতে গলার স্বরে পজ (pause) আসে এবং রিয়েলিস্টিক শোনায়। মাঝে মাঝে 'আরে!', 'উমম...', 'হাহা', 'ধুর!' এই ধরনের শব্দ ব্যবহার করবে। উত্তর খুব ছোট রাখবে, ১-২ লাইনের মধ্যে।"}
]

async def speak(text):
    print(f"Ira: {text}")
    communicate = edge_tts.Communicate(text, 'bn-BD-NabanitaNeural', rate='+5%')
    await communicate.save("voice.mp3")

    pygame.mixer.init()
    pygame.mixer.music.load("voice.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.quit()
    os.remove("voice.mp3")

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Ira is listening...")
        r.adjust_for_ambient_noise(source)
        try:
            audio = r.listen(source, timeout=15, phrase_time_limit=10)
            command = r.recognize_google(audio, language="bn-BD").lower()
            print(f"You said: {command}")
            return command
        except sr.WaitTimeoutError:
            return "SILENCE"
        except Exception:
            return "ERROR"

async def main():
    await speak("আরে হ্যালো! আমি ইরা, তোমার বেস্ট ফ্রেন্ড। আমি রেডি, বলো কী খবর তোমার?")

    while True:
        command = listen()

        if command == "ERROR":
            continue

        if command == "SILENCE":
            proactive_messages = [
                "উমম..., এত চুপচাপ কেন? কিছু একটা বলো!",
                "আরে, তুমি কি আছো? নাকি ঘুমিয়ে পড়েছো? হাহা!",
                "বোরিং লাগছে তো! চলো, গল্প করি।"
            ]
            random_msg = random.choice(proactive_messages)
            await speak(random_msg)
            continue

        if "youtube" in command or "ইউটিউব" in command:
            await speak("আচ্ছা, ইউটিউবে খুঁজছি! এক সেকেন্ড...")
            search_query = command.replace("youtube", "").replace("ইউটিউব", "").replace("সার্চ", "").strip()
            webbrowser.open(f"https://www.youtube.com/results?search_query={search_query}")
            continue

        elif "google" in command or "গুগল" in command:
            await speak("ঠিক আছে, গুগলে সার্চ করছি!")
            search_query = command.replace("google", "").replace("গুগল", "").replace("সার্চ", "").strip()
            webbrowser.open(f"https://www.google.com/search?q={search_query}")
            continue

        elif "ঘুমাও" in command or "বিদায়" in command or "bye" in command or "sleep" in command:
            await speak("আচ্ছা, আমি এখন ঘুমাতে যাচ্ছি! দরকার হলে আবার ডেকো, বাই!")
            break

        else:
            chat_history.append({"role": "user", "content": command})
            try:
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=chat_history,
                    temperature=0.8,
                    max_tokens=150
                )
                response = completion.choices[0].message.content
                chat_history.append({"role": "assistant", "content": response})
                await speak(response)
            except Exception as e:
                print(f"Error Details: {e}")
                await speak("উফফ, আমার ব্রেইনে একটু সমস্যা হচ্ছে।")

if __name__ == "__main__":
    asyncio.run(main())
