import os
import json
import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def _load_cv(career_ops_path: str) -> str:
    """Loads cv.md from the career-ops directory."""
    cv_path = os.path.join(career_ops_path, "cv.md")
    if not os.path.exists(cv_path):
        raise FileNotFoundError(f"cv.md not found at {cv_path}")
    with open(cv_path, "r", encoding="utf-8") as f:
        return f.read()


def _build_scoring_prompt(jobs: list, cv_content: str) -> str:
    """Builds the batch scoring prompt."""
    jobs_text = ""
    for i, job in enumerate(jobs, 1):
        jobs_text += f"""
{i}. **{job['title']}** at **{job['company']}**
   Location: {job.get('location', 'Unknown')}
   URL: {job.get('url', 'N/A')}
   Description: {job.get('description', 'No description available')[:500]}
---"""

    return f"""You are an expert technical recruiter evaluating job fit.

Score each job listing below against the candidate's CV on a scale of 1.0 to 5.0.

Scoring criteria:
- 5.0: Perfect match — all required skills present, ideal seniority level
- 4.0-4.9: Strong match — most skills present, minor gaps
- 3.5-3.9: Good match — core skills present, some gaps
- 3.0-3.4: Moderate match — partial skill overlap
- Below 3.0: Weak match — significant gaps

Candidate CV:
{cv_content}

Job Listings:
{jobs_text}

Return ONLY a JSON array. No preamble, no markdown, no explanation.
Format:
[
  {{
    "index": 1,
    "company": "Company Name",
    "title": "Job Title",
    "score": 4.2,
    "reason": "One sentence explaining the score",
    "url": "job url",
    "location": "job location"
  }}
]"""


def _call_claude_api(prompt: str, api_key: str) -> list:
    """Calls the Anthropic API directly for batch scoring."""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(ANTHROPIC_API_URL, json=payload, headers=headers, timeout=120)
    response.raise_for_status()

    data = response.json()
    text = data["content"][0]["text"].strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    return json.loads(text)


def score_jobs(jobs: list, config: dict) -> dict:
    """
    Scores all jobs against cv.md using a single Claude API call per batch.
    Returns dict with success, scored_jobs (list), timestamp.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    if not jobs:
        logger.info("No jobs to score")
        return {
            "success": True,
            "scored_jobs": [],
            "timestamp": timestamp
        }

    career_ops_path = config.get("career_ops", {}).get("path", "/opt/airflow/career-ops")
    cv_content = _load_cv(career_ops_path)

    batch_size = config.get("scoring", {}).get("batch_size", 50)
    min_score = config.get("scoring", {}).get("min_score", 3.5)
    max_results = config.get("scoring", {}).get("max_results_in_digest", 15)

    all_scored = []

    # Process in batches
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        logger.info(f"Scoring batch {i//batch_size + 1} — {len(batch)} jobs")

        prompt = _build_scoring_prompt(batch, cv_content)

        try:
            scored_batch = _call_claude_api(prompt, api_key)
            # Re-attach original URL and location from source data
            for scored in scored_batch:
                idx = scored.get("index", 1) - 1
                if 0 <= idx < len(batch):
                    scored["url"] = batch[idx].get("url", scored.get("url", ""))
                    scored["location"] = batch[idx].get("location", scored.get("location", ""))
            all_scored.extend(scored_batch)
            logger.info(f"Batch scored — {len(scored_batch)} results")
        except Exception as e:
            logger.error(f"Scoring batch failed: {e}")
            continue

    # Filter by min score and sort
    qualified = [j for j in all_scored if j.get("score", 0) >= min_score]
    qualified.sort(key=lambda x: x.get("score", 0), reverse=True)
    top_results = qualified[:max_results]

    logger.info(f"Scoring complete — {len(qualified)} qualified, returning top {len(top_results)}")

    return {
        "success": True,
        "scored_jobs": top_results,
        "timestamp": timestamp
    }