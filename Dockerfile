FROM apache/airflow:2.9.1-python3.11

USER root

# Install system dependencies + Node.js (required for Claude CLI and career-ops)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install career-ops Node dependencies
COPY --chown=airflow:root career-ops/package*.json /opt/airflow/career-ops/
RUN cd /opt/airflow/career-ops && npm install

# Install Playwright browsers
RUN npx playwright install chromium --with-deps || true

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt