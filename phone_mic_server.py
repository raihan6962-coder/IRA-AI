"""Ira Phone Mic Server - Auto firewall config + QR code + network test"""

import os, sys, json, socket, tempfile, webbrowser, subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from groq import Groq
import edge_tts
import pygame
import asyncio
from datetime import datetime

load_env = lambda: [exec(open(".env").read())] if os.path.exists(".env") else None

def load_env():
    if os.path.exists(".env"):
        with open(".env", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip("\"'")

load_env()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("API key not found in .env file"); sys.exit(1)

GOODBYE_WORDS = ["sleep","ঘুম","bye","বাই","বিদায়","থাম","stop"]
SEARCH_YOUTUBE = ["youtube","ইউটিউব"]
SEARCH_GOOGLE = ["google","গুগল"]
chat_history = []

def log(msg,t="INFO"):
    s={"INFO":"•","USER":"»","IRA":"«","SYS":"◆","ERR":"✗"}.get(t,"•")
    print(f" {datetime.now().strftime('%H:%M:%S')} {s} {msg}")

def get_reply(msg):
    global chat_history
    chat_history.append({"role":"user","content":msg})
    msgs = [{"role":"system","content":"তুমি ইরা। তুমি আমার বন্ধু। খুব ছোট করে উত্তর দাও, মাত্র ১ লাইন। সবসময় বাংলায় বলো। স্বাভাবিক, ক্যাজুয়াল টোনে বলো। প্রতিবার উত্তরের শুরুতে একটি ফিলার শব্দ দাও: আরে, উমম, হাহা, ধুর, আচ্ছা, ওহ।"}] + chat_history[-10:]
    try:
        r = Groq(api_key=GROQ_API_KEY).chat.completions.create(model="llama-3.1-8b-instant",messages=msgs,max_tokens=80,temperature=0.7)
        reply = r.choices[0].message.content.strip()
        chat_history.append({"role":"assistant","content":reply})
        return reply
    except Exception as e:
        log(f"Groq error: {e}","ERR")
        return "উফ! একটু সমস্যা হচ্ছে। আবার বলো তো?"

def speak(text):
    log(text,"IRA")
    pygame.mixer.init(frequency=22050,size=-16,channels=1)
    with tempfile.NamedTemporaryFile(delete=False,suffix=".mp3") as f:
        p = f.name
    try:
        asyncio.run(edge_tts.Communicate(text,"bn-BD-NabanitaNeural",rate="+0%").save(p))
        pygame.mixer.music.load(p); pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
    except: pass
    finally:
        if os.path.exists(p): os.unlink(p)
    pygame.mixer.quit()

def add_firewall_rule():
    try:
        r = subprocess.run(['netsh','advfirewall','firewall','show','rule','name=all'],capture_output=True,text=True,timeout=5)
        if "Ira Phone Mic" not in r.stdout:
            subprocess.run(['netsh','advfirewall','firewall','add','rule','name=Ira Phone Mic','dir=in','action=allow','protocol=TCP','localport=5050'],capture_output=True,timeout=5)
            return True
    except: pass
    return False

HTML = """<!DOCTYPE html>
<html lang="bn">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<title>Ira Mic</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d0d1a;color:#fff;font-family:sans-serif;text-align:center;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px}
.circle{width:80px;height:80px;border-radius:50%;background:radial-gradient(circle,#0f0,#060);margin:20px;animation:glow 2s infinite}
@keyframes glow{0%{box-shadow:0 0 10px #0f0}50%{box-shadow:0 0 30px #0f0}100%{box-shadow:0 0 10px #0f0}}
h1{color:#0f0;font-size:24px;margin:5px}
.status{background:#1a1a2e;border-radius:12px;padding:18px;margin:10px;width:100%;max-width:360px;font-size:15px;min-height:50px}
.btn{width:110px;height:110px;border-radius:50%;border:none;font-size:44px;cursor:pointer;margin:15px;background:#e94560;color:#fff;transition:.3s;box-shadow:0 0 20px rgba(233,69,96,.5)}
.btn.active{background:#f00;animation:pulse .8s infinite}
@keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.15)}100%{transform:scale(1)}}
.you{color:#0ff;font-size:13px;margin:8px;min-height:20px}
.reply{background:#1a1a2e;border-radius:12px;padding:15px;margin:10px;width:100%;max-width:360px;font-size:15px;line-height:1.6;display:none}
.reply.show{display:block}
</style></head>
<body>
<div class="circle"></div>
<h1>🎙️ Ira</h1>
<div class="status" id="status">Tap 🎤 and speak</div>
<div class="you" id="youText"></div>
<button class="btn" id="btn">🎤</button>
<div class="reply" id="reply"></div>
<script>
const btn=document.getElementById('btn'),st=document.getElementById('status'),rp=document.getElementById('reply'),yt=document.getElementById('youText');
let recOn=false,recog;
if(!('webkitSpeechRecognition'in window)&&!('SpeechRecognition'in window)){st.textContent='❌ Use Chrome browser!';btn.disabled=true}else{
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
recog=new SR();recog.continuous=false;recog.interimResults=true;recog.lang='bn-BD';
recog.onresult=function(e){
let final='';
for(let i=e.resultIndex;i<e.results.length;i++){const t=e.results[i][0].transcript;if(e.results[i].isFinal)final+=t;else st.textContent='🔵 '+t}
if(final){
recOn=false;btn.classList.remove('active');btn.textContent='🎤';
st.textContent='⏳ Sending...';yt.textContent='🗣️ '+final;
fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:final})})
.then(r=>r.json()).then(d=>{
if(d.reply==='__GOODBYE__'){st.textContent='😴 Bye!';rp.textContent='😴 Goodbye!';rp.className='reply show';return}
st.textContent='💬 Ira replied!';rp.textContent='🤖 '+d.reply;rp.className='reply show'
}).catch(e=>{st.textContent='❌ Error!';rp.textContent='❌ '+e.message;rp.className='reply show'})
}};
recog.onerror=function(){recOn=false;btn.classList.remove('active');btn.textContent='🎤';st.textContent='❌ Error. Tap 🎤 again'};
recog.onend=function(){recOn=false;btn.classList.remove('active');btn.textContent='🎤';if(st.textContent.startsWith('🔵'))st.textContent='Tap 🎤 and speak'};
}
btn.onclick=function(){
if(recOn){recog.stop();recOn=false;btn.classList.remove('active');btn.textContent='🎤';st.textContent='Stopped';return}
if(recog){recog.start();recOn=true;btn.classList.add('active');btn.textContent='⏹';st.textContent='🔴 Speak now!';rp.className='reply'}
};
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))
    def do_POST(self):
        if self.path=="/chat":
            try:
                d=json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
                text=d.get("text","").strip().lower()
                log(text,"USER")
                if not text: reply="বলো তো! কিছু বলোনি তো!"
                elif any(w in text for w in GOODBYE_WORDS): reply="__GOODBYE__"
                elif any(w in text for w in SEARCH_YOUTUBE):
                    q = text
                    for w in SEARCH_YOUTUBE + ["search", "সার্চ", "খুঁজ"]: q = q.replace(w, "")
                    q = q.strip()
                    if q: webbrowser.open(f"https://www.youtube.com/results?search_query={q}");reply=f"ইউটিউবে {q} খুঁজছি!"
                    else: reply="কী খুঁজবি বলো!"
                elif any(w in text for w in SEARCH_GOOGLE):
                    q = text
                    for w in SEARCH_GOOGLE + ["search", "সার্চ", "খুঁজ"]: q = q.replace(w, "")
                    q = q.strip()
                    if q: webbrowser.open(f"https://www.google.com/search?q={q}");reply=f"গুগলে {q} খুঁজছি!"
                    else: reply="কী খুঁজবি বলো!"
                else: reply=get_reply(text)
                if reply!="__GOODBYE__": speak(reply)
                self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers()
                self.wfile.write(json.dumps({"reply":reply}).encode("utf-8"))
            except Exception as e: log(f"Error: {e}","ERR"); self.send_response(500); self.send_header("Content-Type","application/json"); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(json.dumps({"error":str(e)}).encode("utf-8"))
    def log_message(self,*a): pass

def get_ip():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try: s.connect(("8.8.8.8",80));ip=s.getsockname()[0]
    except: ip="127.0.0.1"
    finally: s.close();return ip

def main():
    ip=get_ip()
    added=add_firewall_rule()
    print()
    print("="*55)
    print("      🎤 IRA PHONE MIC")
    print("="*55)
    if added: print("  ✅ Firewall rule added for port 5050")
    print()
    print(f"  📱 Open Chrome on your PHONE and type:")
    print(f"     http://{ip}:5050")
    print()
    print("  ⚠️  SAME WiFi te connected kina CHECK koro!")
    print("  ⚠️  Phone e Chrome browser use koro!")
    print()
    print("  🔍 Not working? Try these:")
    print("   1. PC te Windows Firewall disable koro (temporary)")
    print("   2. Phone WiFi te connected ki na check koro")
    print("   3. PC te cmd -> ipconfig -> IPv4 address check koro")
    print("   4. http://<PC_IP>:5050 phone browser e type koro")
    print()
    print("  ⌨️  Still not working? Just type on PC keyboard!")
    print("="*55)
    print()
    s=HTTPServer(("0.0.0.0",5050),Handler)
    try: s.serve_forever()
    except KeyboardInterrupt: s.server_close();print("\nStopped.")

if __name__=="__main__": main()
