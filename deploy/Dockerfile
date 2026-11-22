FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN pip install fastapi "uvicorn[standard]" httpx openai pydantic python-dotenv pillow
COPY backend/race.py backend/server.py backend/wiki.py backend/og.py backend/topics.py backend/surprise_pairs.json backend/
COPY backend/assets backend/assets
COPY backend/sample-runs backend/sample-runs
COPY web web
WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
