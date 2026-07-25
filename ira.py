import os
import speech_recognition as sr
import edge_tts
import pygame
import asyncio
from groq import Groq
import webbrowser
import random

# ⚠️ এখানে অবশ্যই আপনার আসল Groq API Key দেবেন, নাহলে Error thinking আসবে!
GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)

# ইরার নতুন বাংলা পার্সোনালিটি
chat_history = [
    {"role": "system", "content": "তোমার নাম ইরা। তুমি একটি খুব মিষ্টি, মজার এবং বন্ধুসুলভ এআই অ্যাসিস্ট্যান্ট। তুমি আমার বেস্ট ফ্রেন্ড। তুমি সবসময় বাংলায় কথা বলবে। একদম সত্যিকারের মানুষের মতো করে কথা বলবে, রোবটের মতো নয়। কথায় ইমোশন রাখবে, মাঝে মাঝে 'হা হা' করে হাসবে, 'উমম', 'আরে', 'আচ্ছা' ইত্যাদি ব্যবহার করবে। উত্তরগুলো ছোট এবং কিউট হবে। আমাকে 'তুমি' বলে ডাকবে।"}
]

async def speak(text):
    print(f"Ira: {text}")
    # bn-BD-NabanitaNeural হলো একদম রিয়েল বাংলাদেশি মেয়ের ভয়েস
    communicate = edge_tts.Communicate(text, 'bn-BD-NabanitaNeural')
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
            # এখন সে বাংলা কথা পরিষ্কার বুঝতে পারবে
            command = r.recognize_google(audio, language="bn-BD").lower()
            print(f"You said: {command}")
            return command
        except sr.WaitTimeoutError:
            return "SILENCE"
        except Exception:
            return "ERROR"

async def main():
    await speak("হ্যালো বস! আমি ইরা, তোমার ভার্চুয়াল বেস্ট ফ্রেন্ড। আমি রেডি, বলো কী খবর?")
    
    while True:
        command = listen()
        
        if command == "ERROR":
            continue
            
        # নিজে থেকে কথা বলা
        if command == "SILENCE":
            proactive_messages = [
                "উমম... এত চুপচাপ কেন? কিছু একটা বলো!",
                "আরে, তুমি কি আছো? নাকি ঘুমিয়ে পড়েছো? হা হা!",
                "বোরিং লাগছে তো! চলো গল্প করি।",
                "হ্যালো! তোমার বেস্ট ফ্রেন্ডকে ভুলে গেলে নাকি?"
            ]
            random_msg = random.choice(proactive_messages)
            await speak(random_msg)
            continue

        # পিসি কন্ট্রোল: ইউটিউব সার্চ
        if "youtube" in command or "ইউটিউব" in command:
            await speak("আচ্ছা, ইউটিউবে খুঁজছি! এক সেকেন্ড...")
            search_query = command.replace("youtube", "").replace("ইউটিউব", "").replace("সার্চ", "").strip()
            webbrowser.open(f"https://www.youtube.com/results?search_query={search_query}")
            continue
            
        # পিসি কন্ট্রোল: গুগল সার্চ
        elif "google" in command or "গুগল" in command:
            await speak("ঠিক আছে, গুগলে সার্চ করছি!")
            search_query = command.replace("google", "").replace("গুগল", "").replace("সার্চ", "").strip()
            webbrowser.open(f"https://www.google.com/search?q={search_query}")
            continue
            
        # পিসি কন্ট্রোল: শাটডাউন বা এক্সিট
        elif "ঘুমাও" in command or "বিদায়" in command or "bye" in command or "sleep" in command:
            await speak("আচ্ছা, আমি এখন ঘুমাতে যাচ্ছি! দরকার হলে আবার ডেকো। বাই!")
            break
            
        # Groq AI এর সাথে মজার কথাবার্তা
        else:
            chat_history.append({"role": "user", "content": command})
            try:
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=chat_history,
                    temperature=0.8, # ইমোশন এবং ক্রিয়েটিভিটি বাড়ানোর জন্য
                    max_tokens=150
                )
                response = completion.choices[0].message.content
                chat_history.append({"role": "assistant", "content": response})
                await speak(response)
            except Exception as e:
                print(f"Error Details: {e}")
                await speak("উফফ, আমার ব্রেইনে একটু সমস্যা হচ্ছে। তুমি কি এপিআই কী (API Key) ঠিকমতো দিয়েছো?")

if __name__ == "__main__":
    asyncio.run(main())
