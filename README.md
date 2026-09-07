# Ada — AI Career & Productivity Agent

A multi-agent system that finds job postings (via Gmail alerts + RemoteOK),
matches them against your resume using AI embeddings, schedules application
tasks on your calendar, and can send WhatsApp messages / make calls / open
apps on command. Every real-world action is either human-approved or
duplicate-safe by design.

Named after Ada Lovelace, the first computer programmer — fitting for an
agent that follows instructions and takes action on its own.

## Architecture
1. **Ingestion agents** — `gmail_ingest.py` (LinkedIn/Naukri alerts),
   `remoteok_ingest.py` (live job board listings)
2. **Matching agent** — `matching_agent.py` scores each job against your
   resume using local AI embeddings (sentence-transformers, free, no API cost)
3. **Planning agent** — `planning_agent.py` finds free Google Calendar slots
   and auto-schedules application tasks, skipping anything already scheduled
4. **Approval dashboard** — `dashboard.py` (Streamlit) — visual job review,
   with a toggle between fully-automatic and manual tick-to-approve modes
5. **Communication agents** — `whatsapp_agent.py`, `call_agent.py`,
   `meeting_reminder_agent.py` (Twilio) — send messages, place calls, and
   remind you of upcoming meetings by calling your phone
6. **Ada assistant** — `ada_assistant.py` — natural-language command layer
   ("send hi to my gf", "open whatsapp", "call mom") sitting on top of the
   agents above
7. **Daily summary** — `daily_summary.py` — the single command that runs
   the whole pipeline and prints one clean report

## Quick reference

| Script | What it proves |
|---|---|
| `config/google_auth.py` | OAuth works; token is saved for reuse |
| `agents/gmail_ingest.py` | Real job data from your inbox via Gmail API |
| `agents/remoteok_ingest.py` | Real job listings from RemoteOK's public API |
| `agents/matching_agent.py` | Resume-vs-job scoring using local AI embeddings |
| `agents/planning_agent.py` | Auto-schedules to Google Calendar, no duplicates |
| `agents/dashboard.py` | Browser-based review UI (auto or manual mode) |
| `agents/whatsapp_agent.py` | Sends a real WhatsApp message via Twilio |
| `agents/call_agent.py` | Places a real phone call with a spoken message |
| `agents/meeting_reminder_agent.py` | Calls your phone before calendar meetings |
| `agents/ada_assistant.py` | Natural-language command interface |
| `agents/daily_summary.py` | Runs everything, prints one report |

## Setup (in order)

1. `pip install -r requirements.txt`
2. Follow the Google Cloud OAuth setup inside `config/google_auth.py`
3. `python config/google_auth.py` (one-time browser login)
4. `python agents/gmail_ingest.py` and `python agents/remoteok_ingest.py` to
   confirm ingestion works
5. `python -m agents.matching_agent` to confirm resume scoring works
6. `python -m agents.planning_agent` to confirm auto-scheduling works
7. (Optional) Set up Twilio — see comments in `agents/whatsapp_agent.py` —
   then test `python -m agents.whatsapp_agent` and `python -m agents.call_agent`
8. `python -m agents.ada_assistant` to try natural-language commands
9. `python -m agents.daily_summary` to run the full pipeline in one command

## Never commit these files
Already in `.gitignore`:
```
.env
config/credentials.json
config/token.json
```

## Roadmap status
- [x] Week 1 — Gmail + Calendar OAuth, job ingestion (Gmail + RemoteOK)
- [x] Week 2 — Resume matching via local AI embeddings
- [x] Week 3 — Calendar auto-scheduling, duplicate-safe
- [x] Week 4 — Approval dashboard (Streamlit, auto/manual toggle)
- [x] Week 5 — WhatsApp, calls, meeting reminders, Ada command layer
- [x] Week 6 — Daily summary agent tying everything together

## Known limitations / future enhancements
- **Voice input**: built (`voice_ada.py`) but blocked by a `pyaudio` /
  Python 3.14 compatibility issue on this machine. The command-parsing
  logic is identical to the typed version, so voice can be added later
  without touching the core agents.
- **Calling from your own personal number**: not implemented on purpose —
  automating your real WhatsApp/phone risks account bans. Twilio's
  dedicated number is the ToS-compliant approach used here instead.
- **Twilio trial restrictions**: messages/calls only work with numbers
  verified on the Twilio account until you upgrade out of the free trial.

