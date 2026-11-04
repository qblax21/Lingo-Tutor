"""Serves index.html and forwards /api/* to the local Ollama, so only this one port is exposed.
Listens on localhost and the Tailscale address only (not your regular Wi-Fi/LAN)."""
import json, subprocess, sys, threading, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8000
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


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
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
        if not self.path.startswith("/api/"):
            return self._send(404, b"not found", "text/plain")
        data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
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
