# Nutrition chatbot: RAG + LLM

The **Nutrition Assistant** uses **chat sessions**: create with `POST /api/chatbot/sessions`, list with `GET /api/chatbot/sessions`, load history with `GET /api/chatbot/sessions/{id}/messages`, delete with `DELETE /api/chatbot/sessions/{id}`. Send turns with `POST /api/chatbot/message` and body `{ "message": "...", "session_id": <id> }`.

The same endpoint can answer using **retrieval-augmented generation**:

1. **Retrieval** — Top matches from a **Chroma** vector index built from your `food_items` table (sentence-transformers `all-MiniLM-L6-v2` by default), **plus** the same hybrid food search used elsewhere (Typesense/SQL + fuzzy) merged into the context.
2. **Generation** — An **LLM** (OpenAI or **Ollama**) answers using only that context for food-specific facts, with a fixed system policy (no diagnosis, concise, no duplicate disclaimer).

If no LLM is configured, behavior falls back to **rule-based** replies, including **separate** handling for **high** vs **low** blood sugar questions (so they are not answered with the same “low-GI foods” list as prevention questions).

When an LLM **is** configured, recent turns loaded from the database (`chat_messages`) are sent as context so **follow-up questions** get answers that match the latest ask (see `CHATBOT_HISTORY_MAX` in `.env`).

## Topic filtering (transformers + classifier; SHAP internal only)

When **`CHATBOT_TOPIC_NLP=true`** (default), the API loads the same **sentence-transformers** model as RAG (`RAG_EMBEDDING_MODEL`) and scores whether the message fits nutrition/diabetes scope (anchor themes + small **logistic regression**). **Off-topic** questions get a **short, plain redirect** only — no SHAP or retrieval dump in the chat response.

**Chat responses are consolidated:** the assistant text plus the usual medical disclaimer — no **“Why this answer”** / evidence / classifier logic in the JSON `response` field.

Linear **SHAP** on the topic classifier logit is still computed in code for possible future logging or tooling; it is **not** appended to user-visible replies. Set **`CHATBOT_TOPIC_NLP=false`** for faster cold-start if you do not need the gate.

## Configure an LLM (pick one)

### OpenAI

```env
OPENAI_API_KEY=sk-...
CHATBOT_MODEL=gpt-4o-mini
```

Optional: `OPENAI_BASE_URL` for Azure OpenAI or other OpenAI-compatible gateways.

### Ollama (local)

```bash
ollama pull llama3.2
```

```env
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
```

Do **not** set `OPENAI_API_KEY` if you want Ollama only (OpenAI is preferred when the key is set).

## Vector index

After foods are seeded, the API runs **`rebuild_rag_index()`** (see `build_rag_store` in `api/utils/seed.py`). Data lives under `instance/chroma_nutrition` (override with `CHROMA_PERSIST_DIR`).

- First run downloads the embedding model (can be slow / large).
- `CHATBOT_USE_LEGACY_ONLY=true` forces the old rule engine even if an LLM is configured.

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| Still rule-based | `OPENAI_API_KEY` or `OLLAMA_HOST` set? Any LLM error in API logs? |
| Empty or weak answers | Chroma populated? (`rebuild` log after seed). Try a food name in the DB. |
| Ollama errors | Model name matches `ollama list`; server on `OLLAMA_HOST`. |
