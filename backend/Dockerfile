FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure start script has executable permissions
RUN chmod +x scripts/start.sh

EXPOSE 8000

ENV PYTHONPATH=/app

CMD ["./scripts/start.sh"]
