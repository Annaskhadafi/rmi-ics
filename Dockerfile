# Gunakan image Python yang stabil
FROM python:3.11-slim

# Install dependencies sistem untuk Selenium dan Chrome/Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables agar Selenium menemukan Chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir \
    beautifulsoup4 \
    pandas \
    selenium \
    requests \
    openpyxl \
    lxml \
    plotly \
    kaleido

# Berikan izin eksekusi ke semua script python
RUN chmod +x *.py

# Container akan tetap hidup agar Cron Job Dokploy bisa memanggil script di dalamnya
CMD ["tail", "-f", "/dev/null"]
