# Local AI Setup

Local AI is optional. No API keys are required.

Supported local integrations:

- Ollama on `http://127.0.0.1:11434`
- `whisper`, `faster-whisper`, or `whisperx` CLI for transcription
- Local model files in `models/`, `output/models/`, `.ollama/models`, or Hugging Face cache folders

Check status:

```powershell
python render.py model-manager status
python render.py local-ai status
```

When a model is unavailable, the app falls back to deterministic local generation and repair helpers.
