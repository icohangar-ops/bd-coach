# LiteLLM proxy image with extra deps the BD Coach hooks need
# (cubiczan-resilience + asyncpg for the Postgres audit hook).
FROM ghcr.io/berriai/litellm:main-stable

COPY requirements.txt /tmp/hook-requirements.txt
RUN pip install --no-cache-dir -r /tmp/hook-requirements.txt
