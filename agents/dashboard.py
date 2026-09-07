"""
ADA Agent — AI career assistant dashboard.

Clean, professional SaaS dashboard UI for job matching, calendar scheduling, and AI agent commands.
Run:  streamlit run agents/dashboard.py
"""

from __future__ import annotations

import contextlib
import io
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.activity_tracker import get_today_stats, record_calendar_scheduled
from agents.ada_assistant import APPS_PATH, CONTACTS_PATH, load_apps, load_contacts, process_command
from agents.daily_summary import build_daily_summary
from agents.job_pipeline import (
    run_full_pipeline,
    run_gmail_pipeline,
    run_remoteok_pipeline,
    schedule_jobs,
)
from agents.planning_agent import LOOK_AHEAD_DAYS, get_already_scheduled_titles
from config.google_auth import get_calendar_service

# ---------------------------------------------------------------------------
# Page + Theme (Linear / Vercel Dark SaaS Aesthetic)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ADA Agent — AI Career Platform",
    layout="wide",
    page_icon="🤖",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@500;600;700;800&display=swap');

:root {
    --ada-bg: #090A0F;
    --ada-surface: #11131C;
    --ada-surface-hover: #181B28;
    --ada-border: #1E2232;
    --ada-border-light: #2A3046;
    --ada-text-main: #F3F4F8;
    --ada-text-muted: #8E95AA;
    --ada-text-dim: #5E657B;
    --ada-primary: #6C5CE7;
    --ada-primary-soft: rgba(108, 92, 231, 0.15);
    --ada-accent: #00D2D3;
    --ada-success: #10B981;
    --ada-gradient: linear-gradient(135deg, #6C5CE7 0%, #00D2D3 100%);
}

/* App Background & Scrollbars */
[data-testid="stAppViewContainer"] { background: var(--ada-bg); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { display: none; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--ada-bg); }
::-webkit-scrollbar-thumb { background: var(--ada-border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--ada-primary); }

/* Typography */
html, body, [class*="css"] {
    color: var(--ada-text-main);
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
}
h1, h2, h3, h4 {
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: -0.02em;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: #0C0D14 !important;
    border-right: 1px solid var(--ada-border) !important;
    padding-top: 1rem;
}
[data-testid="stSidebar"] .stMarkdown p { color: var(--ada-text-muted) !important; }
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--ada-gradient) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 14px rgba(108, 92, 231, 0.3) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background: transparent !important;
    color: #C5CBE0 !important;
    border: none !important;
    text-align: left !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    padding: 0.6rem 0.85rem !important;
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
    background: var(--ada-surface-hover) !important;
    color: #fff !important;
}

/* Header & Brand */
.brand-title {
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 1.4rem;
    background: var(--ada-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.brand-status {
    font-size: 0.75rem;
    color: var(--ada-text-muted);
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 0.2rem;
}
.status-dot {
    width: 7px; height: 7px;
    background: var(--ada-success);
    border-radius: 50%;
    box-shadow: 0 0 8px var(--ada-success);
}

/* Content Layout Containers */
.main-content {
    max-width: 1200px;
    margin: 0 auto;
    padding-bottom: 3rem;
}

.hero-banner {
    background: linear-gradient(135deg, #131522 0%, #0F101A 100%);
    border: 1px solid var(--ada-border);
    border-radius: 20px;
    padding: 2rem 2.25rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 300px; height: 100%;
    background: radial-gradient(circle at 100% 0%, rgba(108, 92, 231, 0.12) 0%, transparent 70%);
    pointer-events: none;
}
.hero-headline {
    font-size: 2.1rem;
    font-weight: 800;
    color: var(--ada-text-main);
    margin: 0 0 0.5rem 0;
}
.hero-subtext {
    color: var(--ada-text-muted);
    font-size: 0.98rem;
    line-height: 1.6;
    margin: 0;
    max-width: 720px;
}

/* Metric KPI Cards */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.25rem;
    margin-bottom: 2rem;
}
.kpi-card {
    background: var(--ada-surface);
    border: 1px solid var(--ada-border);
    border-radius: 16px;
    padding: 1.25rem 1.4rem;
    transition: all 0.2s ease;
}
.kpi-card:hover {
    border-color: var(--ada-border-light);
    transform: translateY(-2px);
}
.kpi-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: var(--ada-text-muted);
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.kpi-value {
    font-family: 'Outfit', sans-serif;
    font-size: 2.1rem;
    font-weight: 800;
    color: var(--ada-text-main);
    margin-top: 0.4rem;
    line-height: 1;
}

/* Section Header */
.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 1.75rem 0 1rem 0;
}
.section-title-text {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--ada-text-main);
}
.section-caption {
    font-size: 0.85rem;
    color: var(--ada-text-muted);
}

/* Action Button Grid Fix */
.main-content div[data-testid="column"] .stButton > button {
    background: var(--ada-surface) !important;
    color: var(--ada-text-main) !important;
    border: 1px solid var(--ada-border) !important;
    border-radius: 14px !important;
    min-height: 70px !important;
    white-space: pre-line !important;
    text-align: left !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    line-height: 1.4 !important;
    padding: 1rem 1.1rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
}
.main-content div[data-testid="column"] .stButton > button:hover {
    border-color: var(--ada-primary) !important;
    background: var(--ada-surface-hover) !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(108, 92, 231, 0.2) !important;
}

/* Job Feed Card Container */
.job-feed-container {
    background: var(--ada-surface);
    border: 1px solid var(--ada-border);
    border-radius: 18px;
    padding: 1.25rem;
}
.job-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    border-bottom: 1px solid var(--ada-border);
    transition: background 0.15s ease;
    border-radius: 12px;
}
.job-row:last-child { border-bottom: none; }
.job-row:hover { background: var(--ada-surface-hover); }
.job-title-text { font-weight: 600; font-size: 0.95rem; color: var(--ada-text-main); }
.job-source-tag { font-size: 0.8rem; color: var(--ada-text-muted); margin-top: 0.2rem; }
.score-badge {
    background: rgba(108, 92, 231, 0.15);
    color: var(--ada-primary);
    border: 1px solid rgba(108, 92, 231, 0.3);
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
    font-size: 0.88rem;
}

/* Hotkey Footer Badge */
.shortcut-badge {
    background: #141622;
    border: 1px solid var(--ada-border);
    border-radius: 12px;
    padding: 0.75rem 1.25rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.75rem;
    font-size: 0.88rem;
    color: var(--ada-text-muted);
}
kbd {
    background: #1E2232;
    border: 1px solid #2E354B;
    border-radius: 5px;
    color: var(--ada-accent);
    font-family: monospace;
    font-weight: 700;
    padding: 3px 6px;
    font-size: 0.8em;
}

div[data-testid="stTextInput"] input {
    background: var(--ada-surface) !important;
    color: var(--ada-text-main) !important;
    border: 1px solid var(--ada-border) !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
}
div[data-testid="stTextInput"] input::placeholder { color: var(--ada-text-dim) !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session State
# ---------------------------------------------------------------------------
if "ada_page" not in st.session_state:
    st.session_state.ada_page = "home"
if "ranked_jobs" not in st.session_state:
    st.session_state.ranked_jobs = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "daily_summary" not in st.session_state:
    st.session_state.daily_summary = None
if "last_cmd_output" not in st.session_state:
    st.session_state.last_cmd_output = None


def cmd_button(icon: str, title: str, subtitle: str, key: str) -> bool:
    return st.button(f"{icon}  {title}\n{subtitle}", key=key, use_container_width=True)


def apply_result(result: dict | None) -> None:
    if not result:
        st.error("Something went wrong. Check your Google credentials and resume.txt.")
        return
    st.session_state.last_result = result
    st.session_state.ranked_jobs = result.get("ranked_jobs", [])


def run_google_action(label: str, func):
    """Run action safely with user-friendly error messages."""
    try:
        return func()
    except Exception as exc:
        text = str(exc)
        if "invalid_grant" in text or "RefreshError" in type(exc).__name__:
            st.error("Google authentication expired. Please run `python config\\google_auth.py` in your terminal.")
            return None
        st.error(f"{label} failed: {exc}")
        return None


def render_result_banner() -> None:
    result = st.session_state.last_result
    if not result:
        return
    scheduled = result.get("scheduled", [])
    st.markdown(
        f'<div style="background:var(--ada-primary-soft); border:1px solid var(--ada-primary); border-radius:12px; padding:1rem 1.25rem; margin-bottom:1.5rem; color:var(--ada-text-main);">'
        f'✅ <b>{result.get("message", "Done.")}</b>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if scheduled:
        for item in scheduled:
            job = item.get("job", {})
            link = job.get("link", "")
            cal = item.get("calendar_link", "")
            start = item.get("start")
            when = start.strftime("%a %d %b, %I:%M %p") if isinstance(start, datetime) else ""
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.markdown(f"**{job.get('title', 'Job')}**  \n*{when}*")
            with cols[1]:
                if link:
                    st.link_button("View posting", link, use_container_width=True)
            with cols[2]:
                if cal:
                    st.link_button("Google Calendar", cal, use_container_width=True)


# ---------------------------------------------------------------------------
# Sidebar Navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="brand-title">🤖 ADA Agent</div>'
        '<div class="brand-status"><span class="status-dot"></span> System Online & Monitoring</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<span style='font-size:0.75rem; font-weight:700; color:var(--ada-text-dim); uppercase; letter-spacing:0.06em;'>MATCHING CONTROLS</span>", unsafe_allow_html=True)
    auto_min_score = st.slider("Minimum Match Threshold", 0, 100, 50, help="Only jobs matching above this percentage will be auto-scheduled.")
    auto_top_n = st.slider("Max Application Slots", 1, 10, 3, help="Maximum number of calendar events to create per scan run.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<span style='font-size:0.75rem; font-weight:700; color:var(--ada-text-dim); uppercase; letter-spacing:0.06em;'>NAVIGATION</span>", unsafe_allow_html=True)

    nav = [
        ("🏠  Overview", "home"),
        ("🗣️  Talk to Ada", "talk"),
        ("✨  Job Matches", "matches"),
        ("📅  Calendar Sync", "calendar"),
        ("📊  Daily Report", "summary"),
    ]
    for label, key in nav:
        btn_type = "primary" if st.session_state.ada_page == key else "secondary"
        if st.button(label, key=f"nav_{key}", use_container_width=True, type=btn_type):
            st.session_state.ada_page = key
            if key == "summary":
                with st.spinner("Compiling today's performance report..."):
                    st.session_state.daily_summary = build_daily_summary(min_score=auto_min_score)
            st.rerun()

    st.markdown("<hr style='border-color:var(--ada-border); margin: 1.5rem 0;'>", unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:0.78rem; color:var(--ada-text-muted); line-height:1.5;">'
        '⚡ <b>Desktop Launcher</b><br>'
        'Press <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>A</kbd> anywhere on Windows to launch ADA.'
        '</div>',
        unsafe_allow_html=True,
    )

stats = get_today_stats()
ranked_jobs = st.session_state.ranked_jobs
search = st.session_state.get("job_search_query", "")

if search:
    q = search.lower()
    ranked_jobs = [j for j in ranked_jobs if q in j.get("title", "").lower() or q in j.get("source", "").lower()]


# ---------------------------------------------------------------------------
# Navigation Bar Component
# ---------------------------------------------------------------------------
def render_navigation() -> None:
    top_nav = [
        ("🏠 Overview", "home"),
        ("🗣️ Talk to Ada", "talk"),
        ("✨ Job Matches", "matches"),
        ("📅 Calendar Sync", "calendar"),
        ("📊 Daily Report", "summary"),
    ]
    nav_cols = st.columns(len(top_nav))
    for (label, key), col in zip(top_nav, nav_cols):
        with col:
            btn_type = "primary" if st.session_state.ada_page == key else "secondary"
            if st.button(label, key=f"topnav_{key}", use_container_width=True, type=btn_type):
                st.session_state.ada_page = key
                if key == "summary":
                    with st.spinner("Compiling today's performance report..."):
                        st.session_state.daily_summary = build_daily_summary(min_score=auto_min_score)
                st.rerun()


if st.session_state.ada_page != "home":
    render_navigation()

# ---------------------------------------------------------------------------
# Main Content Area
# ---------------------------------------------------------------------------
st.markdown('<div class="main-content">', unsafe_allow_html=True)

if st.session_state.ada_page == "home":
    # 1. Hero Section
    st.markdown(
        """
        <div class="hero-banner">
            <div class="hero-headline">Autonomous AI Career Assistant</div>
            <p class="hero-subtext">Ada parses Gmail job alerts & RemoteOK listings, computes semantic AI embeddings against your resume, and schedules application time blocks directly onto Google Calendar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Key Metrics Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-header"><span>Gmail Matches</span><span>📧</span></div>'
            f'<div class="kpi-value">{stats["gmail_matches"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-header"><span>Calendar Today</span><span>📅</span></div>'
            f'<div class="kpi-value">{stats["calendar_added"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-header"><span>Fresh Postings</span><span>🆕</span></div>'
            f'<div class="kpi-value">{stats["fresh_jobs"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-header"><span>Total Loaded</span><span>🎯</span></div>'
            f'<div class="kpi-value">{len(st.session_state.ranked_jobs)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # 3. Quick Actions Grid (Clean, spacious 2x3 layout)
    st.markdown('<div class="section-header"><div class="section-title-text">Pipeline Control Actions</div><div class="section-caption">Execute tasks individually or run the full pipeline</div></div>', unsafe_allow_html=True)
    
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        if cmd_button("📧", "Scan Gmail Alerts", "Check inbox for LinkedIn & Naukri emails", "qa_gmail"):
            with st.spinner("Checking Gmail inbox for job alerts..."):
                apply_result(run_google_action("Scan Gmail", lambda: run_gmail_pipeline(min_score=auto_min_score, top_n=auto_top_n)))
    with qa2:
        if cmd_button("🌐", "Scan RemoteOK", "Fetch live remote developer listings", "qa_remoteok"):
            with st.spinner("Fetching RemoteOK listings..."):
                apply_result(run_google_action("Scan RemoteOK", lambda: run_remoteok_pipeline(min_score=auto_min_score, top_n=auto_top_n)))
    with qa3:
        if cmd_button("📅", "Auto Schedule", "Sync top matched jobs to Calendar", "qa_schedule"):
            with st.spinner("Scheduling top matches to Calendar..."):
                if st.session_state.ranked_jobs:
                    scheduled = schedule_jobs(st.session_state.ranked_jobs, min_score=auto_min_score, top_n=auto_top_n)
                    done = [s for s in scheduled if s.get("status") == "scheduled"]
                    record_calendar_scheduled(len(done))
                    apply_result({
                        "source": "Calendar",
                        "found": len(st.session_state.ranked_jobs),
                        "ranked_jobs": st.session_state.ranked_jobs,
                        "scheduled": done,
                        "message": f"Scheduled {len(done)} top match(es) on your Google Calendar.",
                    })
                else:
                    apply_result(run_google_action("Auto Schedule", lambda: run_full_pipeline(min_score=auto_min_score, top_n=auto_top_n)))

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    qa4, qa5, qa6 = st.columns(3)
    with qa4:
        if cmd_button("🔍", "Run Full Pipeline", "Fetch all sources + auto schedule", "qa_full"):
            with st.spinner("Running full ingestion & scheduling pipeline..."):
                apply_result(run_google_action("Full Pipeline", lambda: run_full_pipeline(min_score=auto_min_score, top_n=auto_top_n)))
    with qa5:
        if cmd_button("📊", "Daily Summary", "View today's activity log & metrics", "qa_summary"):
            with st.spinner("Compiling report..."):
                st.session_state.daily_summary = build_daily_summary(min_score=auto_min_score)
            st.session_state.ada_page = "summary"
            st.rerun()
    with qa6:
        if cmd_button("💬", "WhatsApp Dispatch", "Send daily update to your phone", "qa_wa"):
            try:
                from agents.whatsapp_agent import MY_PHONE_NUMBER, send_whatsapp_message
                summary = build_daily_summary(min_score=auto_min_score)
                send_whatsapp_message(MY_PHONE_NUMBER, summary["summary_text"])
                st.success("Summary sent via WhatsApp!")
            except Exception as exc:
                st.info(f"WhatsApp configuration notice: {exc}")

    st.markdown("<br>", unsafe_allow_html=True)
    render_result_banner()

    # 4. Filter & Job Feed Section
    st.markdown('<div class="section-header"><div class="section-title-text">Ranked Job Feed</div><div class="section-caption">Scored locally using sentence embeddings</div></div>', unsafe_allow_html=True)

    st.text_input("Filter job postings", placeholder="Search by job title, company, or tech stack...", label_visibility="collapsed", key="job_search_query")
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    feed = st.session_state.ranked_jobs
    if search:
        feed = ranked_jobs

    if not feed:
        st.markdown(
            '<div style="background:var(--ada-surface); border:1px solid var(--ada-border); border-radius:16px; padding:2rem; text-align:center; color:var(--ada-text-muted);">'
            'No jobs loaded yet. Click <b>Scan Gmail Alerts</b> or <b>Scan RemoteOK</b> above to start.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for job in feed[:10]:
            link = job.get("link", "")
            score = job.get("match_score", "—")
            st.markdown(
                f'<div class="job-row">'
                f'<div>'
                f'<div class="job-title-text">{job["title"]}</div>'
                f'<div class="job-source-tag">{job.get("source","")}</div>'
                f'</div>'
                f'<div style="display:flex; align-items:center; gap:1rem;">'
                f'<span class="score-badge">{score}% Match</span>'
                f'{f"<a href=\'{link}\' target=\'_blank\' style=\'color:var(--ada-primary); font-size:0.85rem; font-weight:600; text-decoration:none;\'>Open Posting →</a>" if link else ""}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------------------
# Talk to Ada Assistant Page
# ---------------------------------------------------------------------------
elif st.session_state.ada_page == "talk":
    st.markdown(
        """
        <div class="hero-banner">
            <div class="hero-headline">🗣️ ADA Voice & Command Center</div>
            <p class="hero-subtext">Execute natural language instructions to launch desktop apps, open websites, dispatch WhatsApp messages, or trigger phone call reminders.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="background:var(--ada-surface); border:1px solid var(--ada-border); border-radius:18px; padding:1.75rem; margin-bottom:1.5rem;">', unsafe_allow_html=True)
    st.markdown("<span style='font-size:0.9rem; font-weight:700; color:var(--ada-text-main);'>Enter Command</span>", unsafe_allow_html=True)
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    
    cmd_col, btn_col = st.columns([5, 1])
    with cmd_col:
        ada_command = st.text_input(
            "Ada command input", placeholder="e.g. open insta, send hi to my gf, call mom, open youtube",
            label_visibility="collapsed", key="ada_talk_command_input",
        )
    with btn_col:
        run_clicked = st.button("Execute", type="primary", use_container_width=True)

    st.markdown("<div style='margin-top:1rem; font-size:0.82rem; color:var(--ada-text-muted); font-weight:600;'>QUICK SHORTCUTS:</div>", unsafe_allow_html=True)
    preset_cols = st.columns(6)
    presets = [
        ("🌐 LinkedIn", "open linkedin"),
        ("📧 Gmail", "open gmail"),
        ("📅 Calendar", "open calendar"),
        ("▶️ YouTube", "open youtube"),
        ("💬 WhatsApp", "send hi to my gf"),
        ("📞 Call Contact", "call mom"),
    ]
    for (label, cmd_text), col in zip(presets, preset_cols):
        with col:
            if st.button(label, key=f"preset_{hash(cmd_text)}", use_container_width=True):
                ada_command = cmd_text
                run_clicked = True

    if run_clicked and ada_command:
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                process_command(ada_command)
            res_text = output.getvalue().strip() or "Command executed successfully."
            st.session_state.last_cmd_output = ("success", res_text)
        except Exception as e:
            st.session_state.last_cmd_output = ("error", f"Execution failed: {e}")

    if st.session_state.last_cmd_output:
        status_type, msg = st.session_state.last_cmd_output
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        if status_type == "success":
            st.success(f"**Ada Assistant Response:**\n\n{msg}")
        else:
            st.error(msg)
    st.markdown("</div>", unsafe_allow_html=True)

    col_info_a, col_info_b = st.columns(2)
    with col_info_a:
        st.markdown('<div class="section-title-text" style="margin-bottom:0.75rem;">Configured Desktop Apps</div>', unsafe_allow_html=True)
        st.markdown('<div style="background:var(--ada-surface); border:1px solid var(--ada-border); border-radius:16px; padding:1.25rem;">', unsafe_allow_html=True)
        try:
            apps = load_apps()
            for app_name, info in apps.items():
                target = info.get("target", "")
                st.markdown(f"• **{app_name.capitalize()}** — `{target}`")
        except Exception:
            st.caption("No custom apps configured yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_info_b:
        st.markdown('<div class="section-title-text" style="margin-bottom:0.75rem;">Configured Phone Contacts</div>', unsafe_allow_html=True)
        st.markdown('<div style="background:var(--ada-surface); border:1px solid var(--ada-border); border-radius:16px; padding:1.25rem;">', unsafe_allow_html=True)
        try:
            contacts = load_contacts()
            for nickname, phone in contacts.items():
                st.markdown(f"• **{nickname.capitalize()}** — `{phone}`")
        except Exception:
            st.caption("No contacts configured yet.")
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Job Matches Page
# ---------------------------------------------------------------------------
elif st.session_state.ada_page == "matches":
    st.markdown('<div class="section-header"><div class="section-title-text">✨ Ranked Job Matches</div></div>', unsafe_allow_html=True)
    render_result_banner()
    jobs = ranked_jobs if search else st.session_state.ranked_jobs
    if not jobs:
        st.info("No jobs loaded yet. Return to Overview and click Scan Gmail or Scan RemoteOK.")
    else:
        for job in jobs:
            cols = st.columns([4, 1, 1])
            with cols[0]:
                st.markdown(f"**{job.get('match_score','—')}% Match** · {job['title']}  \n*{job.get('source','')}*")
            with cols[1]:
                if job.get("link"):
                    st.link_button("View Job", job["link"], use_container_width=True)
            with cols[2]:
                if st.button("📅 Add Slot", key=f"cal_{hash(job['title'])}"):
                    with st.spinner("Scheduling event..."):
                        scheduled = schedule_jobs([job], min_score=0, top_n=1)
                        if scheduled:
                            record_calendar_scheduled(1)
                            st.success("Scheduled on Google Calendar!")
                        else:
                            st.info("Already on calendar or no open slot.")

# ---------------------------------------------------------------------------
# Calendar Sync Page
# ---------------------------------------------------------------------------
elif st.session_state.ada_page == "calendar":
    st.markdown('<div class="section-header"><div class="section-title-text">📅 Google Calendar Sync</div></div>', unsafe_allow_html=True)
    try:
        cal = get_calendar_service()
        already = get_already_scheduled_titles(cal, LOOK_AHEAD_DAYS)
    except Exception:
        already = set()
        cal = None

    jobs = st.session_state.ranked_jobs
    if not jobs:
        st.info("No jobs loaded. Scan jobs from Overview first.")
    else:
        for job in jobs:
            tag = "✅ Scheduled on Calendar" if job["title"] in already else "⏳ Open for scheduling"
            st.markdown(f"**{job.get('match_score','—')}% Match** · {job['title']} — *{tag}*")
            if job.get("link"):
                st.link_button("Open job link", job["link"], key=f"link_{hash(job['title'])}")

    if cal and jobs:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Auto Schedule All Top Matches", type="primary"):
            with st.spinner("Finding open time slots and scheduling..."):
                scheduled = schedule_jobs(jobs, min_score=auto_min_score, top_n=auto_top_n)
                done = [s for s in scheduled if s.get("status") == "scheduled"]
                record_calendar_scheduled(len(done))
                st.session_state.last_result = {
                    "source": "Calendar",
                    "found": len(jobs),
                    "ranked_jobs": jobs,
                    "scheduled": done,
                    "message": f"Successfully scheduled {len(done)} job application events.",
                }
                st.rerun()

# ---------------------------------------------------------------------------
# Daily Summary Page
# ---------------------------------------------------------------------------
elif st.session_state.ada_page == "summary":
    if st.session_state.daily_summary is None:
        with st.spinner("Compiling today's performance report..."):
            st.session_state.daily_summary = build_daily_summary(min_score=auto_min_score)

    s = st.session_state.daily_summary
    st.markdown(
        f"""
        <div class="hero-banner">
            <div class="hero-headline">📊 Daily Performance Summary</div>
            <p class="hero-subtext">{s['date_label']} — Complete report of agent activities and matches</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-header"><span>Gmail Alerts</span><span>📧</span></div>'
            f'<div class="kpi-value">{s["gmail_alerts_today"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-header"><span>Matches Scored</span><span>✅</span></div>'
            f'<div class="kpi-value">{s["gmail_matches_today"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-header"><span>Calendar Added</span><span>📅</span></div>'
            f'<div class="kpi-value">{s["calendar_added_today"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-header"><span>Fresh Postings</span><span>🆕</span></div>'
            f'<div class="kpi-value">{s["fresh_jobs_today"]}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-title-text" style="margin-bottom:0.75rem;">Today\'s Strongest Matches</div>', unsafe_allow_html=True)
        st.markdown('<div style="background:var(--ada-surface); border:1px solid var(--ada-border); border-radius:16px; padding:1.25rem;">', unsafe_allow_html=True)
        if s["gmail_matches"]:
            for job in s["gmail_matches"]:
                link = job.get("link", "")
                st.markdown(f"**{job.get('match_score','—')}%** · {job['title']}")
                if link:
                    st.link_button("View posting", link, key=f"gs_{hash(job['title'])}")
        else:
            st.caption("No strong Gmail matches recorded today yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="section-title-text" style="margin-bottom:0.75rem;">Activity History Log</div>', unsafe_allow_html=True)
        st.markdown('<div style="background:var(--ada-surface); border:1px solid var(--ada-border); border-radius:16px; padding:1.25rem;">', unsafe_allow_html=True)
        if s["activity_log"]:
            for item in s["activity_log"][:12]:
                st.markdown(
                    f'<div class="activity-item">'
                    f'<span class="activity-time">{item["time"]}</span>'
                    f'<span>{item["message"]}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No activity logged yet today.")
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🔄 Refresh Summary Report"):
        st.session_state.daily_summary = build_daily_summary(min_score=auto_min_score)
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
