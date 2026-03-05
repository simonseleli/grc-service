FROM python:3.11-slim

LABEL maintainer="FCC Digital Team"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/logs /app/media /app/staticfiles

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8006", "--workers", "4", "--timeout", "120"]
