"""
ADA Agent — AI career assistant dashboard.

Clean UI for job matching, calendar scheduling, and daily summaries.
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
# Page + theme design system
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ADA Agent",
    layout="wide",
    page_icon="🤖",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap');

:root {
    --ada-bg: #0B0C10;
    --ada-card: #16171D;
    --ada-card-hover: #1E2140;
    --ada-ink: #F0F1F5;
    --ada-muted: #9497A8;
    --ada-line: #2A2C36;
    --ada-primary: #7C6FFF;
    --ada-primary-soft: #201D3A;
    --ada-accent: #00E5D2;
    --ada-gradient: linear-gradient(135deg, #7C6FFF 0%, #00E5D2 100%);
}

/* Base resets & layout */
[data-testid="stAppViewContainer"] { background: var(--ada-bg); }
[data-testid="stHeader"] { background: transparent !important; }

/* ALWAYS show the sidebar collapse/expand toggle button clearly */
[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    background: #16171D !important;
    border: 1.5px solid var(--ada-primary) !important;
    border-radius: 10px !important;
    color: var(--ada-accent) !important;
    margin: 10px !important;
    z-index: 999999 !important;
    box-shadow: 0 4px 16px rgba(124, 111, 255, 0.3) !important;
}
[data-testid="stSidebarCollapsedControl"]:hover {
    background: #1E2140 !important;
    border-color: var(--ada-accent) !important;
}
[data-testid="stSidebarCollapsedControl"] svg {
    fill: var(--ada-accent) !important;
    color: var(--ada-accent) !important;
}

/* Custom scrollbars */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--ada-bg); }
::-webkit-scrollbar-thumb { background: var(--ada-line); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--ada-primary); }

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: #0B0C10 !important;
    border-right: 1px solid var(--ada-line) !important;
}
[data-testid="stSidebar"] .stMarkdown p { color: #9BA3BF !important; }

.sidebar-label {
    font-size: 0.72rem;
    font-weight: 800;
    color: #00E5D2;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

[data-testid="stSidebar"] .stSlider label {
    font-size: 0.84rem !important;
    font-weight: 600 !important;
    color: #E8EAF5 !important;
}

[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--ada-gradient) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 16px rgba(124, 111, 255, 0.25) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background: transparent !important;
    color: #C5CBE0 !important;
    border: none !important;
    text-align: left !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
    background: var(--ada-card-hover) !important;
    color: #fff !important;
}

html, body, [class*="css"] {
    color: var(--ada-ink);
    font-family: 'Plus Jakarta Sans', sans-serif;
}
h1, h2, h3 {
    font-family: 'Outfit', sans-serif !important;
}

.brand-logo {
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 1.5rem;
    background: var(--ada-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.brand-sub {
    font-size: 0.78rem;
    color: #7B83A8 !important;
    margin-top: 0.1rem;
}
.brand-dot {
    display: inline-block;
    width: 8px; height: 8px;
    background: #34D399;
    border-radius: 50%;
    margin-right: 6px;
    box-shadow: 0 0 8px #34D399;
}

/* Hotkey Banner */
.hotkey-banner {
    background: linear-gradient(135deg, rgba(30, 35, 55, 0.8) 0%, rgba(15, 25, 35, 0.8) 100%);
    border: 1px solid rgba(124, 111, 255, 0.35);
    border-radius: 14px;
    padding: 0.85rem 1.35rem;
    margin-bottom: 1.25rem;
    color: #F0F1F5;
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
.hotkey-status {
    font-size: 0.8rem;
    color: #00E5D2;
    font-weight: 700;
}
kbd {
    background: #161824;
    border: 1px solid #2A2E44;
    border-radius: 6px;
    box-shadow: 0 2px 0 #000;
    color: #00E5D2;
    display: inline-block;
    font-family: monospace;
    font-size: 0.85em;
    font-weight: 700;
    line-height: 1;
    padding: 4px 7px;
    margin: 0 2px;
    white-space: nowrap;
}

/* Component cards */
.ada-card {
    background: var(--ada-card);
    border: 1px solid var(--ada-line);
    border-radius: 20px;
    padding: 1.5rem 1.8rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    transition: all 0.2s ease;
    margin-bottom: 1.5rem;
}
.hero-card {
    background: linear-gradient(145deg, #151724 0%, #0F111B 100%);
    border: 1px solid rgba(124, 111, 255, 0.25);
    box-shadow: 0 8px 32px rgba(124, 111, 255, 0.08);
}
.hero-title {
    font-family: 'Outfit', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    margin: 0 0 0.4rem 0;
    color: var(--ada-ink);
}
.hero-sub { color: var(--ada-muted); font-size: 0.95rem; margin: 0; line-height: 1.55; }

/* Stat metric cards */
.stat-card {
    background: var(--ada-card);
    border: 1px solid var(--ada-line);
    border-radius: 16px;
    padding: 1.25rem 1.4rem;
    text-align: center;
    transition: transform 0.15s ease, border-color 0.15s ease;
}
.stat-card:hover {
    transform: translateY(-2px);
    border-color: var(--ada-primary);
}
.stat-icon { font-size: 1.5rem; margin-bottom: 0.35rem; }
.stat-label {
    font-size: 0.72rem;
    color: var(--ada-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 700;
}
.stat-value {
    font-family: 'Outfit', sans-serif;
    font-size: 2.1rem;
    font-weight: 800;
    color: var(--ada-primary);
    line-height: 1.1;
    margin-top: 0.25rem;
}

.section-title {
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
    font-size: 1.15rem;
    margin: 0 0 0.85rem 0;
    color: var(--ada-ink);
}

/* Button styling - non-collapsing, crisp cards */
.main-content div[data-testid="column"] .stButton > button {
    background: var(--ada-card) !important;
    color: var(--ada-ink) !important;
    border: 1px solid var(--ada-line) !important;
    border-radius: 14px !important;
    min-height: 60px !important;
    white-space: pre-wrap !important;
    word-break: break-word !important;
    text-align: center !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    line-height: 1.35 !important;
    padding: 0.75rem 0.85rem !important;
    transition: all 0.15s ease !important;
}
.main-content div[data-testid="column"] .stButton > button:hover {
    border-color: var(--ada-primary) !important;
    background: var(--ada-card-hover) !important;
    box-shadow: 0 4px 16px rgba(124, 111, 255, 0.2) !important;
    transform: translateY(-1px);
}

div[data-testid="stTextInput"] input {
    background: var(--ada-card) !important;
    color: var(--ada-ink) !important;
    border: 1px solid var(--ada-line) !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
}
div[data-testid="stTextInput"] input::placeholder { color: var(--ada-muted) !important; }

.feed-item {
    border-bottom: 1px solid var(--ada-line);
    padding: 1rem 0;
}
.feed-item:last-child { border-bottom: none; }
.feed-title { font-weight: 600; font-size: 0.98rem; }
.feed-meta { color: var(--ada-muted); font-size: 0.83rem; margin-top: 0.25rem; }
.feed-match {
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    color: var(--ada-primary);
    font-size: 1rem;
    background: rgba(124, 111, 255, 0.12);
    border: 1px solid rgba(124, 111, 255, 0.25);
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
}
.feed-link a { color: var(--ada-primary); text-decoration: none; font-size: 0.83rem; font-weight: 600; }

.result-banner {
    background: var(--ada-primary-soft);
    border: 1px solid #D5D2FF;
    border-radius: 14px;
    padding: 1rem 1.25rem;
    margin-bottom: 1.5rem;
}
.summary-hero {
    background: var(--ada-gradient);
    border-radius: 20px;
    padding: 2rem;
    color: #fff;
    margin-bottom: 1.5rem;
}
.summary-hero h2 { color: #fff !important; margin: 0 0 0.5rem 0; font-size: 1.6rem; }
.summary-hero p { color: rgba(255,255,255,0.88); margin: 0; }

.activity-item {
    display: flex;
    gap: 0.75rem;
    padding: 0.65rem 0;
    border-bottom: 1px solid var(--ada-line);
    font-size: 0.88rem;
}
.activity-time { color: var(--ada-muted); min-width: 70px; font-size: 0.78rem; }

.user-pill {
    display: flex; align-items: center; gap: 0.65rem;
    padding: 0.5rem 0;
}
.user-avatar {
    width: 36px; height: 36px; border-radius: 50%;
    background: var(--ada-gradient);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700; color: #fff;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
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
    return st.button(f"{icon} {title}\n{subtitle}", key=key, use_container_width=True)


def apply_result(result: dict | None) -> None:
    if not result:
        st.error("Something went wrong. Check your Google login and resume.txt.")
        return
    st.session_state.last_result = result
    st.session_state.ranked_jobs = result.get("ranked_jobs", [])


def run_google_action(label: str, func):
    """Run a Gmail/Calendar action and show a short error instead of a traceback."""
    try:
        return func()
    except Exception as exc:
        text = str(exc)
        if "invalid_grant" in text or "RefreshError" in type(exc).__name__:
            st.error(
                "Google login expired. A browser window should open so you can sign in again. "
                "If it does not, run this in a terminal, then retry the button:\n\n"
                "`python config\\google_auth.py`"
            )
            return None
        st.error(f"{label} failed: {exc}")
        return None


def render_result_banner() -> None:
    result = st.session_state.last_result
    if not result:
        return
    scheduled = result.get("scheduled", [])
    st.markdown(
        f'<div class="result-banner">✅ <b>{result.get("message", "Done.")}</b></div>',
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
                st.markdown(f"**{job.get('title', 'Job')}**  \n{when}")
            with cols[1]:
                if link:
                    st.link_button("View job", link, use_container_width=True)
            with cols[2]:
                if cal:
                    st.link_button("Calendar", cal, use_container_width=True)


# ---------------------------------------------------------------------------
# Sidebar (Left Column Controls)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="brand-logo">🤖 ADA Agent</div>'
        '<div class="brand-sub"><span class="brand-dot"></span>AI Career Assistant · Online</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label">⚙️ MATCHING ENGINE CONTROLS</div>', unsafe_allow_html=True)

    auto_min_score = st.slider(
        "Minimum Match Score Threshold %",
        min_value=0, max_value=100, value=50, step=5,
        help="Only job postings scoring at or above this percentage will be automatically scheduled on Google Calendar.",
    )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    auto_top_n = st.slider(
        "Max Schedule Slots (Top N)",
        min_value=1, max_value=10, value=3, step=1,
        help="Maximum number of top-matching application slots to schedule per scan execution.",
    )

    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="sidebar-label">📍 NAVIGATION</div>', unsafe_allow_html=True)

    nav = [
        ("🏠  Home", "home"),
        ("🗣️  Talk to Ada", "talk"),
        ("✨  Job Matches", "matches"),
        ("📅  My Calendar", "calendar"),
        ("📊  Daily Summary", "summary"),
    ]
    for label, key in nav:
        btn_type = "primary" if st.session_state.ada_page == key else "secondary"
        if st.button(label, key=f"nav_{key}", use_container_width=True, type=btn_type):
            st.session_state.ada_page = key
            if key == "summary":
                with st.spinner("Building today's summary..."):
                    st.session_state.daily_summary = build_daily_summary(min_score=auto_min_score)
            st.rerun()

    st.markdown("<hr style='border-color:#2A2D4A; margin:1.5rem 0;'>", unsafe_allow_html=True)

    st.markdown(
        '<div class="user-pill">'
        '<div class="user-avatar">K</div>'
        '<div><div style="color:#E8EAF5;font-weight:600;font-size:0.88rem">You</div>'
        '<div style="color:#7B83A8;font-size:0.75rem">Active session</div></div></div>',
        unsafe_allow_html=True,
    )

stats = get_today_stats()
ranked_jobs = st.session_state.ranked_jobs
search = st.session_state.get("job_search_query", "")

if search:
    q = search.lower()
    ranked_jobs = [j for j in ranked_jobs if q in j.get("title", "").lower() or q in j.get("source", "").lower()]


# ---------------------------------------------------------------------------
# Navigation Bar Component (Rendered on ALL pages to guarantee navigation)
# ---------------------------------------------------------------------------
def render_navigation() -> None:
    top_nav = [
        ("🏠 Home", "home"),
        ("🗣️ Talk to Ada", "talk"),
        ("✨ Job Matches", "matches"),
        ("📅 My Calendar", "calendar"),
        ("📊 Daily Summary", "summary"),
    ]
    nav_cols = st.columns(len(top_nav))
    for (label, key), col in zip(top_nav, nav_cols):
        with col:
            btn_type = "primary" if st.session_state.ada_page == key else "secondary"
            if st.button(label, key=f"topnav_{key}", use_container_width=True, type=btn_type):
                st.session_state.ada_page = key
                if key == "summary":
                    with st.spinner("Building today's summary..."):
                        st.session_state.daily_summary = build_daily_summary(min_score=auto_min_score)
                st.rerun()


# Render top navigation bar across all pages
render_navigation()
st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Main Content Area
# ---------------------------------------------------------------------------
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# 1. Top Hotkey Banner
st.markdown(
    """
    <div class="hotkey-banner">
        <div>
            ⚡ <b>IMPORTANT DESKTOP SHORTCUT:</b> Press <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>A</kbd> anywhere on Windows to launch ADA Assistant instantly!
        </div>
        <span class="hotkey-status">Global Hotkey Active</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.ada_page == "home":
    # 2. Hero Greeting Card (Hello I'm ADA - Full Width)
    st.markdown(
        """
        <div class="ada-card hero-card">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem;">
                <span class="brand-dot"></span>
                <span style="font-size:0.75rem; font-weight:700; color:#00E5D2; text-transform:uppercase; letter-spacing:0.08em;">Active Career Assistant</span>
            </div>
            <div class="hero-title">Hello, I'm ADA 👋</div>
            <p class="hero-sub">Monitors your Gmail job alerts, parses remote listings, scores them against your resume with AI embeddings, and auto-schedules application slots on Google Calendar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Quick Actions Section (Below Hello I'm ADA)
    st.markdown('<div class="section-title">⚡ Quick Actions</div>', unsafe_allow_html=True)
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        if cmd_button("📧", "Scan Gmail", "Inbox job alerts", "qa_gmail"):
            with st.spinner("Checking Gmail inbox for job alerts..."):
                apply_result(run_google_action(
                    "Scan Gmail",
                    lambda: run_gmail_pipeline(min_score=auto_min_score, top_n=auto_top_n),
                ))
    with qa2:
        if cmd_button("🌐", "Scan RemoteOK", "Live remote jobs", "qa_remoteok"):
            with st.spinner("Fetching RemoteOK listings..."):
                apply_result(run_google_action(
                    "Scan RemoteOK",
                    lambda: run_remoteok_pipeline(min_score=auto_min_score, top_n=auto_top_n),
                ))
    with qa3:
        if cmd_button("📅", "Auto Schedule", "Calendar sync", "qa_schedule"):
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
                    apply_result(run_google_action(
                        "Auto Schedule",
                        lambda: run_full_pipeline(min_score=auto_min_score, top_n=auto_top_n),
                    ))

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    qa4, qa5, qa6 = st.columns(3)
    with qa4:
        if cmd_button("🔍", "Full Pipeline", "Run all sources", "qa_full"):
            with st.spinner("Running full Gmail + RemoteOK pipeline..."):
                apply_result(run_google_action(
                    "Full Pipeline",
                    lambda: run_full_pipeline(min_score=auto_min_score, top_n=auto_top_n),
                ))
    with qa5:
        if cmd_button("📊", "Daily Summary", "Today's report", "qa_summary"):
            with st.spinner("Building summary..."):
                st.session_state.daily_summary = build_daily_summary(min_score=auto_min_score)
            st.session_state.ada_page = "summary"
            st.rerun()
    with qa6:
        if cmd_button("💬", "WhatsApp", "Send update", "qa_wa"):
            try:
                from agents.whatsapp_agent import MY_PHONE_NUMBER, send_whatsapp_message
                summary = build_daily_summary(min_score=auto_min_score)
                send_whatsapp_message(MY_PHONE_NUMBER, summary["summary_text"])
                st.success("Summary sent to WhatsApp!")
            except Exception as exc:
                st.info(f"WhatsApp not configured: {exc}")

    st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)

    # 4. Stat Metric Cards (Directly Below Quick Actions)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-icon">📧</div>'
            f'<div class="stat-label">Gmail Matches</div>'
            f'<div class="stat-value">{stats["gmail_matches"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="stat-card"><div class="stat-icon">📅</div>'
            f'<div class="stat-label">Calendar Today</div>'
            f'<div class="stat-value">{stats["calendar_added"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="stat-card"><div class="stat-icon">🆕</div>'
            f'<div class="stat-label">Fresh Jobs</div>'
            f'<div class="stat-value">{stats["fresh_jobs"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="stat-card"><div class="stat-icon">🎯</div>'
            f'<div class="stat-label">Jobs Loaded</div>'
            f'<div class="stat-value">{len(st.session_state.ranked_jobs)}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
    render_result_banner()

    # 5. Search & Job Feed (Full Width)
    st.text_input(
        "Search jobs", placeholder="Search by title, skills or company...",
        label_visibility="collapsed", key="job_search_query",
    )
    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Top Matches Feed</div>', unsafe_allow_html=True)
    feed = st.session_state.ranked_jobs
    if search:
        feed = ranked_jobs

    html = '<div class="ada-card">'
    if not feed:
        html += '<p style="color:#8E93A6;margin:0;padding:0.75rem 0;">No matches loaded yet. Click <b>Scan Gmail</b> or <b>Scan RemoteOK</b> to populate job postings.</p>'
    for job in feed[:12]:
        link = job.get("link", "")
        link_part = f'<div class="feed-link"><a href="{link}" target="_blank">View posting →</a></div>' if link else ""
        html += f"""
        <div class="feed-item">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:1rem">
                <div>
                    <div class="feed-title">{job['title']}</div>
                    <div class="feed-meta">{job.get('source','')}</div>
                    {link_part}
                </div>
                <div class="feed-match">{job.get('match_score','—')}% Match</div>
            </div>
        </div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Dedicated "Talk to Ada" Page
# ---------------------------------------------------------------------------
elif st.session_state.ada_page == "talk":
    st.markdown(
        """
        <div class="summary-hero">
            <h2>🗣️ Talk to ADA Assistant</h2>
            <p>Execute natural language commands to launch desktop apps, open websites, send WhatsApp messages, or place phone calls.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ada-card" style="margin-bottom:1.5rem">', unsafe_allow_html=True)
    st.markdown("**Enter Natural Language Command**")
    cmd_col, btn_col = st.columns([5, 1])
    with cmd_col:
        ada_command = st.text_input(
            "Ada command", placeholder="e.g. open insta, send hi to my gf, call mom",
            label_visibility="collapsed", key="ada_talk_command_input",
        )
    with btn_col:
        run_clicked = st.button("Execute", type="primary", use_container_width=True)

    # Preset command chips
    st.markdown("<div style='margin-top:0.6rem; font-size:0.83rem; color:var(--ada-muted); font-weight:600;'>Preset Command Shortcuts:</div>", unsafe_allow_html=True)
    preset_cols = st.columns(6)
    presets = [
        ("🌐 Open LinkedIn", "open linkedin"),
        ("📧 Open Gmail", "open gmail"),
        ("📅 Open Calendar", "open calendar"),
        ("▶️ Open YouTube", "open youtube"),
        ("💬 Send WhatsApp", "send hi to my gf"),
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
            st.session_state.last_cmd_output = ("error", f"Command failed: {e}")

    if st.session_state.last_cmd_output:
        status_type, msg = st.session_state.last_cmd_output
        if status_type == "success":
            st.success(f"**Ada Response:**\n\n{msg}")
        else:
            st.error(msg)
    st.markdown("</div>", unsafe_allow_html=True)

    col_info_a, col_info_b = st.columns(2)
    with col_info_a:
        st.markdown('<div class="section-title">Known Desktop Apps & Websites</div>', unsafe_allow_html=True)
        st.markdown('<div class="ada-card">', unsafe_allow_html=True)
        try:
            apps = load_apps()
            for app_name, info in apps.items():
                target = info.get("target", "")
                st.markdown(f"• **{app_name.capitalize()}** — `{target}`")
        except Exception:
            st.caption("No app config loaded.")
        st.markdown(f"<br><small style='color:var(--ada-muted);'>Config file: <code>{APPS_PATH}</code></small>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_info_b:
        st.markdown('<div class="section-title">Configured Phone Contacts</div>', unsafe_allow_html=True)
        st.markdown('<div class="ada-card">', unsafe_allow_html=True)
        try:
            contacts = load_contacts()
            for nickname, phone in contacts.items():
                st.markdown(f"• **{nickname.capitalize()}** — `{phone}`")
        except Exception:
            st.caption("No contacts configured yet.")
        st.markdown(f"<br><small style='color:var(--ada-muted);'>Config file: <code>{CONTACTS_PATH}</code></small>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.ada_page == "matches":
    st.markdown('<div class="section-title">✨ Job Matches</div>', unsafe_allow_html=True)
    render_result_banner()
    jobs = ranked_jobs if search else st.session_state.ranked_jobs
    if not jobs:
        st.info("No jobs loaded yet. Go to **Home** and click **Scan Gmail** or **Scan RemoteOK**.")
    for job in jobs:
        cols = st.columns([4, 1, 1])
        with cols[0]:
            st.markdown(f"**{job.get('match_score','—')}%** · {job['title']}  \n*{job.get('source','')}*")
        with cols[1]:
            if job.get("link"):
                st.link_button("Job", job["link"], use_container_width=True)
        with cols[2]:
            if st.button("📅", key=f"cal_{hash(job['title'])}", help="Add to calendar"):
                with st.spinner("Scheduling..."):
                    scheduled = schedule_jobs([job], min_score=0, top_n=1)
                    if scheduled:
                        record_calendar_scheduled(1)
                        st.success("Added to calendar!")
                    else:
                        st.info("Already scheduled or no free slot.")

elif st.session_state.ada_page == "calendar":
    st.markdown('<div class="section-title">📅 My Calendar</div>', unsafe_allow_html=True)
    try:
        cal = get_calendar_service()
        already = get_already_scheduled_titles(cal, LOOK_AHEAD_DAYS)
    except Exception:
        already = set()
        cal = None

    jobs = st.session_state.ranked_jobs
    if not jobs:
        st.info("Load jobs from Home first.")
    for job in jobs:
        tag = "✅ On calendar" if job["title"] in already else "⏳ Not scheduled"
        st.markdown(f"**{job.get('match_score','—')}%** · {job['title']} — *{tag}*")
        if job.get("link"):
            st.link_button("Open job posting", job["link"], key=f"link_{hash(job['title'])}")

    if cal and jobs:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Schedule all top matches", type="primary"):
            with st.spinner("Scheduling..."):
                scheduled = schedule_jobs(jobs, min_score=auto_min_score, top_n=auto_top_n)
                done = [s for s in scheduled if s.get("status") == "scheduled"]
                record_calendar_scheduled(len(done))
                st.session_state.last_result = {
                    "source": "Calendar",
                    "found": len(jobs),
                    "ranked_jobs": jobs,
                    "scheduled": done,
                    "message": f"Scheduled {len(done)} job(s).",
                }
                st.rerun()

elif st.session_state.ada_page == "summary":
    if st.session_state.daily_summary is None:
        with st.spinner("Loading..."):
            st.session_state.daily_summary = build_daily_summary(min_score=auto_min_score)

    s = st.session_state.daily_summary
    st.markdown(
        f"""
        <div class="summary-hero">
            <h2>📊 Daily Summary</h2>
            <p>{s['date_label']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"<p style='font-size:1.05rem;color:var(--ada-ink);margin-bottom:1.5rem'>{s['summary_text']}</p>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-icon">📧</div>'
            f'<div class="stat-label">Gmail Alerts</div>'
            f'<div class="stat-value">{s["gmail_alerts_today"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="stat-card"><div class="stat-icon">✅</div>'
            f'<div class="stat-label">Gmail Matches</div>'
            f'<div class="stat-value">{s["gmail_matches_today"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="stat-card"><div class="stat-icon">📅</div>'
            f'<div class="stat-label">Added to Calendar</div>'
            f'<div class="stat-value">{s["calendar_added_today"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="stat-card"><div class="stat-icon">🆕</div>'
            f'<div class="stat-label">Fresh Jobs Today</div>'
            f'<div class="stat-value">{s["fresh_jobs_today"]}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-title">Today\'s Gmail Matches</div>', unsafe_allow_html=True)
        st.markdown('<div class="ada-card">', unsafe_allow_html=True)
        if s["gmail_matches"]:
            for job in s["gmail_matches"]:
                link = job.get("link", "")
                st.markdown(f"**{job.get('match_score','—')}%** · {job['title']}")
                if link:
                    st.link_button("Open", link, key=f"gs_{hash(job['title'])}")
        else:
            st.caption("No Gmail matches yet today. Click Scan Gmail on Home.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="section-title">What ADA Did Today</div>', unsafe_allow_html=True)
        st.markdown('<div class="ada-card">', unsafe_allow_html=True)
        if s["activity_log"]:
            for item in s["activity_log"][:12]:
                st.markdown(
                    f'<div class="activity-item">'
                    f'<span class="activity-time">{item["time"]}</span>'
                    f'<span>{item["message"]}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No activity yet. Run an agent from the Home page.")
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🔄 Refresh summary"):
        st.session_state.daily_summary = build_daily_summary(min_score=auto_min_score)
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
