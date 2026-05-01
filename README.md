# Code Review Agent

A production-ready REST API that reviews PR diffs using LLM function calling.
Accepts a code diff, returns structured issues with severity levels and an
overall risk score.

## Architecture
```
POST /api/review
│
▼
FastAPI (main.py)
│  Pydantic validation (size guard, empty check)
▼
reviewer.py
│  Two function calling tools:
│  • flag_issue(line, severity, reason, suggestion)
│  • score_risk(score, summary)
▼
llm_client.py
│  Provider-agnostic — Groq (dev) or OpenAI (prod)
│  Switch via .env only, zero code changes
▼
logger.py
│  Token usage + USD cost per request
▼
Response → structured JSON
```

## Stack

| Layer | Tech |
|-------|------|
| API framework | FastAPI + Pydantic |
| LLM (dev) | Groq — llama-3.3-70b-versatile |
| LLM (prod) | OpenAI — gpt-4o-mini |
| Function calling | OpenAI tool-use spec |
| Containerization | Docker + docker-compose |
| CI | GitHub Actions |

## Why these choices

**FastAPI over Flask** — async-ready for LLM streaming, automatic OpenAPI
docs, Pydantic validation built in. No boilerplate.

**Function calling over prompt parsing** — guaranteed JSON structure, no
regex fragility. The model signals explicitly when it's done calling tools.

**Provider-agnostic client** — Groq is free and fast for development.
OpenAI GPT-4o-mini for production. Switching is two lines in `.env`.

**Size guard before API call** — diffs over 6,000 chars are rejected with
a 422 before touching the LLM. Prevents runaway token costs.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/review` | Submit a PR diff for review |
| GET | `/api/review/{id}` | Retrieve a past review by ID |
| GET | `/api/usage` | Token + cost summary for the session |
| GET | `/api/health` | Health check |

## Cost per review

| Provider | Model | Avg tokens | Est. cost |
|----------|-------|------------|-----------|
| Groq | llama-3.3-70b-versatile | ~750 | $0.00 (free) |
| OpenAI | gpt-4o-mini | ~750 | ~$0.0005 |
| OpenAI | gpt-4o | ~750 | ~$0.008 |

## Run locally

```bash
git clone https://github.com/tfariyah31/ai-code-review-agent
cd ai-code-review-agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for interactive API docs.

## Run with Docker

```bash
docker compose up
```

## Switch to OpenAI

Edit `.env`:

```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```
No code changes required.

