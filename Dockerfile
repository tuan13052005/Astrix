# Tùy chọn: dùng Dockerfile để deploy đảm bảo ffmpeg luôn có sẵn,
# bất kể nền tảng (Railway, Render, Fly.io đều hỗ trợ "Deploy from
# Dockerfile"). Nếu bạn đang dùng Nixpacks (Railway mặc định) thì
# dùng nixpacks.toml thay vì file này.

FROM python:3.11-slim

# Cài ffmpeg từ apt (bắt buộc để phát audio trong voice channel)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libopus0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
