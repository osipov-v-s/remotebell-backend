FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    mpg123 \
    alsa-utils \
    libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем ВСЕ файлы из текущей директории в /app
COPY . .

EXPOSE 8000

# Запускаем main.py из корня (не из папки app)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]