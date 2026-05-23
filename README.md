# NovelSmith

Local-first AI novel writing studio.

See [ROADMAP.md](ROADMAP.md) for the planned Hermes/Codex-style agent direction.

## Run locally

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8765
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Agent provider

The first MVP uses OpenAI-compatible chat completions:

- Base URL: `https://api.openai.com/v1`, `https://api.deepseek.com/v1`, `http://localhost:11434/v1`, etc.
- Model: provider model name.
- API key: stored only in browser local storage and sent to the local backend for each run.

If no key/base URL/model is configured, the backend streams a local demo draft so the UI can be tested offline.
