FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 GHOST_DB=/data/ghost_signal.db
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ghost_signal ./ghost_signal
RUN mkdir -p /data && useradd --create-home ghost && chown ghost /data
USER ghost
EXPOSE 8000
CMD ["sh", "-c", "uvicorn ghost_signal.app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*"]
