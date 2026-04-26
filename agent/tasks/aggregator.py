import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def aggregate_reports(scored_jobs: list, output_path: str) -> dict:
    """
    Builds a digest markdown file from scored job results.
    Returns dict with success, reports_found, digest_path, timestamp.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    date_str = datetime.now().strftime("%Y-%m-%d")

    if not scored_jobs:
        logger.info("No scored jobs to aggregate")
        return {
            "success": True,
            "reports_found": 0,
            "digest_path": None,
            "timestamp": timestamp
        }

    os.makedirs(output_path, exist_ok=True)
    digest_path = os.path.join(output_path, f"digest-{date_str}.md")

    lines = [
        f"# Career-Ops Daily Digest — {date_str}",
        f"\n**{len(scored_jobs)} recommended role(s)** scored above threshold\n",
        "| # | Company | Role | Score | Why | Location | Apply |",
        "|---|---------|------|-------|-----|----------|-------|"
    ]

    for i, job in enumerate(scored_jobs, 1):
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown Role")
        score = job.get("score", 0)
        reason = job.get("reason", "")
        location = job.get("location", "")
        url = job.get("url", "#")
        lines.append(
            f"| {i} | {company} | {title} | {score}/5 | {reason} | {location} | [Apply]({url}) |"
        )

    lines += [
        "\n---",
        "\n💡 *For deep research, tailored resume PDF, and cover letter on any role above:*",
        "```",
        "cd career-ops && claude --dangerously-skip-permissions",
        "/career-ops {paste job URL here}",
        "```",
        f"\n_Generated: {timestamp}_"
    ]

    with open(digest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Digest written to {digest_path} with {len(scored_jobs)} entries")

    return {
        "success": True,
        "reports_found": len(scored_jobs),
        "digest_path": digest_path,
        "timestamp": timestamp
    }