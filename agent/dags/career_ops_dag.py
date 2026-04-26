import sys
import os
import yaml
import logging
from datetime import datetime, timedelta

sys.path.insert(0, "/opt/airflow/agent/tasks")

from airflow import DAG
from airflow.operators.python import PythonOperator

import scanner
import scorer
import aggregator
import notifier

logger = logging.getLogger(__name__)

CONFIG_PATH = "/opt/airflow/agent/config/agent_config.yml"
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

INTERVAL_DAYS = config["schedule"]["interval_days"]
DIGEST_OUTPUT = config["digest"]["output_path"]

default_args = {
    "owner": "ryan",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}

with DAG(
    dag_id="career_ops_agent",
    description="Autonomous job search — scrapes via Apify, scores via Claude API, delivers digest via Telegram",
    default_args=default_args,
    start_date=datetime(2026, 4, 26),
    catchup=False,
    schedule_interval=f"0 8 */{INTERVAL_DAYS} * *" if INTERVAL_DAYS > 1 else "@daily",
    tags=["career", "agent", "jobs"]
) as dag:

    def task_scan(**context):
        result = scanner.run_scan(config)
        if not result["success"]:
            raise RuntimeError("Scan failed")
        context["ti"].xcom_push(key="jobs", value=result["jobs"])
        context["ti"].xcom_push(key="job_count", value=result["count"])
        logger.info(f"Scan complete — {result['count']} jobs found")

    def task_score(**context):
        jobs = context["ti"].xcom_pull(key="jobs", task_ids="scan_portals")
        if not jobs:
            logger.info("No jobs to score — skipping")
            context["ti"].xcom_push(key="scored_jobs", value=[])
            return
        result = scorer.score_jobs(jobs, config)
        context["ti"].xcom_push(key="scored_jobs", value=result["scored_jobs"])
        logger.info(f"Scoring complete — {len(result['scored_jobs'])} qualified jobs")

    def task_aggregate(**context):
        scored_jobs = context["ti"].xcom_pull(key="scored_jobs", task_ids="score_jobs")
        result = aggregator.aggregate_reports(
            scored_jobs=scored_jobs or [],
            output_path=DIGEST_OUTPUT
        )
        context["ti"].xcom_push(key="digest_path", value=result["digest_path"])

    def task_notify(**context):
        digest_path = context["ti"].xcom_pull(key="digest_path", task_ids="aggregate")
        result = notifier.send_digest(
            digest_path=digest_path,
            bot_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
            chat_id=os.environ.get("TELEGRAM_CHAT_ID")
        )
        if not result["success"]:
            raise RuntimeError(f"Notification failed: {result['error']}")

    scan_portals = PythonOperator(
        task_id="scan_portals",
        python_callable=task_scan,
        provide_context=True
    )

    score_jobs_task = PythonOperator(
        task_id="score_jobs",
        python_callable=task_score,
        provide_context=True
    )

    aggregate = PythonOperator(
        task_id="aggregate",
        python_callable=task_aggregate,
        provide_context=True
    )

    notify = PythonOperator(
        task_id="notify",
        python_callable=task_notify,
        provide_context=True
    )

    scan_portals >> score_jobs_task >> aggregate >> notify