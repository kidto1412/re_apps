# syntax=docker/dockerfile:1
FROM python:3.11-alpine

WORKDIR /app

# Copy application files
COPY schema_sqlite.py .
COPY mock_backend.py .
COPY mobile_pos_client.py .
COPY pos_cli.py .
COPY receipt_generator.py .
COPY api_specification.json .
COPY swagger_ui.html .

# Initialize schema and seed data
RUN python3 -c "from schema_sqlite import Database; db = Database('pos_database.db'); db.seed_defaults(); db.close()"

EXPOSE 5000

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/product')" || exit 1

ENTRYPOINT ["python3", "mock_backend.py"]
