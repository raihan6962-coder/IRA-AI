"""Ira Phone Mic - Record audio on phone, PC does speech recognition"""

import os, sys, json, socket, tempfile, webbrowser, base64, struct, subprocess, shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from groq import Groq
import speech_recognition as sr
import wave
import edge_tts
import pygame
import asyncio
from datetime import datetime

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
if not GROQ_API_KEY: print("API key not found in .env file"); sys.exit(1)

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
    except Exception as e: return "উফ! একটু সমস্যা হচ্ছে। আবার বলো তো?"

def speak(text):
    log(text,"IRA")
    pygame.mixer.init(frequency=22050,size=-16,channels=1)
    with tempfile.NamedTemporaryFile(delete=False,suffix=".mp3") as f: p=f.name
    try:
        asyncio.run(edge_tts.Communicate(text,"bn-BD-NabanitaNeural",rate="+0%").save(p))
        pygame.mixer.music.load(p); pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
    except: pass
    finally:
        if os.path.exists(p): os.unlink(p)
    pygame.mixer.quit()

HTML = """<!DOCTYPE html>
<html lang="bn">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<title>Ira Mic</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d0d1a;color:#fff;font-family:sans-serif;text-align:center;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px}
.circle{width:80px;height:80px;border-radius:50%;background:radial-gradient(circle,#0f0,#060);margin:20px;animation:glow 2s infinite}
@keyframes glow{0%{box-shadow:0 0 10px #0f0}50%{box-shadow:0 0 30px #0f0}100%{box-shadow:0 0 10px #0f0}}
h1{color:#0f0;font-size:24px}
.status{background:#1a1a2e;border-radius:12px;padding:18px;margin:10px;width:100%;max-width:360px;font-size:14px;min-height:50px}
.btn{width:120px;height:120px;border-radius:50%;border:none;font-size:50px;cursor:pointer;margin:15px;background:#e94560;color:#fff;transition:.3s;box-shadow:0 0 25px rgba(233,69,96,.5)}
.btn.recording{background:#f00;animation:pulse .8s infinite}
@keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.12)}100%{transform:scale(1)}}
.reply{background:#1a1a2e;border-radius:12px;padding:15px;margin:10px;width:100%;max-width:360px;font-size:15px;line-height:1.6;display:none;min-height:40px}
.reply.show{display:block}
</style></head>
<body>
<div class="circle"></div>
<h1>Ira</h1>
<div class="status" id="status">🔴 Press & hold 🎤 talk, release to send</div>
<button class="btn" id="btn">🎤</button>
<div class="reply" id="reply"></div>
<script>
const btn=document.getElementById('btn'),st=document.getElementById('status'),rp=document.getElementById('reply');
let audioCtx=null,stream=null,samples=[],recording=false,srcNode=null,procNode=null;

// Request mic permission ONCE on page load - keep stream alive
async function init(){
    try{
        stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}});
        audioCtx=new(window.AudioContext||window.webkitAudioContext)();
        st.textContent='✅ Tap 🎤 to start recording';
        btn.disabled=false;
    }catch(e){
        st.textContent='❌ Mic allow koro browser settings e';
        btn.disabled=true;
    }
}
init();

btn.addEventListener('click',toggleRec);

function toggleRec(){
    if(recording){stopRec();}
    else{startRec();}
}

function startRec(){
    if(recording||!stream)return;
    samples=[];
    // Use MediaRecorder (more reliable on mobile)
    try{
        const mediaRec=new MediaRecorder(stream,{mimeType:'audio/webm'});
        mediaRec.ondataavailable=function(e){
            if(e.data.size>0)samples.push(e.data);
        };
        mediaRec.onstop=function(){
            const blob=new Blob(samples,{type:'audio/webm'});
            sendAudio(blob);
        };
        window._mediaRec=mediaRec;
        mediaRec.start(100);
        recording=true;
        btn.classList.add('recording');
        btn.textContent='⏹';
        st.textContent='🔴 Recording... tap ⏹ to stop';
    }catch(e){
        st.textContent='❌ Mic error: '+e.message;
    }
}

function stopRec(){
    if(!recording)return;
    recording=false;
    btn.classList.remove('recording');
    btn.textContent='🎤';
    if(window._mediaRec&&window._mediaRec.state!=='inactive'){
        window._mediaRec.stop();
    }else{
        st.textContent='✅ Tap 🎤 and speak';
    }
}

function sendAudio(blob){
    st.textContent='⏳ Sending...';
    const reader=new FileReader();
    reader.onload=function(){
        const b64=reader.result.split(',')[1];
        fetch('/upload',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({audio:b64,format:'webm'})
        }).then(r=>r.json()).then(d=>{
            if(d.reply==='__GOODBYE__'){st.textContent='😴 Bye!';rp.textContent='😴 Ira: goodbye!';rp.className='reply show';return}
            st.textContent='💬 Ira replied!';rp.textContent='🤖 '+d.reply;rp.className='reply show'
        }).catch(e=>{
            st.textContent='❌ Connection error';rp.textContent='❌ Check PC';rp.className='reply show'
        })
    };
    reader.readAsDataURL(blob);
}

function encodeWAV(samples,sr){
    const len=samples.length,buf=new ArrayBuffer(44+len*2),dv=new DataView(buf);
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
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Cache-Control","no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))
    def do_POST(self):
        if self.path=="/upload":
            try:
                d=json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
                wav_b64=d.get("audio","")
                wav_bytes=base64.b64decode(wav_b64)
                
                fmt=d.get("format","wav")
                
                with tempfile.NamedTemporaryFile(delete=False,suffix="."+fmt) as f:
                    tmp=f.name; f.write(wav_bytes)
                
                if fmt=="webm":
                    wav_tmp=tmp.replace("."+fmt,".wav")
                    converted=False
                    # Try ffmpeg
                    if shutil.which("ffmpeg"):
                        subprocess.run(["ffmpeg","-i",tmp,"-acodec","pcm_s16le","-ar","16000","-ac","1",wav_tmp,"-y"],capture_output=True,timeout=10)
                        if os.path.exists(wav_tmp): converted=True
                    # Try pydub
                    if not converted:
                        try:
                            from pydub import AudioSegment
                            AudioSegment.from_file(tmp).export(wav_tmp,format="wav")
                            converted=True
                        except: pass
                    if converted:
                        os.unlink(tmp)
                        tmp=wav_tmp
                    else:
                        os.unlink(tmp)
                        reply="❌ PC te ffmpeg install nei। `winget install ffmpeg` diye install koro"
                        self.send_response(200)
                        self.send_header("Content-Type","application/json")
                        self.send_header("Access-Control-Allow-Origin","*")
                        self.end_headers()
                        self.wfile.write(json.dumps({"reply":reply}).encode("utf-8"))
                        return
                
                r=sr.Recognizer()
                try:
                    with sr.AudioFile(tmp) as src:
                        audio=r.record(src)
                    try: text=r.recognize_google(audio,language="bn-BD").lower().strip()
                    except: text=r.recognize_google(audio,language="en-US").lower().strip()
                    log(text,"USER")
                except: text=""
                finally:
                    if os.path.exists(tmp): os.unlink(tmp)
                
                if not text: reply="আমি শুনতে পাইনি! আরেকটু জোরে বলো!"
                else:
                    rest=text
                    for w in ["ira","ইরা","আইরা"]:
                        if w in text: idx=text.index(w)+len(w); rest=text[idx:].strip().lstrip(" ,!?।"); break
                    if not rest: reply="হুম, বলো!"
                    elif any(w in rest for w in GOODBYE_WORDS): reply="__GOODBYE__"
                    elif any(w in rest for w in SEARCH_YOUTUBE):
                        q=rest
                        for w in SEARCH_YOUTUBE+["search","সার্চ","খুঁজ"]: q=q.replace(w,"")
                        q=q.strip()
                        if q: webbrowser.open(f"https://www.youtube.com/results?search_query={q}");reply=f"ইউটিউবে {q} খুঁজছি!"
                        else: reply="কী খুঁজবি বলো!"
                    elif any(w in rest for w in SEARCH_GOOGLE):
                        q=rest
                        for w in SEARCH_GOOGLE+["search","সার্চ","খুঁজ"]: q=q.replace(w,"")
                        q=q.strip()
                        if q: webbrowser.open(f"https://www.google.com/search?q={q}");reply=f"গুগলে {q} খুঁজছি!"
                        else: reply="কী খুঁজবি বলো!"
                    else: reply=get_reply(rest)
                
                if reply!="__GOODBYE__": speak(reply)
                
                self.send_response(200)
                self.send_header("Content-Type","application/json")
                self.send_header("Access-Control-Allow-Origin","*")
                self.end_headers()
                self.wfile.write(json.dumps({"reply":reply}).encode("utf-8"))
            except Exception as e:
                log(f"Error: {e}","ERR")
                self.send_response(500)
                self.send_header("Content-Type","application/json")
                self.send_header("Access-Control-Allow-Origin","*")
                self.end_headers()
                self.wfile.write(json.dumps({"error":str(e)}).encode("utf-8"))
    def log_message(self,*a): pass

def get_ip():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try: s.connect(("8.8.8.8",80));ip=s.getsockname()[0]
    except: ip="127.0.0.1"
    finally: s.close();return ip

def main():
    ip=get_ip()
    print()
    print("="*55)
    print("      🎤 IRA PHONE MIC")
    print("="*55)
    print(f"  🌐 {ip}:5050")
    print()
    print("  📱 Phone Chrome browser e http://{ip}:5050 open koro")
    print("  🎤 Press & hold 🎤 -> talk -> release")
    print("  PC will hear you and Ira will reply!")
    print("="*55)
    print()
    s=HTTPServer(("0.0.0.0",5050),Handler)
    try: s.serve_forever()
    except KeyboardInterrupt: s.server_close()

if __name__=="__main__": main()
