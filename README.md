# Mini JARVIS 🎙️

A voice-first AI assistant designed to feel like a real cinematic AI. It features an interactive web interface with a custom-built Web Audio API visualizer, PostgreSQL (Supabase) long-term memory persistence, and lightning-fast text-to-speech using ElevenLabs and Groq.

## Features ✨
- **Voice Mode**: A dedicated, distraction-free UI with a real-time audio visualizer that syncs perfectly with JARVIS's voice.
- **Continuous Conversation**: Talk to JARVIS completely hands-free.
- **Contextual Memory**: Powered by Supabase. JARVIS remembers what you said in previous conversations.
- **Ultra-Low Latency**: Uses Groq Whisper (STT) and Groq LLaMA/GPT (LLM) for blazing-fast inference.

## Local Development 💻

### 1. Backend (Python/FastAPI)
The backend manages the database connections, memory, Groq integrations, and the ElevenLabs TTS API.

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

**Environment Variables**:
Create a `.env` file in the `backend/` directory:
```env
GROQ_API_KEY=your_groq_key
TTS_API_KEY=your_elevenlabs_key
DATABASE_URL="postgresql://postgres.xxx:password@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
```

Start the backend:
```bash
python server.py
# (Runs on http://localhost:8000)
```

### 2. Frontend (React/Vite)
The frontend provides the sleek dark-mode UI and Web Audio API graph routing for the visualizer.

```bash
cd frontend
npm install
npm run dev
# (Runs on http://localhost:5173)
```

---

## Deployment Instructions 🚀

### 1. Deploy the Backend (Render)
1. Push this repository to GitHub.
2. Create a new **Web Service** on [Render](https://render.com/).
3. Settings:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables: `GROQ_API_KEY`, `TTS_API_KEY`, and `DATABASE_URL`.
5. Deploy and copy the live URL (e.g., `https://jarvis-backend.onrender.com`).

### 2. Deploy the Frontend (Vercel)
1. Go to [Vercel](https://vercel.com/) and create a **New Project**.
2. Import the same GitHub repository.
3. Settings:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
4. Add Environment Variable:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://jarvis-backend.onrender.com/api` *(Make sure to use your Render URL + /api)*
5. Deploy!
