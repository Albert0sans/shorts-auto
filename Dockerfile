# Use NVIDIA CUDA base image (includes GPU drivers)
# Ubuntu 22.04 comes with Python 3.10, which works well with WhisperX
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# 1. Install Python, pip, ffmpeg, and git
# ffmpeg: Required by WhisperX for audio
# git: Required to install WhisperX from GitHub
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Install Python dependencies
COPY requirements.txt .
# Upgrade pip first to avoid issues
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# 4. Copy your function code
COPY . .

# 5. Define entry point
ENV PORT=8080
# Use python3 explicitly
CMD ["functions-framework", "--target=createShortsJob"]