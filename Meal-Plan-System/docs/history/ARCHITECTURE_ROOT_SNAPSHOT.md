# Glocusense Architecture

**Stack:** React frontend + Python FastAPI backend

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React SPA - Vite :5173)             │
│  Landing, Login, Register, Dashboard, Search, Chatbot,           │
│  Recommendations, Glucose Tracking                              │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API (FastAPI - Python :8000)                  │
│  /api/auth (register, login, me)                                 │
│  /api/search, /api/chatbot/message, /api/recommendations          │
│  /api/glucose                                                    │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              SQLite (AppData/Glocusense/glocusense.db)           │
│              ChromaDB (instance/chroma_nutrition) - RAG          │
└─────────────────────────────────────────────────────────────────┘
```

## Run

```bash
# Backend
pip install -r requirements.txt
python run.py

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173
