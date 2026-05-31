FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git curl ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip wheel \
 && pip install --no-cache-dir -r requirements.txt \
 && pip uninstall -y pyrogram || true \
 && pip install --force-reinstall --no-cache-dir "kurigram>=2.2.23" --no-deps \
 && pip install --no-cache-dir --upgrade "py-tgcalls>=2.2.12" "yt-dlp>=2026.3.17" "lyricsgenius"

# pyrogram.emoji stub
RUN python3 -c "import pyrogram, os; \
  p=os.path.join(os.path.dirname(pyrogram.__file__),'emoji.py'); \
  open(p,'w').write('FLAG_TURKEY=\"\\U0001F1F9\\U0001F1F7\"\nFLAG_GERMANY=\"\\U0001F1E9\\U0001F1EA\"\nFLAG_UNITED_KINGDOM=\"\\U0001F1EC\\U0001F1E7\"\nFLAG_RUSSIA=\"\\U0001F1F7\\U0001F1FA\"\nFLAG_FRANCE=\"\\U0001F1EB\\U0001F1F7\"\nFLAG_SPAIN=\"\\U0001F1EA\\U0001F1F8\"\nFLAG_ITALY=\"\\U0001F1EE\\U0001F1F9\"\nFLAG_CHINA=\"\\U0001F1E8\\U0001F1F3\"\nFLAG_INDONESIA=\"\\U0001F1EE\\U0001F1E9\"\nFLAG_SOUTH_KOREA=\"\\U0001F1F0\\U0001F1F7\"\nFLAG_UKRAINE=\"\\U0001F1FA\\U0001F1E6\"\nFLAG_BELARUS=\"\\U0001F1E7\\U0001F1FE\"\nFLAG_UZBEKISTAN=\"\\U0001F1FA\\U0001F1FF\"\n')"

COPY . /app
WORKDIR /app

CMD ["python3", "-m", "YukkiMusic"]
