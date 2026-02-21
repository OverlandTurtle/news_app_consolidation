FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (mysqlclient build support)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       pkg-config \
       default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

# Runtime config is supplied via environment variables (see .env.example / README).
# Migrations are run explicitly (not at container start) to avoid DB surprises.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
