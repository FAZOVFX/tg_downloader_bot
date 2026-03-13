FROM python:3.10-slim

# Kerakli paketlarni o'rnatish
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# yt-dlp ni oxirgi versiyaga yangilash
RUN pip install --upgrade yt-dlp

CMD ["python", "main.py"]
