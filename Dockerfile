FROM python:3.12-slim

WORKDIR /app

# System deps for ib_insync (it pulls in tzdata via pandas at install time).
RUN apt-get update && apt-get install -y --no-install-recommends \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 5050
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5050"]
