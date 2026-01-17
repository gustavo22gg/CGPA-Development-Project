FROM python:3.9-slim

# 1. Install dependencies
RUN apt-get update && apt-get install -y \
    wget curl gnupg unzip xvfb libxi6 libgconf-2-4 \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list && \
    apt-get update && apt-get install -y google-chrome-stable

# 3. Install ChromeDriver (The Safe Way)
RUN CHROME_MAJOR_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d . -f 1) && \
    DRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_MAJOR_VERSION}") && \
    wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${DRIVER_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /tmp && \
    # Move from the folder to the destination (Overwrite if needed)
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    # Make executable
    chmod +x /usr/local/bin/chromedriver && \
    # Clean up
    rm -rf /tmp/chromedriver*

ENV DISPLAY=:99
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:10000", "--timeout", "120", "app:app"]
