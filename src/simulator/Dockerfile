FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN mkdir -p src && pip install --no-cache-dir .

COPY src/simulator/ .

CMD ["python", "simulate.py"]
