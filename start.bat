@echo off
rem Starts Ollama (if needed) and the Lingo Tutor server, reachable on localhost and over Tailscale.
start "" /min "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
py "%~dp0server.py"
pause
