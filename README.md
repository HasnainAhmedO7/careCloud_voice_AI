# CareCloud Voice AI

A patient registration system with two parts: a FastAPI REST backend for managing patient
records, and a LiveKit voice AI agent that lets callers register or update their information
over the phone in a natural conversation.

## Architecture

```
Caller ──(phone)──> LiveKit SIP ──> voice_agent (LiveKit Agent) ──(HTTP)──> app (FastAPI) ──> SQLite/Postgres
```

- **`app/`** — FastAPI backend exposing a patient registration API
- **`voice_agent/`** — LiveKit voice agent that answers inbound calls, collects patient
  details conversationally, and calls the backend API to save/update records

## Backend API (`app/`)

- **Framework**: FastAPI + SQLAlchemy 2.0, SQLite by default (swap via `DATABASE_URL`)
- **Validation**: Pydantic v2 schemas shared between create/update (name format, 10-digit
  US phone normalization, DOB not in the future, US state whitelist, ZIP format)
- **Responses**: every endpoint returns a `{data, error}` envelope
- **Soft deletes**: records are never hard-deleted, only flagged via `deleted_at`

### Endpoints

| Method | Path              | Description                          |
|--------|-------------------|---------------------------------------|
| GET    | `/health`         | Health check                          |
| GET    | `/patients`        | List patients (filter by last name, DOB, phone) |
| GET    | `/patients/{id}`   | Get one patient                       |
| POST   | `/patients`        | Create a patient                      |
| PUT    | `/patients/{id}`   | Update a patient                      |
| DELETE | `/patients/{id}`   | Soft-delete a patient                 |

### Run it

```bash
cd app/..            # repo root
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`. On first run, two demo patients are seeded.

## Voice Agent (`voice_agent/`)

Built on `livekit-agents`, using LiveKit's managed inference for VAD (`silero`) and STT
(`deepgram/nova-3`) and TTS (`cartesia/sonic-3`), with an explicit OpenAI LLM plugin
(`gpt-4o-mini`) for reliable multi-turn tool-calling.

The agent's system prompt drives a natural phone-intake flow: greet the caller, look up
their number for an existing record, collect required fields conversationally, offer
optional fields (insurance, emergency contact), read everything back for confirmation, then
save via the backend API.

### Tools

- `lookup_patient_by_phone` — checks for an existing record by phone number
- `save_new_patient` — creates a new patient record
- `update_existing_patient` — updates a returning caller's record

### Run it

```bash
cd voice_agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in LiveKit + OpenAI credentials
python agent.py start
```

### Telephony setup (LiveKit Cloud)

To receive real phone calls, in LiveKit Cloud (Telephony section):

1. Rent or bring a phone number.
2. Create a SIP dispatch rule targeting `agent_name: telephony_agent` (see
   `dispatch-rule-catchall.json` for reference) and attach it to the number.
3. Make sure the dispatch rule's `room_config.agents[].deployment` matches whatever
   `LIVEKIT_AGENT_DEPLOYMENT` the worker registers with (leave both unset unless you
   specifically need multiple deployment tiers) — a mismatch here silently drops every
   call without any error, since the job never reaches a worker with a different tag.

## Environment variables

**`app/.env`**
| Var | Description |
|---|---|
| `DATABASE_URL` | SQLAlchemy connection string (defaults to local SQLite) |
| `PORT` | Port for uvicorn |

**`voice_agent/.env`**
| Var | Description |
|---|---|
| `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | LiveKit Cloud project credentials |
| `OPENAI_API_KEY` | Used by the explicit OpenAI LLM plugin |
| `API_BASE_URL` | URL of the backend API (default `http://localhost:8000`) |

## Tech stack

- Python, FastAPI, SQLAlchemy 2.0, Pydantic v2
- `livekit-agents`, Deepgram, Cartesia, OpenAI
