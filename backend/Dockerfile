# Imagem da API do SafeMask (PI-III #232).
# Tesseract com portugues, para PDF escaneado. Sem torch: o NER fica de fora
# (requirements-ia.txt), como no deploy.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# O script precisa de fim de linha LF mesmo se o clone for do Windows.
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
