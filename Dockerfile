# Python bazasini olamiz
FROM python:3.10-slim

# FFmpeg va kerakli tizim asboblarini o'rnatamiz
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 && apt-get clean

# Ishchi papkani yaratamiz
WORKDIR /app

# Kutubxonalar ro'yxatini ko'chirib, o'rnatamiz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Barcha kodlarni ko'chiramiz
COPY . .

# Botni ishga tushiramiz
CMD ["python", "main.py"]
