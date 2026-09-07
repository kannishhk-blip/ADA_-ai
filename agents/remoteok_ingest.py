"""
Ingestion agent (RemoteOK part): pulls jobs from RemoteOK's public API.

We switched from Indeed RSS to RemoteOK because Indeed has been restricting
its public RSS feed in many regions (it now often returns a webpage instead
of RSS data, which breaks parsing). RemoteOK provides a stable, public,
no-login-required JSON feed - a more reliable data source for this project.

No scraping, no login, no ToS issues - this is RemoteOK's official public
API endpoint.
"""

import re
import requests

# Edit this to change which roles you're searching for.
# RemoteOK's actual tag spellings vary between postings (e.g. "ai" vs
# "artificial-intelligence", "machinelearning" vs "machine-learning"), so we
# match broadly against BOTH tags and the job title, not just one exact tag.
# We use WORD-BOUNDARY matching (not plain substring) so short keywords like
# "ai" or "ml" don't accidentally match inside unrelated words such as
# "retail", "mail", or "maintenance".
REMOTEOK_API_URL = "https://remoteok.com/api"
SEARCH_KEYWORDS = [
    "ai", "artificial intelligence", "artificial-intelligence",
    "machine learning", "machine-learning", "machinelearning", "ml",
    "python", "data science", "data-science", "llm", "genai",
]
_KEYWORD_PATTERNS = [re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE) for k in SEARCH_KEYWORDS]


def _text_matches_keywords(text: str) -> bool:
    return any(pattern.search(text) for pattern in _KEYWORD_PATTERNS)


def fetch_remoteok_jobs(max_results=15):
    """
    Returns a list of dicts: [{title, company, link, tags, published}, ...]
    """
    headers = {"User-Agent": "career-agent-student-project"}
    response = requests.get(REMOTEOK_API_URL, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()
    # The first item in RemoteOK's response is always metadata, not a job - skip it
    listings = data[1:] if len(data) > 1 else []

    jobs = []
    for job in listings:
        title = job.get("position", "")
        tags_text = " ".join(job.get("tags", []))

        # Word-boundary match against title AND tags combined - avoids both
        # false negatives (tag spelling mismatches) and false positives
        # (short keywords matching inside unrelated words).
        if _text_matches_keywords(title) or _text_matches_keywords(tags_text):
            jobs.append({
                "title": title,
                "company": job.get("company", ""),
                "link": job.get("url", ""),
                "tags": job.get("tags", []),
                "published": job.get("date", ""),
            })

        if len(jobs) >= max_results:
            break

    return jobs


if __name__ == "__main__":
    try:
        jobs = fetch_remoteok_jobs()
        print(f"Found {len(jobs)} job(s) from RemoteOK matching {SEARCH_KEYWORDS}:\n")
        for j in jobs:
            print(f"- {j['title']} at {j['company']}")
            print(f"  {j['link']}\n")
    except requests.exceptions.RequestException as e:
        print(f"Could not reach RemoteOK: {e}")
