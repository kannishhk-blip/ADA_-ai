"""
Matching agent (Week 2): scores each job posting against your resume using
sentence embeddings, so you see the most relevant jobs first instead of a
random list.

How it works, in plain terms:
1. Your resume text is converted into a vector (a list of numbers that
   captures its meaning).
2. Each job's title + description is converted into a vector the same way.
3. We compare the resume vector to each job vector using "cosine similarity"
   - a measure of how close two vectors point in the same direction.
   Score close to 1.0 = very similar meaning, close to 0 = unrelated.
4. Jobs are sorted highest-score first.

This runs 100% locally on your laptop (no API cost) using a small,
lightweight embedding model - fine for an 8GB RAM machine.
"""

import os
from sentence_transformers import SentenceTransformer, util

# Import the ingestion agents built in Week 1
from agents.gmail_ingest import fetch_gmail_jobs
from agents.remoteok_ingest import fetch_remoteok_jobs


def _extract_subject_and_snippet(gmail_message: dict):
    """Gmail's raw message format buries subject inside payload.headers."""
    headers = gmail_message.get("payload", {}).get("headers", [])
    subject = next(
        (h["value"] for h in headers if h.get("name", "").lower() == "subject"),
        "(no subject)",
    )
    snippet = gmail_message.get("snippet", "")
    return subject, snippet

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESUME_PATH = os.path.join(BASE_DIR, "data", "resume.txt")

# Small, fast, good-quality model - about 80MB download, runs fine on CPU
MODEL_NAME = "all-MiniLM-L6-v2"


def load_resume_text():
    if not os.path.exists(RESUME_PATH):
        raise FileNotFoundError(
            f"Resume not found at {RESUME_PATH}. "
            "Save your resume as plain text there first."
        )
    with open(RESUME_PATH, "r", encoding="utf-8") as f:
        return f.read()


def collect_all_jobs():
    """
    Pulls jobs from both Week 1 ingestion sources and normalizes them into
    one consistent format: {title, source, link, description}
    """
    jobs = []

    # Gmail job alerts (LinkedIn/Naukri) — silent fetch, links extracted from body.
    jobs.extend(fetch_gmail_jobs())

    # RemoteOK listings
    for job in fetch_remoteok_jobs():
        jobs.append({
            "title": job["title"],
            "source": f"RemoteOK - {job['company']}",
            "link": job["link"],
            "description": " ".join(job.get("tags", [])),
        })

    return jobs


def rank_jobs_by_resume_match(jobs, resume_text, model):
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)

    scored_jobs = []
    for job in jobs:
        job_text = f"{job['title']} {job['description']}"
        job_embedding = model.encode(job_text, convert_to_tensor=True)
        similarity = util.cos_sim(resume_embedding, job_embedding).item()

        scored_jobs.append({**job, "match_score": round(similarity * 100, 1)})

    return sorted(scored_jobs, key=lambda j: j["match_score"], reverse=True)


if __name__ == "__main__":
    print("Loading embedding model (first run downloads ~80MB, be patient)...")
    model = SentenceTransformer(MODEL_NAME)

    print("Loading resume...")
    resume_text = load_resume_text()

    print("Collecting jobs from Gmail + RemoteOK...")
    jobs = collect_all_jobs()

    if not jobs:
        print("No jobs found from either source. Run Week 1 scripts first.")
    else:
        print(f"\nScoring {len(jobs)} job(s) against your resume...\n")
        ranked = rank_jobs_by_resume_match(jobs, resume_text, model)

        for job in ranked:
            print(f"{job['match_score']}%  |  {job['title']}  ({job['source']})")
            if job["link"]:
                print(f"        {job['link']}")
        print()
