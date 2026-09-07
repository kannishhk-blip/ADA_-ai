# Ada — AI Career & Productivity Agent

> [!IMPORTANT]
> **⚡ GLOBAL DESKTOP HOTKEY: `Ctrl + Alt + A`**  
> Press <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>A</kbd> anywhere on Windows to instantly pop open the ADA Assistant floating application window!  
> To enable global listening, run `python -m agents.ada_hotkey` in the background.

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
8. **Ada hotkey** — `ada_hotkey.py` — listens for `Ctrl+Alt+A` to open the app window instantly.

## System Subsystems & Script Reference

| Subsystem / Module | Key Scripts | Capability Proved |
|---|---|---|
| 🔐 **Auth & Config** | `config/google_auth.py` | Google OAuth2 Desktop authentication & session token management |
| 📡 **Job Ingestion & Matching** | `gmail_ingest.py`, `remoteok_ingest.py`, `matching_agent.py` | Fetches inbox alerts & remote listings, scores against resume via local AI embeddings |
| 📅 **Calendar & Planning** | `planning_agent.py`, `meeting_reminder_agent.py` | Auto-schedules application slots on Google Calendar & places phone reminders before meetings |
| 💬 **Comms & Command Layer** | `ada_assistant.py`, `whatsapp_agent.py`, `call_agent.py` | Natural language voice/text commands, Twilio WhatsApp messaging & phone calling |
| 🖥️ **Dashboard & Automation** | `dashboard.py`, `ada_hotkey.py`, `daily_summary.py` | Streamlit web GUI, global `Ctrl+Alt+A` desktop launcher, & daily automated pipeline runner |

## Setup (in order)

1. `pip install -r requirements.txt`
2. Follow the Google Cloud OAuth setup inside `config/google_auth.py`
3. `python config/google_auth.py` (one-time browser login)
4. `python agents/gmail_ingest.py` and `python agents/remoteok_ingest.py` to
   confirm ingestion works
5. `python -m agents.matching_agent` to confirm resume scoring works
6. `python -m agents.planning_agent` to confirm auto-scheduling works
7. `python -m agents.ada_hotkey` to start the global `Ctrl+Alt+A` hotkey listener
8. (Optional) Set up Twilio — see comments in `agents/whatsapp_agent.py` —
   then test `python -m agents.whatsapp_agent` and `python -m agents.call_agent`
9. `python -m agents.ada_assistant` to try natural-language commands
10. `python -m agents.daily_summary` to run the full pipeline in one command

## Never commit these files
Already in `.gitignore`:
```
.env
config/credentials.json
config/token.json
data/*.json
```

## Roadmap status
- [x] Week 1 — Gmail + Calendar OAuth, job ingestion (Gmail + RemoteOK)
- [x] Week 2 — Resume matching via local AI embeddings
- [x] Week 3 — Calendar auto-scheduling, duplicate-safe
- [x] Week 4 — Approval dashboard (Streamlit, auto/manual toggle)
- [x] Week 5 — WhatsApp, calls, meeting reminders, Ada command layer
- [x] Week 6 — Daily summary agent tying everything together
- [x] Week 7 — Global `Ctrl+Alt+A` desktop hotkey floating app launcher
