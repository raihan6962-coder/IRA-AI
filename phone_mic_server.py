"""
Phone Mic Server for Ira AI
============================
Your phone acts as Ira's microphone over WiFi.
Run this, open the URL on your phone, and talk!
"""

import os
import sys
import re
import json
import base64
import tempfile
import webbrowser
import time
import math
import threading
import socket
from groq import Groq
import speech_recognition as sr
import edge_tts
import pygame
import asyncio
from datetime import datetime

# ====== TRY TO IMPORT FLASK ======
try:
    from flask import Flask, request, jsonify, send_from_directory
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

# ====== LOAD ENV ======
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

# ====== SHARED IRA ENGINE ======
chat_history = []


def log(msg, type_="INFO"):
    t = datetime.now().strftime("%H:%M:%S")
    symbol = {"INFO": "•", "USER": "»", "IRA": "«", "SYS": "◆", "ERR": "✗"}
    s = symbol.get(type_, "•")
    print(f" {t} {s} {msg}")


def get_ira_reply(msg):
    global chat_history
    chat_history.append({"role": "user", "content": msg})
    system = (
        "তুমি ইরা। তুমি আমার বন্ধু। খুব ছোট করে উত্তর দাও, মাত্র ১ লাইন। "
        "সবসময় বাংলায় বলো। স্বাভাবিক, ক্যাজুয়াল টোনে বলো। "
        "প্রতিবার উত্তরের শুরুতে একটি ফিলার শব্দ দাও: আরে, উমম, হাহা, ধুর, আচ্ছা, ওহ।"
    )
    msgs = [{"role": "system", "content": system}]
    msgs.extend(chat_history[-10:])
    try:
        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=msgs,
            max_tokens=80,
            temperature=0.7,
        )
        reply = resp.choices[0].message.content.strip()
        chat_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        log(f"Groq error: {e}", "ERR")
        return "উফ! একটু সমস্যা হচ্ছে। আবার বলো তো?"


def speak(text):
    log(text, "IRA")
    pygame.mixer.init(frequency=22050, size=-16, channels=1)
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
    pygame.mixer.quit()


def process_audio_file(wav_path):
    """Take a WAV file, run STT, get Ira reply, speak it."""
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language="bn-BD").lower().strip()
        log(text, "USER")
    except sr.UnknownValueError:
        try:
            text = recognizer.recognize_google(audio, language="en-US").lower().strip()
            log(text, "USER")
        except:
            return "আমি তোমার কথা শুনতে পাইনি! আরেকটু জোরে বলো!"
    except Exception as e:
        return f"STT error: {e}"

    if not text:
        return "আমি তোমার কথা শুনতে পাইনি! আরেকটু জোরে বলো!"

    found_wake = False
    rest = text
    for w in WAKE_WORDS:
        if w in text:
            idx = text.index(w) + len(w)
            rest = text[idx:].strip().lstrip(" ,!?।")
            found_wake = True
            break

    if not found_wake:
        # Without wake word, still respond (phone mode is always active)
        rest = text

    if not rest:
        return "হুম, বলো! শুনছি!"

    if any(w in rest for w in GOODBYE_WORDS):
        return "__GOODBYE__"

    if any(w in rest for w in SEARCH_YOUTUBE):
        q = rest
        for w in SEARCH_YOUTUBE + ["search", "সার্চ", "খুঁজ"]:
            q = q.replace(w, "")
        q = q.strip()
        if q:
            webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
            return f"ইউটিউবে {q} খুঁজছি!"

    if any(w in rest for w in SEARCH_GOOGLE):
        q = rest
        for w in SEARCH_GOOGLE + ["search", "সার্চ", "খুঁজ"]:
            q = q.replace(w, "")
        q = q.strip()
        if q:
            webbrowser.open(f"https://www.google.com/search?q={q}")
            return f"গুগলে {q} খুঁজছি!"

    return get_ira_reply(rest)


# ====== FLASK WEB SERVER ======
HTML_PAGE = """<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Ira Phone Mic</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:sans-serif;background:#1a1a2e;color:#fff;display:flex;flex-direction:column;align-items:center;min-height:100vh;padding:20px}
h1{color:#0f0;margin:20px 0;font-size:24px}
.status{background:#16213e;padding:15px;border-radius:12px;width:100%;max-width:400px;margin:10px 0;text-align:center;font-size:14px}
.status .dot{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:8px;vertical-align:middle}
.dot.green{background:#0f0;box-shadow:0 0 10px #0f0}
.dot.red{background:#f00;box-shadow:0 0 10px #f00}
.dot.blue{background:#00f;box-shadow:0 0 10px #00f}
.btn{padding:20px;border:none;border-radius:50%;font-size:18px;cursor:pointer;margin:15px;width:80px;height:80px;transition:.3s}
.btn.record{background:#e94560;color:#fff}
.btn.record.recording{background:#f00;animation:pulse 1s infinite}
.btn.send{background:#0f3460;color:#fff;width:auto;border-radius:25px;padding:12px 30px}
@keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.1)}100%{transform:scale(1)}}
.response{background:#16213e;padding:15px;border-radius:12px;width:100%;max-width:400px;margin:10px 0;font-size:16px;line-height:1.6;display:none}
.response.show{display:block}
.hint{color:#888;font-size:12px;margin-top:20px;text-align:center}
#timer{font-size:14px;color:#888;margin:5px 0}
.logo{width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,#0f0,#0ff);margin:10px;animation:glow 2s infinite}
@keyframes glow{0%{box-shadow:0 0 5px #0f0}50%{box-shadow:0 0 20px #0f0}100%{box-shadow:0 0 5px #0f0}}
</style>
</head>
<body>
<div class="logo"></div>
<h1>🗣️ Ira Phone Mic</h1>
<div class="status"><span class="dot green" id="statusDot"></span><span id="statusText">Ready! Press record and talk</span></div>
<div id="timer">00:00</div>
<button class="btn record" id="recordBtn">🎤</button>
<button class="btn send" id="sendBtn" disabled>Send to Ira →</button>
<div class="response" id="responseBox"></div>
<div class="hint">Press 🎤 to record → Press Send → Ira replies on PC!</div>
<script>
let mediaRecorder,audioChunks=[],recording=false,startTime;
const recordBtn=document.getElementById('recordBtn');
const sendBtn=document.getElementById('sendBtn');
const statusText=document.getElementById('statusText');
const statusDot=document.getElementById('statusDot');
const responseBox=document.getElementById('responseBox');
const timer=document.getElementById('timer');

recordBtn.onclick=async()=>{
    if(recording){
        mediaRecorder.stop();
        recording=false;
        recordBtn.classList.remove('recording');
        recordBtn.textContent='🎤';
        statusDot.className='dot green';
        statusText.textContent='Recorded! Press Send →';
        return;
    }
    try{
        const stream=await navigator.mediaDevices.getUserMedia({audio:{
            sampleRate:16000,
            channelCount:1,
            echoCancellation:true,
            noiseSuppression:true
        }});
        mediaRecorder=new MediaRecorder(stream,{mimeType:'audio/webm'});
        audioChunks=[];
        mediaRecorder.ondataavailable=e=>audioChunks.push(e.data);
        mediaRecorder.onstop=()=>{
            stream.getTracks().forEach(t=>t.stop());
            const blob=new Blob(audioChunks,{type:'audio/webm'});
            window._audioBlob=blob;
            sendBtn.disabled=false;
        };
        mediaRecorder.start();
        recording=true;
        recordBtn.classList.add('recording');
        recordBtn.textContent='⏹️';
        statusDot.className='dot red';
        statusText.textContent='Recording... speak now!';
        startTime=Date.now();
        const updateTimer=()=>{
            if(!recording)return;
            const s=Math.floor((Date.now()-startTime)/1000);
            timer.textContent=`00:${s.toString().padStart(2,'0')}`;
            requestAnimationFrame(updateTimer);
        };
        updateTimer();
    }catch(e){
        statusText.textContent='Error: '+e.message;
    }
};

sendBtn.onclick=async()=>{
    const blob=window._audioBlob;
    if(!blob)return;
    sendBtn.disabled=true;
    sendBtn.textContent='Sending...';
    statusDot.className='dot blue';
    statusText.textContent='Ira is thinking...';
    const form=new FormData();
    form.append('audio',blob,'recording.webm');
    try{
        const resp=await fetch('/upload',{method:'POST',body:form});
        const data=await resp.json();
        if(data.reply==='__GOODBYE__'){
            statusText.textContent='Ira went to sleep. Bye!';
            responseBox.textContent='😴 Ira gone to sleep!';
            responseBox.className='response show';
            return;
        }
        statusDot.className='dot green';
        statusText.textContent='Ira replied!';
        responseBox.textContent='🤖 Ira: '+data.reply;
        responseBox.className='response show';
    }catch(e){
        statusText.textContent='Error! Check PC connection';
        responseBox.textContent='❌ Connection error: '+e.message;
        responseBox.className='response show';
    }
    sendBtn.textContent='Send to Ira →';
    sendBtn.disabled=false;
    timer.textContent='00:00';
};
</script>
</body>
</html>"""


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return HTML_PAGE

    @app.route("/upload", methods=["POST"])
    def upload():
        if "audio" not in request.files:
            return jsonify({"error": "No audio file"}), 400
        audio_file = request.files["audio"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            tmp_path = f.name
        try:
            audio_file.save(tmp_path)
            reply = process_audio_file(tmp_path)
            if reply == "__GOODBYE__":
                speak("আচ্ছা, পরে দেখা হবে! বাই বাই!")
                return jsonify({"reply": "__GOODBYE__"})
            speak(reply)
            return jsonify({"reply": reply})
        except Exception as e:
            log(f"Process error: {e}", "ERR")
            return jsonify({"error": str(e)}), 500
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    return app


# ====== FIND LOCAL IP ======
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


# ====== MAIN ======
def main():
    if not HAS_FLASK:
        print("=" * 50)
        print("Flask is required! Install it:")
        print("  pip install flask flask-cors")
        print("=" * 50)
        sys.exit(1)

    ip = get_local_ip()
    port = 5050
    print()
    print("=" * 55)
    print("  🎤 IRA PHONE MIC SERVER")
    print("=" * 55)
    print(f"  📡 Open on your phone browser:")
    print(f"  🌐  http://{ip}:{port}")
    print()
    print(f"  📱 Make sure phone & PC are on the SAME WiFi!")
    print("=" * 55)
    print()

    app = create_app()
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
