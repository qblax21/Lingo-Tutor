"""Serves index.html and forwards /api/* to the local Ollama, so only this one port is exposed.
Listens on localhost and the Tailscale address only (not your regular Wi-Fi/LAN)."""
import json, subprocess, sys, threading, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8090
OLLAMA = "http://127.0.0.1:11434"
HTML = Path(__file__).with_name("index.html")
DATA = Path(__file__).with_name("data.json")  # your cards, chat and settings; git-ignored
STATIC = {
    "index.html": "text/html; charset=utf-8",
    "logo.svg": "image/svg+xml",
    "apple-touch-icon.png": "image/png",
    "icon-512.png": "image/png",
    "manifest.webmanifest": "application/manifest+json",
}


# ---- local voice: Whisper (listening) + Piper (speaking). Needs voice-venv; loaded on first use. ----
PREFER = {"pt": "pt_PT"}  # European Portuguese over Brazilian when both are installed
VOICE_DIR = Path(__file__).with_name("voices")
_lock = threading.Lock()
_whisper = None
_piper = {}


ALIASES = {"portugu": "pt", "german": "de", "deutsch": "de", "aleman": "de", "alemao": "de", "spanish": "es",
           "espanol": "es", "castellano": "es", "french": "fr", "francais": "fr", "frances": "fr", "italian": "it",
           "italiano": "it", "japanese": "ja", "nihongo": "ja", "korean": "ko", "chinese": "zh", "mandarin": "zh",
           "russian": "ru", "arabic": "ar", "hindi": "hi", "dutch": "nl", "nederlands": "nl", "turkish": "tr",
           "polish": "pl", "swedish": "sv", "greek": "el", "english": "en"}


def _norm(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).strip().lower()


def iso(lang):
    """'German', 'Europeu Portugues', 'pt-PT', 'Deutsch' ... -> two-letter code (None if unknown)."""
    import re
    s = _norm(lang)
    if re.fullmatch(r"[a-z]{2}([-_][a-z]{2})?", s):
        return s[:2]
    return next((v for k, v in ALIASES.items() if k in s), None)


def _add_cuda_dlls():
    import os, site
    for base in site.getsitepackages():
        for d in (Path(base) / "nvidia").glob("*/bin"):
            os.add_dll_directory(str(d))
            os.environ["PATH"] = str(d) + os.pathsep + os.environ["PATH"]


def transcribe(audio, lang):
    global _whisper
    import io
    with _lock:
        if _whisper is None:
            _add_cuda_dlls()
            from faster_whisper import WhisperModel
            try:
                _whisper = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")
            except Exception as e:
                print("GPU unavailable for Whisper, using CPU:", e, flush=True)
                _whisper = WhisperModel("small", device="cpu", compute_type="int8")
        segs, _ = _whisper.transcribe(io.BytesIO(audio), language=iso(lang), vad_filter=True, beam_size=5)
        return " ".join(s.text.strip() for s in segs).strip()


def synthesize(text, lang):
    import io, wave
    from piper import PiperVoice
    code = iso(lang)
    pref = "pt_BR" if code == "pt" and "braz" in _norm(lang) else PREFER.get(code, "\0")
    models = sorted(VOICE_DIR.glob(f"{code}_*.onnx"), key=lambda p: not p.name.startswith(pref)) if code else []
    if not models:
        raise RuntimeError(f"no Piper voice installed for '{lang}' (put a .onnx voice in the voices folder)")
    with _lock:
        voice = _piper.get(models[0])
        if voice is None:
            voice = _piper[models[0]] = PiperVoice.load(str(models[0]))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            voice.synthesize_wav(text, w)
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/voice":
            import importlib.util as u
            ok = all(u.find_spec(m) for m in ("faster_whisper", "piper")) and any(VOICE_DIR.glob("*.onnx"))
            return self._send(200, json.dumps({"local": bool(ok)}).encode())
        if self.path == "/data":
            return self._send(200, DATA.read_bytes() if DATA.exists() else b"{}")
        name ="index.html" if self.path == "/" else self.path.lstrip("/")
        if name in STATIC and (HTML.parent / name).exists():
            self._send(200, (HTML.parent / name).read_bytes(), STATIC[name])
        else:
            self._send(404, b"not found", "text/plain")

    def do_PUT(self):
        if self.path != "/data":
            return self._send(404, b"not found", "text/plain")
        n = int(self.headers.get("Content-Length", 0))
        if n > 5_000_000:
            return self._send(413, b'{"error":"too large"}')
        body = self.rfile.read(n)
        try:
            json.loads(body)
        except ValueError:
            return self._send(400, b'{"error":"bad json"}')
        tmp = DATA.with_suffix(".tmp")
        tmp.write_bytes(body)
        tmp.replace(DATA)  # atomic, so a crash can't leave half a file
        self._send(200, b"{}")

    def do_POST(self):
        path = urlparse(self.path)
        data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if path.path == "/stt":
            lang = parse_qs(path.query).get("lang", [None])[0]
            try:
                return self._send(200, json.dumps({"text": transcribe(data, lang)}).encode())
            except Exception as e:
                return self._send(503, json.dumps({"error": f"Speech-to-text unavailable: {e}"}).encode())
        if path.path == "/tts":
            try:
                req = json.loads(data)
                return self._send(200, synthesize(req["text"], req.get("lang", "")), "audio/wav")
            except Exception as e:
                return self._send(503, json.dumps({"error": f"Text-to-speech unavailable: {e}"}).encode())
        if not self.path.startswith("/api/"):
            return self._send(404, b"not found", "text/plain")
        req = urllib.request.Request(OLLAMA + self.path, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                self._send(r.status, r.read())
        except urllib.error.HTTPError as e:
            self._send(e.code, e.read())
        except Exception as e:
            self._send(502, ('{"error":"Ollama not reachable: %s"}' % e).encode())

    def log_message(self, *a):
        pass


def tailscale_ip():
    try:
        out = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True).stdout.split()
        return out[0] if out else None
    except Exception:
        return None


if __name__ == "__main__":
    hosts = ["127.0.0.1"]
    ts = tailscale_ip()
    if ts:
        hosts.append(ts)
    servers = [ThreadingHTTPServer((h, PORT), Handler) for h in hosts]
    for s in servers[1:]:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    print("Lingo Tutor running:", ", ".join(f"http://{h}:{PORT}" for h in hosts), flush=True)
    servers[0].serve_forever()
