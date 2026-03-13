# Python-ning yengil versiyasini tanlaymiz
FROM python:3.10-slim

# Tizimga kerakli uskunalarni o'rnatamiz: 
# 1. ffmpeg - videolarni MP4 formatga keltirish uchun
# 2. nodejs - YouTube algoritmlari (JavaScript) ishlashi uchun
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Ishchi papkani yaratamiz
WORKDIR /app

# Kutubxonalar ro'yxatini nusxalaymiz va o'rnatamiz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Barcha fayllarni (main.py, cookies.txt va h.k.) nusxalaymiz
COPY . .

# Botni ishga tushirish buyrug'i
CMD ["python", "main.py"]
