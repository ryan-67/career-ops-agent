# career-ops-agent

An autonomous job search pipeline that scrapes job listings, scores them against your resume using the Claude API, and delivers ranked daily digests via Telegram — orchestrated with Apache Airflow on Docker.

---

## How It Works

```
Airflow Scheduler (every 2 days at 8am)
    │
    ▼
Task 1: scan_portals
    └── Apify scrapes LinkedIn + Indeed for target roles
    └── Filters by title keywords and deduplicates
    │
    ▼
Task 2: score_jobs
    └── Single Claude API call batch-scores all jobs against cv.md
    └── Filters to top results above minimum score threshold
    │
    ▼
Task 3: aggregate
    └── Builds structured markdown digest with ranked results
    └── Saves to agent/digests/digest-YYYY-MM-DD.md
    │
    ▼
Task 4: notify
    └── Sends digest via Telegram Bot API
    └── You review recommendations and apply manually
```

**Tier 2 (manual, on-demand):** For roles you want to pursue after reading the digest, run `/career-ops {url}` in Claude Code inside the `career-ops/` directory to get a full evaluation report, ATS-optimized resume PDF, and cover letter draft.

---

## Tech Stack

- **Orchestration:** Apache Airflow 2.9.1
- **Containerization:** Docker + Docker Compose
- **Scraping:** Apify (LinkedIn Jobs + Indeed scrapers)
- **Scoring:** Anthropic Claude API (claude-haiku — batch scoring)
- **Notification:** Telegram Bot API
- **Deep Evaluation:** career-ops (Claude Code slash commands)
- **Language:** Python 3.11

---

## Project Structure

```
career-ops-agent/
├── agent/
│   ├── dags/
│   │   └── career_ops_dag.py      # Airflow DAG — 4-task pipeline
│   ├── tasks/
│   │   ├── scanner.py             # Apify scraping (LinkedIn + Indeed)
│   │   ├── scorer.py              # Claude API batch scoring
│   │   ├── aggregator.py          # Digest builder
│   │   └── notifier.py            # Telegram delivery
│   ├── config/
│   │   └── agent_config.yml       # Schedule, scoring, filter config
│   ├── digests/                   # Generated digest files
│   └── tests/
│       ├── test_aggregator.py
│       └── test_notifier.py
├── career-ops/                    # Submodule — deep evaluation engine
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env                           # Secrets (not committed)
```

---

## Prerequisites

- Windows 11 with WSL2 enabled
- Docker Desktop (WSL2 backend)
- Anthropic API key — [console.anthropic.com](https://console.anthropic.com)
- Apify account + API token — [apify.com](https://apify.com)
- Telegram Bot token + chat ID — create via [@BotFather](https://t.me/botfather)

---

## Setup

### 1. Clone the repo

```powershell
git clone https://github.com/ryan-67/career-ops-agent.git
cd career-ops-agent
```

### 2. Create your `.env` file

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
APIFY_API_TOKEN=apify_api_your-token-here
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_CHAT_ID=your-chat-id-here
AIRFLOW_UID=50000
AIRFLOW_GID=0
_AIRFLOW_WWW_USER_USERNAME=admin
_AIRFLOW_WWW_USER_PASSWORD=admin
```

### 3. Add your resume

Place your resume as `career-ops/cv.md` in markdown format.

### 4. Configure your profile

Edit `career-ops/config/profile.yml` with your target roles, skills, and compensation preferences.

### 5. Configure portals (optional)

Edit `career-ops/portals.yml` to customize which companies career-ops scans for Tier 2 deep evaluations.

### 6. Configure the agent

Edit `agent/config/agent_config.yml` to set:
- Scraping queries and sources
- Scoring thresholds
- Schedule frequency
- Notification preferences

### 7. Initialize and launch

```powershell
# First time only
docker compose up airflow-init

# Start everything
docker compose up --build -d

# Verify containers are healthy
docker compose ps
```

### 8. Access Airflow UI

Open `http://localhost:8080` — login with `admin / admin`

Enable the `career_ops_agent` DAG and trigger a manual run to test.

---

## Configuration

Key settings in `agent/config/agent_config.yml`:

```yaml
schedule:
  interval_days: 2          # Run every N days
  start_time: "08:00"       # Time of day (local)

scraping:
  max_results_per_query: 25 # Jobs per search query

scoring:
  min_score: 3.5            # Minimum fit score (1-5) to include in digest
  max_results_in_digest: 15 # Max jobs per Telegram message

filters:
  exclude_keywords:         # Job titles to skip
    - "director"
    - "manager"
    - "senior staff"
```

---

## Daily Usage

1. **Receive Telegram digest** every 2 days with ranked job recommendations
2. **Review the list** — each entry includes company, role, fit score, reason, location, and apply link
3. **Apply directly** using the links provided
4. **Deep dive on top roles** using Tier 2:

```bash
cd career-ops
claude --dangerously-skip-permissions
/career-ops {paste job URL}
```

This generates a full evaluation report, ATS-optimized resume PDF tailored to the role, and a cover letter draft.

---

## After a PC Restart

Docker containers stop when your PC shuts down. To bring them back up:

```powershell
cd D:\Projects\career-ops-agent
docker compose up -d
```

To avoid this, enable **"Start Docker Desktop when you log in"** in Docker Desktop settings. Containers are configured with `restart: unless-stopped` and will come back automatically once Docker starts.

---

## Running Tests

```powershell
docker compose exec airflow-webserver pytest /opt/airflow/agent/tests -v
```

---

## Cost Estimate

| Component | Cost |
|-----------|------|
| Apify scraping (~100 jobs) | ~$0.05/run |
| Claude API batch scoring | ~$0.03/run |
| Telegram delivery | Free |
| **Per run total** | **~$0.08** |
| **Monthly (15 runs)** | **~$1.20** |

Set a spending limit at [console.anthropic.com](https://console.anthropic.com) to avoid surprises.

---

## Architecture Notes

- **Tier 1 (this repo):** Cheap autonomous discovery — Apify scrapes, Claude batch-scores, Telegram delivers
- **Tier 2 (career-ops submodule):** On-demand deep evaluation — full report, tailored PDF, cover letter per role
- Airflow uses `LocalExecutor` with PostgreSQL metadata backend
- All secrets loaded from `.env` — never committed to git
- Digests saved locally to `agent/digests/` for reference

---

## Related

- [career-ops](https://github.com/santifer/career-ops) — the deep evaluation engine powering Tier 2
