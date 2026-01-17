FROM python:3.9-slim

# 1. Install Chrome dependencies
RUN apt-get update && apt-get install -y \
    wget curl gnupg unzip xvfb libxi6 libgconf-2-4 \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Google Chrome Stable
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list && \
    apt-get update && apt-get install -y google-chrome-stable

# (Deleted the manual ChromeDriver download block - Python handles it now)

ENV DISPLAY=:99
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:10000", "--timeout", "120", "app:app"]
