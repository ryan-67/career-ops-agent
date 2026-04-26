"""
test_portals.py
Quick script to test if large tech company career pages are
accessible and returning job content before adding to portals.yml.

Usage (PowerShell):
    python test_portals.py
"""

import requests
import time
from datetime import datetime

# Large tech companies with custom career portals
# Add/remove as needed before testing
PORTALS_TO_TEST = [
    {
        "name": "Apple",
        "url": "https://jobs.apple.com/en-us/search?search=data+engineer&sort=newest",
        "content_check": "data engineer"
    },
    {
        "name": "Google",
        "url": "https://careers.google.com/jobs/results/?q=data+engineer&location=United+States",
        "content_check": "data engineer"
    },
    {
        "name": "Amazon / AWS",
        "url": "https://www.amazon.jobs/en/search?base_query=data+engineer&loc_query=United+States",
        "content_check": "data engineer"
    },
    {
        "name": "Meta",
        "url": "https://www.metacareers.com/jobs?q=data+engineer&offices[0]=United+States",
        "content_check": "data engineer"
    },
    {
        "name": "Microsoft",
        "url": "https://careers.microsoft.com/v2/global/en/search?q=data+engineer&l=en_us&pg=1&pgSz=20&o=Recent&flt=true",
        "content_check": "data engineer"
    },
    {
        "name": "LinkedIn",
        "url": "https://www.linkedin.com/jobs/search/?keywords=data%20engineer&location=United%20States",
        "content_check": "data engineer"
    },
    {
        "name": "Netflix",
        "url": "https://jobs.netflix.com/search?q=data+engineer&location=United%20States",
        "content_check": "data engineer"
    },
    {
        "name": "Spotify",
        "url": "https://www.lifeatspotify.com/jobs?l=united-states&q=data+engineer",
        "content_check": "data engineer"
    },
    {
        "name": "Nvidia",
        "url": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite?q=data+engineer&locationCountry=a30a87ed25634629aa6c3958aa2b91ea",
        "content_check": "data engineer"
    },
    {
        "name": "Intel",
        "url": "https://jobs.intel.com/en/search#q=data%20engineer&t=Jobs",
        "content_check": "data engineer"
    },
    {
        "name": "Cisco",
        "url": "https://jobs.cisco.com/jobs/SearchJobs/data%20engineer?21178=%5B169482%5D&21178_format=6020&listFilterMode=1",
        "content_check": "data engineer"
    },
    {
        "name": "Adobe",
        "url": "https://careers.adobe.com/us/en/search-results?keywords=data+engineer",
        "content_check": "data engineer"
    },
    {
        "name": "Oracle",
        "url": "https://careers.oracle.com/jobs/#en/sites/jobsearch/requisitions?keyword=data+engineer&location=United+States&locationId=300000000149325&locationLevel=country",
        "content_check": "data engineer"
    },
    {
        "name": "IBM",
        "url": "https://www.ibm.com/us-en/employment/newhire/index.html#jobs?job-search=data+engineer",
        "content_check": "data engineer"
    },
    {
        "name": "Qualcomm",
        "url": "https://careers.qualcomm.com/careers/search?keywords=data+engineer&country=United+States&jobType=University+Grad",
        "content_check": "data engineer"
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def test_portal(portal: dict) -> dict:
    name = portal["name"]
    url = portal["url"]
    check = portal["content_check"].lower()

    try:
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        status = response.status_code
        content_found = check in response.text.lower()
        final_url = response.url

        if status == 200 and content_found:
            result = "✅ PASS"
            note = "Reachable and contains job content"
        elif status == 200 and not content_found:
            result = "⚠️  PARTIAL"
            note = "Reachable but job content not detected (may use JS rendering)"
        elif status in [301, 302]:
            result = "↩️  REDIRECT"
            note = f"Redirected to: {final_url}"
        elif status == 403:
            result = "🚫 BLOCKED"
            note = "Access denied — likely blocks scrapers"
        elif status == 404:
            result = "❌ NOT FOUND"
            note = "URL returned 404 — check the URL"
        else:
            result = f"⚠️  HTTP {status}"
            note = "Unexpected status code"

        return {
            "name": name,
            "result": result,
            "status": status,
            "note": note,
            "url": url
        }

    except requests.Timeout:
        return {
            "name": name,
            "result": "⏱️  TIMEOUT",
            "status": None,
            "note": "Request timed out after 15s",
            "url": url
        }
    except requests.RequestException as e:
        return {
            "name": name,
            "result": "❌ ERROR",
            "status": None,
            "note": str(e),
            "url": url
        }


def main():
    print(f"\n{'='*60}")
    print(f"  Career Portal Accessibility Test")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    results = []
    for portal in PORTALS_TO_TEST:
        print(f"Testing {portal['name']}...", end=" ", flush=True)
        result = test_portal(portal)
        results.append(result)
        print(result["result"])
        time.sleep(1)  # be polite, avoid rate limiting

    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")

    passed = [r for r in results if "PASS" in r["result"]]
    partial = [r for r in results if "PARTIAL" in r["result"]]
    failed = [r for r in results if any(x in r["result"] for x in ["BLOCKED", "NOT FOUND", "ERROR", "TIMEOUT"])]

    print(f"\n✅ PASS ({len(passed)}) — Safe to add to portals.yml:")
    for r in passed:
        print(f"   {r['name']}: {r['url']}")

    if partial:
        print(f"\n⚠️  PARTIAL ({len(partial)}) — Reachable but may need Playwright (JS rendering):")
        for r in partial:
            print(f"   {r['name']}: {r['note']}")

    if failed:
        print(f"\n❌ FAILED ({len(failed)}) — Do not add to portals.yml:")
        for r in failed:
            print(f"   {r['name']}: {r['note']}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()