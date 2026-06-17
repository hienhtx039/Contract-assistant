FROM python:3.10-bookworm

ARG DEBIAN_FRONTEND=noninteractive

USER root

# Install system dependencies: nginx + supervisor to satisfy AgentBase port 8080 + /health requirement
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    curl \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Update pip
RUN pip install --no-cache-dir -U "pip>=24"

WORKDIR /app

# Copy requirements first (better caching)
COPY requirements_interview.txt /app/
RUN pip install --no-cache-dir -r requirements_interview.txt

# Copy application code
COPY . /app

# nginx: allow non-root to write pid/logs
RUN mkdir -p /var/log/nginx /var/lib/nginx/body /var/lib/nginx/fastcgi \
    && chmod -R 777 /var/log/nginx /var/lib/nginx /run

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Streamlit config
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_CLIENT_LOGGER_LEVEL=error
ENV STREAMLIT_LOGGER_LEVEL=error

# AgentBase Runtime requires port 8080 (nginx proxies to Streamlit on 8501)
EXPOSE 8080

# Health check via AgentBase-required /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# supervisord manages both nginx (port 8080) and streamlit (port 8501)
CMD ["supervisord", "-c", "/app/supervisord.conf"]
