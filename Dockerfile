FROM python:3.9-slim

# Install Chrome dependencies (expanded list for reliability)
RUN apt-get update && apt-get install -y \
    wget curl gnupg unzip xvfb libxi6 libgconf-2-4 \
    fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libgcc1 \
    libglib2.0-0 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0 \
    libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 \
    libxext6 libxfixes3 libxrandr2 libxrender1 libxss1 libxtst6 lsb-release xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome Stable (modern key addition)
RUN curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-archive-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    # Verify installation (for build logs)
    google-chrome --version && \
    which google-chrome && \
    which google-chrome-stable

ENV DISPLAY=:99

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
# Use $PORT from environment (Render sets this)
CMD gunicorn -b 0.0.0.0:${PORT:-10000} --timeout 120 app:app
