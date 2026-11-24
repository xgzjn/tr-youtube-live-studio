# TR YouTube 24H Live Studio — Docker (for Render / Railway / any VPS with Docker)
# No apt commands for you to type: the platform builds this image.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==22.0.0
COPY backend.py .env.example ./
COPY frontend ./frontend
RUN mkdir -p uploads data
ENV HOST=0.0.0.0 PORT=5000
EXPOSE 5000
# Render/Railway set $PORT themselves; gunicorn serves the Flask app.
CMD ["sh", "-c", "gunicorn backend:app --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 300"]
