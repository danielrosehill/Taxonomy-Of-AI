FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/
RUN uv pip install --system --no-cache -r /tmp/requirements.txt
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user HF_HOME=/home/user/.cache/huggingface
WORKDIR /home/user/app
COPY --chown=user app.py index.html ./
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
