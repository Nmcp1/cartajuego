FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libpq5 ayuda con Postgres; build-essential por si alguna dependencia lo requiere
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render usa $PORT; Daphne sirve HTTP + WS desde ASGI :contentReference[oaicite:2]{index=2}
CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput || true; daphne -b 0.0.0.0 -p ${PORT:-10000} config.asgi:application"]
