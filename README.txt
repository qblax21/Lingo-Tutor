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
