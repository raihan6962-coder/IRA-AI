"""
Phone Mic Server for Ira AI
Your phone = Ira's microphone over WiFi.
No Flask needed - uses Python's built-in HTTP server.
"""

import os, sys, json, base64, tempfile, webbrowser, socket, wave
import io
from http.server import HTTPServer, BaseHTTPRequestHandler
from groq import Groq
import speech_recognition as sr
import edge_tts
import pygame
import asyncio
from datetime import datetime
from urllib.parse import urlparse

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
chat_history = []


def log(msg, type_="INFO"):
    t = datetime.now().strftime("%H:%M:%S")
    s = {"INFO": "•", "USER": "»", "IRA": "«", "SYS": "◆", "ERR": "✗"}.get(type_, "•")
    print(f" {t} {s} {msg}")


def get_reply(msg):
    global chat_history
    chat_history.append({"role": "user", "content": msg})
    system = "তুমি ইরা। তুমি আমার বন্ধু। খুব ছোট করে উত্তর দাও, মাত্র ১ লাইন। সবসময় বাংলায় বলো। স্বাভাবিক, ক্যাজুয়াল টোনে বলো। প্রতিবার উত্তরের শুরুতে একটি ফিলার শব্দ দাও: আরে, উমম, হাহা, ধুর, আচ্ছা, ওহ।"
    msgs = [{"role": "system", "content": system}] + chat_history[-10:]
    try:
        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(model="llama-3.1-8b-instant", messages=msgs, max_tokens=80, temperature=0.7)
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
        asyncio.run(edge_tts.Communicate(text, "bn-BD-NabanitaNeural", rate="+0%").save(path))
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
    except Exception as e:
        log(f"Speech error: {e}", "ERR")
    finally:
        if os.path.exists(path): os.unlink(path)
    pygame.mixer.quit()


def process_audio(wav_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        tmp = f.name
        f.write(wav_bytes)
    try:
        r = sr.Recognizer()
        with sr.AudioFile(tmp) as src:
            audio = r.record(src)
        try:
            text = r.recognize_google(audio, language="bn-BD").lower().strip()
        except:
            text = r.recognize_google(audio, language="en-US").lower().strip()
        log(text, "USER")
    except Exception as e:
        return "আমি শুনতে পাইনি! আরেকটু জোরে বলো!"
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

    if not text:
        return "আমি শুনতে পাইনি! আরেকটু জোরে বলো!"

    rest = text
    for w in WAKE_WORDS:
        if w in text:
            idx = text.index(w) + len(w)
            rest = text[idx:].strip().lstrip(" ,!?।")
            break

    if not rest:
        return "হুম, বলো! শুনছি!"

    if any(w in rest for w in GOODBYE_WORDS):
        return "__GOODBYE__"

    if any(w in rest for w in SEARCH_YOUTUBE):
        q = rest
        for w in SEARCH_YOUTUBE + ["search", "সার্চ", "খুঁজ"]: q = q.replace(w, "")
        q = q.strip()
        if q:
            webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
            return f"ইউটিউবে {q} খুঁজছি!"

    if any(w in rest for w in SEARCH_GOOGLE):
        q = rest
        for w in SEARCH_GOOGLE + ["search", "সার্চ", "খুঁজ"]: q = q.replace(w, "")
        q = q.strip()
        if q:
            webbrowser.open(f"https://www.google.com/search?q={q}")
            return f"গুগলে {q} খুঁজছি!"

    return get_reply(rest)


HTML = """<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<title>Ira Phone Mic</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d0d1a;color:#fff;font-family:sans-serif;text-align:center;padding:20px;min-height:100vh;display:flex;flex-direction:column;align-items:center}
.circle{width:80px;height:80px;border-radius:50%;background:radial-gradient(circle,#0f0,#060);margin:25px auto;animation:glow 2s infinite}
@keyframes glow{0%{box-shadow:0 0 10px #0f0}50%{box-shadow:0 0 30px #0f0}100%{box-shadow:0 0 10px #0f0}}
h1{font-size:22px;margin:10px 0;color:#0f0}
.status{background:#1a1a2e;border-radius:10px;padding:12px 20px;margin:10px;font-size:14px;width:100%;max-width:350px}
.rec-btn{width:90px;height:90px;border-radius:50%;border:none;font-size:40px;cursor:pointer;margin:20px;background:#e94560;color:#fff;transition:all .3s;box-shadow:0 0 15px rgba(233,69,96,.5)}
.rec-btn.recording{background:#f00;animation:pulse .8s infinite;box-shadow:0 0 25px #f00}
@keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.12)}100%{transform:scale(1)}}
.send-btn{background:#0f3460;color:#fff;border:none;border-radius:25px;padding:14px 40px;font-size:16px;cursor:pointer;margin:10px;transition:.3s}
.send-btn:disabled{opacity:.4;cursor:default}
.send-btn:not(:disabled):hover{background:#1a5276}
.response{background:#1a1a2e;border-radius:10px;padding:15px;margin:15px;font-size:15px;line-height:1.6;width:100%;max-width:350px;display:none}
.response.show{display:block}
#timer{font-size:13px;color:#888;margin:5px}
.ip{font-size:12px;color:#666;margin-top:20px}
</style>
</head>
<body>
<div class="circle"></div>
<h1>Ira Phone Mic</h1>
<div class="status" id="status">🎤 Press the button & talk</div>
<div id="timer">0s</div>
<button class="rec-btn" id="recBtn">🎤</button>
<button class="send-btn" id="sendBtn" disabled>Send to Ira</button>
<div class="response" id="resp"></div>
<div class="ip" id="ipInfo"></div>
<script>
let recOn=false, startTime, audioCtx, samples=[];
const recBtn=document.getElementById('recBtn');
const sendBtn=document.getElementById('sendBtn');
const status=document.getElementById('status');
const resp=document.getElementById('resp');
const timer=document.getElementById('timer');
const ipInfo=document.getElementById('ipInfo');
ipInfo.textContent='Server: '+window.location.hostname+':'+window.location.port;

function encodeWAV(samples, sr){
    const len=samples.length, buf=new ArrayBuffer(44+len*2);
    const dv=new DataView(buf);
    function wStr(o,s){for(let i=0;i<s.length;i++)dv.setUint8(o+i,s.charCodeAt(i));}
    wStr(0,'RIFF');dv.setUint32(4,36+len*2,true);wStr(8,'WAVE');
    wStr(12,'fmt ');dv.setUint32(16,16,true);dv.setUint16(20,1,true);
    dv.setUint16(22,1,true);dv.setUint32(24,sr,true);dv.setUint32(28,sr*2,true);
    dv.setUint16(32,2,true);dv.setUint16(34,16,true);wStr(36,'data');
    dv.setUint32(40,len*2,true);
    for(let i=0;i<len;i++){
        const s=Math.max(-1,Math.min(1,samples[i]));
        dv.setInt16(44+i*2,s<0?s*0x8000:s*0x7FFF,true);
    }
    return new Blob([buf],{type:'audio/wav'});
}

recBtn.onclick=async()=>{
    if(recOn){
        recOn=false;
        recBtn.classList.remove('recording');
        recBtn.textContent='🎤';
        status.textContent='✅ Recorded! Press "Send to Ira"';
        if(audioCtx)audioCtx.close();
        return;
    }
    try{
        const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}});
        audioCtx=new(window.AudioContext||window.webkitAudioContext)();
        const src=audioCtx.createMediaStreamSource(stream);
        const node=audioCtx.createScriptProcessor(4096,1,1);
        samples=[];
        node.onaudioprocess=e=>{
            const ch=e.inputBuffer.getChannelData(0);
            for(let i=0;i<ch.length;i++)samples.push(ch[i]);
        };
        src.connect(node);node.connect(audioCtx.destination);
        recOn=true;
        recBtn.classList.add('recording');
        recBtn.textContent='⏹';
        status.textContent='🔴 Recording... Speak now!';
        startTime=Date.now();
        function update(){if(!recOn)return;timer.textContent=Math.floor((Date.now()-startTime)/1000)+'s';requestAnimationFrame(update)}
        update();
    }catch(e){status.textContent='❌ Mic error: '+e.message;}
};

sendBtn.onclick=async()=>{
    if(!samples.length)return;
    if(recOn){recOn=false;if(audioCtx)audioCtx.close();recBtn.classList.remove('recording');recBtn.textContent='🎤';}
    sendBtn.disabled=true;sendBtn.textContent='Sending...';
    status.textContent='⏳ Ira is thinking...';
    const wav=encodeWAV(samples,audioCtx?audioCtx.sampleRate:16000);
    const reader=new FileReader();
    reader.onload=async()=>{
        const b64=reader.result.split(',')[1];
        try{
            const r=await fetch('/upload',{
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({audio:b64})
            });
            const d=await r.json();
            if(d.reply==='__GOODBYE__'){status.textContent='😴 Bye!';resp.textContent='😴 Ira gone to sleep!';resp.className='response show';return;}
            status.textContent='💬 Ira replied!';
            resp.textContent='🤖 '+d.reply;
            resp.className='response show';
        }catch(e){status.textContent='❌ Connection error!';resp.textContent='Error: '+e.message;resp.className='response show';}
        sendBtn.textContent='Send to Ira';sendBtn.disabled=false;
        timer.textContent='0s';
    };
    reader.readAsDataURL(wav);
};
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/upload":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))
                wav_bytes = base64.b64decode(data.get("audio", ""))

                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                    tmp = f.name
                    f.write(wav_bytes)

                try:
                    r = sr.Recognizer()
                    with sr.AudioFile(tmp) as src:
                        audio = r.record(src)
                    try:
                        text = r.recognize_google(audio, language="bn-BD").lower().strip()
                    except:
                        text = r.recognize_google(audio, language="en-US").lower().strip()
                    log(text, "USER")
                except Exception as e:
                    text = ""
                    log(f"STT error: {e}", "ERR")
                finally:
                    if os.path.exists(tmp): os.unlink(tmp)

                if not text:
                    reply = "আমি শুনতে পাইনি! আরেকটু জোরে বলো!"
                else:
                    rest = text
                    for w in WAKE_WORDS:
                        if w in text:
                            idx = text.index(w) + len(w)
                            rest = text[idx:].strip().lstrip(" ,!?।")
                            break
                    if not rest:
                        reply = "হুম, বলো!"
                    elif any(w in rest for w in GOODBYE_WORDS):
                        reply = "__GOODBYE__"
                    elif any(w in rest for w in SEARCH_YOUTUBE):
                        q = rest
                        for w in SEARCH_YOUTUBE + ["search", "সার্চ", "খুঁজ"]: q = q.replace(w, "")
                        q = q.strip()
                        if q:
                            webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
                            reply = f"ইউটিউবে {q} খুঁজছি!"
                        else: reply = "কী খুঁজবি বলো!"
                    elif any(w in rest for w in SEARCH_GOOGLE):
                        q = rest
                        for w in SEARCH_GOOGLE + ["search", "সার্চ", "খুঁজ"]: q = q.replace(w, "")
                        q = q.strip()
                        if q:
                            webbrowser.open(f"https://www.google.com/search?q={q}")
                            reply = f"গুগলে {q} খুঁজছি!"
                        else: reply = "কী খুঁজবি বলো!"
                    else:
                        reply = get_reply(rest)

                if reply != "__GOODBYE__":
                    speak(reply)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"reply": reply}).encode("utf-8"))
            except Exception as e:
                log(f"Upload error: {e}", "ERR")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def log_message(self, format, *args):
        pass


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def main():
    ip = get_ip()
    port = 5050
    print()
    print("=" * 55)
    print("          IRA PHONE MIC SERVER")
    print("=" * 55)
    print(f"  Open on your phone browser:")
    print(f"  >>>  http://{ip}:{port}  <<<")
    print()
    print(f"  [i] Phone & PC must be on the same WiFi")
    print(f"  [i] If no sound on PC, check Windows volume")
    print("=" * 55)
    print()

    server = HTTPServer(("0.0.0.0", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
