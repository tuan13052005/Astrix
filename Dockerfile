# Tùy chọn: dùng Dockerfile để deploy đảm bảo ffmpeg/opus/libsodium
# luôn có sẵn, bất kể nền tảng (Railway, Render, Fly.io đều hỗ trợ
# "Deploy from Dockerfile"). Nếu bạn đang dùng Nixpacks (Railway mặc
# định) thì dùng nixpacks.toml thay vì file này.

FROM python:3.11-slim

# Cài ffmpeg (giải mã/stream audio), libopus0 (encode voice Discord),
# libsodium23 (mã hoá voice cho PyNaCl) từ apt
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libopus0 libsodium23 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]