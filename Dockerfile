FROM ghcr.io/astral-sh/uv:debian

# Install ffmpeg for pydub's audio conversion capabilities
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./pyproject.toml .
COPY ./uv.lock .
COPY ./README.md .
COPY ./.python-version .
COPY ./pocket_tts ./pocket_tts

RUN uv run pocket-tts --help

RUN uv pip install -e .[server]

CMD ["uv", "run", "pocket-tts", "serve", "--host", "0.0.0.0"]
