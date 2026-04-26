# Career-Ops Agent

An autonomous job search pipeline that runs on Apache Airflow. Every few days it scrapes LinkedIn and Indeed, scores each listing against your résumé using the Claude AI API, and delivers a ranked digest straight to Telegram — no manual searching required.

## How It Works

```
Airflow DAG (every N days)
  └─► scan_portals   — Apify scrapes LinkedIn + Indeed
  └─► score_jobs     — Claude AI scores each listing vs. your CV (1–5)
  └─► aggregate      — builds a ranked Markdown digest
  └─► notify         — pushes digest to Telegram
```

On each run the agent:
1. Scrapes job portals via [Apify](https://apify.com/) actors (no brittle Selenium required)
2. Filters out seniority levels and keywords you don't want (director, VP, clearance, etc.)
3. Sends all listings to Claude as a single batch prompt — cheap and fast
4. Returns only roles scored ≥ 3.5 / 5.0, sorted by fit
5. Splits long digests across multiple Telegram messages automatically

## Stack

| Layer | Tech |
|---|---|
| Orchestration | Apache Airflow 2.9 (LocalExecutor) |
| Scraping | Apify (LinkedIn + Indeed actors) |
| AI Scoring | Anthropic Claude API (Haiku 4.5) |
| Notifications | Telegram Bot API |
| Infrastructure | Docker Compose + PostgreSQL 15 |

## Project Structure

```
career-ops-agent/
├── agent/
│   ├── dags/
│   │   └── career_ops_dag.py     # Airflow DAG definition
│   ├── tasks/
│   │   ├── scanner.py            # Apify scraping (LinkedIn + Indeed)
│   │   ├── scorer.py             # Claude AI batch scoring
│   │   ├── aggregator.py         # Digest builder
│   │   └── notifier.py           # Telegram delivery
│   ├── config/
│   │   └── agent_config.yml      # Search queries, scoring thresholds, schedule
│   └── tests/
│       ├── test_aggregator.py
│       └── test_notifier.py
├── career-ops/                   # CV + application tracker (submodule)
├── Dockerfile                    # Extends apache/airflow:2.9.1
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Quickstart

### Prerequisites

- Docker Desktop
- Accounts: [Apify](https://apify.com/), [Anthropic](https://console.anthropic.com/), Telegram bot token

### 1. Clone and configure

```bash
git clone https://github.com/67rkim/career-ops-agent.git
cd career-ops-agent
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Edit your search config

Open `agent/config/agent_config.yml` and set your target roles, locations, and scoring thresholds:

```yaml
scraping:
  linkedin_queries:
    - query: "Data Engineer"
      location: "United States"
  max_results_per_query: 25

scoring:
  min_score: 3.5          # Only show jobs scoring above this
  max_results_in_digest: 15

schedule:
  interval_days: 2        # Run every 2 days
```

### 3. Add your résumé

Place `cv.md` inside the `career-ops/` directory (Markdown format). The scorer reads this on every run to evaluate fit.

### 4. Start Airflow

```bash
# First run only — initializes DB and admin user
docker compose up airflow-init

# Start all services
docker compose up -d

# Open Airflow UI
open http://localhost:8080
```

Unpause the `career_ops_agent` DAG in the Airflow UI, or trigger it manually.

## Configuration Reference

`agent/config/agent_config.yml` controls everything:

| Key | Default | Description |
|---|---|---|
| `schedule.interval_days` | `2` | How often the DAG runs |
| `scraping.sources` | `[linkedin, indeed]` | Portals to scrape |
| `scraping.max_results_per_query` | `25` | Listings pulled per search query |
| `scoring.min_score` | `3.5` | Minimum Claude score to include in digest |
| `scoring.max_results_in_digest` | `15` | Max roles sent to Telegram |
| `filters.exclude_keywords` | `[director, VP, ...]` | Title keywords to skip |

## Security

- All secrets are loaded from `.env` (gitignored)
- `.env.example` shows required keys — never contains real values
- Set a strong `FERNET_KEY` in `.env` before any production use

## License

MIT
