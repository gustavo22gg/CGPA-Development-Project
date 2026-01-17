FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    wget \
    unzip \
    xvfb \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN chromium --version && chromedriver --version && which chromedriver

CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT} --workers 1 --threads 1 --timeout 600 app:app"]
