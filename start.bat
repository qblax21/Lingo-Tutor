@echo off
rem Starts Ollama (if needed) and the Lingo Tutor server, reachable on localhost and over Tailscale.
rem Uses the voice-venv (Whisper + Piper) if it exists, otherwise plain "py" (no local voice).
start "" /min "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
if exist "%~dp0voice-venv\Scripts\python.exe" (
  "%~dp0voice-venv\Scripts\python.exe" "%~dp0server.py"
) else (
  py "%~dp0server.py"
)
pause
