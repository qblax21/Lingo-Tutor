Lingo Tutor - free, runs on your own PC

1. Install Ollama: https://ollama.com/download (Windows installer).
2. Download a model (your RTX 3060 + 32 GB RAM handles a 7-8B model well). In PowerShell:
     ollama pull qwen2.5:7b
   (Good alternatives: llama3.1:8b, gemma2:9b. Smaller/faster: llama3.2:3b)
3. Allow the page to talk to Ollama. Because index.html opens from a file, Ollama must accept
   any origin. Run once in PowerShell, then fully quit and restart Ollama (tray icon -> Quit):
     setx OLLAMA_ORIGINS "*"
4. Double-click index.html, open Settings, pick "Local model (Ollama)",
   set your language, Save.

Nothing leaves your computer and there is no cost.

--- Local voice (optional, already set up on this PC) ---
Whisper (listening) and Piper (speaking) run from voice-venv, which start.bat uses automatically.
To rebuild it:
  C:\Users\Owner\miniconda3\python.exe -m venv voice-venv
  voice-venv\Scripts\python.exe -m pip install -r requirements-voice.txt
Piper voices go in the voices folder (.onnx + .onnx.json), e.g. de_DE-thorsten-high, pt_PT-tugao-medium.
Download more from https://huggingface.co/rhasspy/piper-voices (the filename starts with the language code,
e.g. fr_FR-..., es_ES-..., it_IT-...). Whisper downloads itself on first use (about 1.6 GB).
Settings > Voice switches back to the browser's built-in voice.
