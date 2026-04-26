import os
import time
import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

APIFY_BASE_URL = "https://api.apify.com/v2"


def _run_actor(api_token: str, actor_id: str, run_input: dict, timeout: int = 120) -> list:
    """Runs an Apify actor and returns the results as a list."""
    headers = {"Content-Type": "application/json"}
    url = f"{APIFY_BASE_URL}/acts/{actor_id}/run-sync-get-dataset-items"
    params = {"token": api_token, "timeout": timeout, "memory": 256}

    try:
        response = requests.post(url, json=run_input, params=params, timeout=timeout + 30)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        logger.error(f"Apify actor {actor_id} failed: {e}")
        return []
    except requests.Timeout:
        logger.error(f"Apify actor {actor_id} timed out after {timeout}s")
        return []


def _scrape_linkedin(api_token: str, queries: list, max_per_query: int) -> list:
    """Scrapes LinkedIn Jobs via Apify."""
    jobs = []
    actor_id = "curiosity_dragon/linkedin-jobs-scraper"

    for q in queries:
        logger.info(f"Scraping LinkedIn: {q['query']} in {q['location']}")
        run_input = {
            "queries": [q["query"]],
            "location": q["location"],
            "count": max_per_query,
            "proxy": {"useApifyProxy": True}
        }
        results = _run_actor(api_token, actor_id, run_input)
        for r in results:
            jobs.append({
                "title": r.get("title", ""),
                "company": r.get("companyName", ""),
                "location": r.get("location", ""),
                "url": r.get("jobUrl", ""),
                "description": r.get("description", "")[:2000],
                "source": "linkedin",
                "scraped_at": datetime.now(timezone.utc).isoformat()
            })
        time.sleep(2)

    logger.info(f"LinkedIn scraping complete — {len(jobs)} jobs found")
    return jobs


def _scrape_indeed(api_token: str, queries: list, max_per_query: int) -> list:
    """Scrapes Indeed via Apify."""
    jobs = []
    actor_id = "misceres/indeed-scraper"

    for q in queries:
        logger.info(f"Scraping Indeed: {q['query']} in {q['location']}")
        run_input = {
            "position": q["query"],
            "country": "US",
            "location": q["location"],
            "maxItems": max_per_query,
            "parseCompanyDetails": False
        }
        results = _run_actor(api_token, actor_id, run_input)
        for r in results:
            jobs.append({
                "title": r.get("positionName", ""),
                "company": r.get("company", ""),
                "location": r.get("location", ""),
                "url": r.get("url", ""),
                "description": r.get("description", "")[:2000],
                "source": "indeed",
                "scraped_at": datetime.now(timezone.utc).isoformat()
            })
        time.sleep(2)

    logger.info(f"Indeed scraping complete — {len(jobs)} jobs found")
    return jobs


def _filter_jobs(jobs: list, exclude_keywords: list) -> list:
    """Filters out jobs matching exclusion keywords in title."""
    filtered = []
    for job in jobs:
        title_lower = job.get("title", "").lower()
        if any(kw.lower() in title_lower for kw in exclude_keywords):
            continue
        if not job.get("url"):
            continue
        filtered.append(job)

    # Deduplicate by URL
    seen = set()
    deduped = []
    for job in filtered:
        if job["url"] not in seen:
            seen.add(job["url"])
            deduped.append(job)

    logger.info(f"Filtered {len(jobs)} → {len(deduped)} jobs after exclusions and dedup")
    return deduped


def run_scan(config: dict) -> dict:
    """
    Main scan function. Scrapes jobs from configured sources.
    Returns dict with success, jobs (list), count, timestamp.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    api_token = os.environ.get("APIFY_API_TOKEN")

    if not api_token:
        raise RuntimeError("APIFY_API_TOKEN not set in environment")

    scraping_config = config.get("scraping", {})
    sources = scraping_config.get("sources", ["linkedin"])
    max_per_query = scraping_config.get("max_results_per_query", 25)
    exclude_keywords = config.get("filters", {}).get("exclude_keywords", [])

    all_jobs = []

    if "linkedin" in sources:
        linkedin_queries = scraping_config.get("linkedin_queries", [])
        linkedin_jobs = _scrape_linkedin(api_token, linkedin_queries, max_per_query)
        all_jobs.extend(linkedin_jobs)

    if "indeed" in sources:
        indeed_queries = scraping_config.get("indeed_queries", [])
        indeed_jobs = _scrape_indeed(api_token, indeed_queries, max_per_query)
        all_jobs.extend(indeed_jobs)

    filtered_jobs = _filter_jobs(all_jobs, exclude_keywords)

    logger.info(f"Scan complete — {len(filtered_jobs)} jobs ready for scoring")

    return {
        "success": True,
        "jobs": filtered_jobs,
        "count": len(filtered_jobs),
        "timestamp": timestamp
    }