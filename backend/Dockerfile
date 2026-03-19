FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Single worker is suitable for development/class use.
# For production, set --workers based on available CPU cores.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
