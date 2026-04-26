import os
import pytest
from datetime import datetime
from pathlib import Path
from agent.tasks.aggregator import aggregate_reports


@pytest.fixture
def reports_dir(tmp_path):
    """Creates 3 sample career-ops report files in a temp directory."""
    reports = tmp_path / "reports"
    reports.mkdir()

    samples = [
        ("001-google-2026-04-23.md", "# Data Engineer\n\n**URL:** https://careers.google.com/jobs/1\n\n## Summary\nStrong match for pipeline experience.\n\nScore: 4.5/5"),
        ("002-snowflake-2026-04-23.md", "# Analytics Engineer\n\n**URL:** https://careers.snowflake.com/jobs/2\n\n## Summary\nGood fit for dbt and Snowflake skills.\n\nScore: 4.0/5"),
        ("003-databricks-2026-04-23.md", "# Platform Engineer\n\n**URL:** https://databricks.com/jobs/3\n\n## Summary\nDecent match but missing Spark experience.\n\nScore: 3.2/5"),
    ]

    for filename, content in samples:
        (reports / filename).write_text(content, encoding="utf-8")

    return tmp_path


def test_aggregate_finds_all_reports(reports_dir, tmp_path):
    output_path = str(tmp_path / "digests")
    result = aggregate_reports(
        career_ops_path=str(reports_dir),
        output_path=output_path,
        since_hours=9999  # ensure all files are included
    )
    assert result["success"] is True
    assert result["reports_found"] == 3
    assert result["digest_path"] is not None
    assert os.path.exists(result["digest_path"])


def test_aggregate_digest_contains_companies(reports_dir, tmp_path):
    output_path = str(tmp_path / "digests")
    result = aggregate_reports(
        career_ops_path=str(reports_dir),
        output_path=output_path,
        since_hours=9999
    )
    with open(result["digest_path"], "r") as f:
        content = f.read()
    assert "Google" in content
    assert "Snowflake" in content
    assert "Databricks" in content


def test_aggregate_empty_directory(tmp_path):
    empty = tmp_path / "reports"
    empty.mkdir()
    result = aggregate_reports(
        career_ops_path=str(tmp_path),
        output_path=str(tmp_path / "digests"),
        since_hours=9999
    )
    assert result["success"] is True
    assert result["reports_found"] == 0
    assert result["digest_path"] is None


def test_aggregate_skips_malformed_files(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "001-broken-2026-04-23.md").write_text(
        "this file has no parseable content %%%", encoding="utf-8"
    )
    result = aggregate_reports(
        career_ops_path=str(tmp_path),
        output_path=str(tmp_path / "digests"),
        since_hours=9999,
        min_score=0.0
    )
    assert result["success"] is True