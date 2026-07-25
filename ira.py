import os
import speech_recognition as sr
import edge_tts
import pygame
import asyncio
from groq import Groq
import webbrowser
import random

# আপনার Groq API Key এখানে দিন (অবশ্যই দেবেন, নাহলে কাজ করবে না)
GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)

chat_history = [
    {"role": "system", "content": "Your name is Ira. You are a highly realistic, funny, sweet, and friendly female AI assistant for my PC. You talk like a real human girl, very casual and friendly. Keep your answers short and to the point. You are my best friend."}
]

async def speak(text):
    print(f"Ira: {text}")
    communicate = edge_tts.Communicate(text, 'en-US-JennyNeural')
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
            # ১৫ সেকেন্ড কোনো কথা না বললে টাইমআউট হয়ে যাবে
            audio = r.listen(source, timeout=15, phrase_time_limit=10)
            command = r.recognize_google(audio).lower()
            print(f"You said: {command}")
            return command
        except sr.WaitTimeoutError:
            return "SILENCE" # চুপ থাকলে এই সিগন্যাল যাবে
        except Exception:
            return "ERROR"

async def main():
    # ১. চালু হওয়ার সাথে সাথে গ্রিটিং (Greeting)
    await speak("Hey boss! I am Ira, your virtual bestie. I am online and ready to rock. What's up?")
    
    while True:
        command = listen()
        
        if command == "ERROR":
            continue
            
        # ২. নিজে থেকে কথা বলা (Proactive Feature)
        if command == "SILENCE":
            proactive_messages = [
                "I am bored! Say something.",
                "Hey, are you still there? I'm missing our chat.",
                "Just checking in! How is your work going?",
                "It's so quiet! Tell me a joke or something.",
                "Hellooo! Don't ignore your bestie!"
            ]
            random_msg = random.choice(proactive_messages)
            await speak(random_msg)
            continue

        # পিসি কন্ট্রোল: ইউটিউব সার্চ
        if "youtube" in command and "search" in command:
            await speak("Sure, searching on YouTube right now!")
            search_query = command.replace("search", "").replace("on youtube", "").replace("youtube", "").strip()
            webbrowser.open(f"https://www.youtube.com/results?search_query={search_query}")
            continue
            
        # পিসি কন্ট্রোল: গুগল সার্চ
        elif "google" in command and "search" in command:
            await speak("Looking it up on Google for you!")
            search_query = command.replace("search", "").replace("on google", "").replace("google", "").strip()
            webbrowser.open(f"https://www.google.com/search?q={search_query}")
            continue
            
        # পিসি কন্ট্রোল: শাটডাউন বা এক্সিট
        elif "go to sleep" in command or "bye" in command:
            await speak("Okay, catching some sleep! Call me if you need anything. Bye!")
            break
            
        # Groq AI এর সাথে কথাবার্তা
        else:
            chat_history.append({"role": "user", "content": command})
            try:
                completion = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=chat_history,
                    temperature=0.7,
                    max_tokens=150
                )
                response = completion.choices[0].message.content
                chat_history.append({"role": "assistant", "content": response})
                await speak(response)
            except Exception as e:
                print("Error thinking...")

if __name__ == "__main__":
    asyncio.run(main())
