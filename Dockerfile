# Use an official Python runtime as a base image
FROM python:3.11

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install required system dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libasound2 \
    libgbm-dev \
    libu2f-udev \
    libvulkan1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome options
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

# Set the working directory in the container
WORKDIR /app

# Copy the project files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the Flask app runs on
EXPOSE 5000

# Run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
