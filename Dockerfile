# Dockerfile for Open-Source Incident Management System
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Seed initial database
RUN python seed_data.py

# Expose web portal port
EXPOSE 5000

ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Run Flask service
CMD ["python", "app.py"]
