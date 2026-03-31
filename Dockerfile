FROM python:3.12-slim

# Tizim paketlarini o'rnatish
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Avval requirements ni copy qilib o'rnatamiz (cache uchun yaxshi)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Keyin qolgan kodni copy qilamiz
COPY . .

# Bot tokenni muhit o'zgaruvchisi sifatida qabul qilish
ENV BOT_TOKEN=""

CMD ["python", "bot.py"]