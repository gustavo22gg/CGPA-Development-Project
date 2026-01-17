# Use an official lightweight Python image.
FROM python:3.9-slim

# Install system dependencies for Chrome and ChromeDriver.
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    && rm -rf /var/lib/apt/lists/*

# Add Google’s official GPG key and set up the Chrome repository.
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list && \
    apt-get update && apt-get install -y google-chrome-stable

# Install the latest ChromeDriver matching the installed Chrome.
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /tmp && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver*

# Set the DISPLAY environment variable (required for headless operation in some cases).
ENV DISPLAY=:99

# Set the working directory.
WORKDIR /app

# Copy the dependency list and install Python packages.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code.
COPY . .

# Expose the port that your Flask app will run on.
EXPOSE 5000

# Run the Flask application.
CMD ["gunicorn", "-b", "0.0.0.0:10000", "--timeout", "120", "app:app"]
