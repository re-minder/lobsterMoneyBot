## Inline Telegram Video Bot (PEX, SQLite)

An inline Telegram bot that returns cached videos based on a keyphrase. Owners can teach the bot new (phrase, file_id) pairs via `/remember <phrase>` by replying to a video message. Packaged as a single-file PEX for easy server deployment (no pip/venv needed on the server). Uses SQLite (file-based) for storage.

### Features
- **Inline mode**: type `@YourBot <phrase>` to get matching videos
- **Commands**:
  - `/start`: owners get setup instructions; non-owners get usage help
  - `/remember <phrase>`: reply to a video to save it with the phrase
  - `/status [page]`: list stored phrases/videos with pagination, and who saved them (owners only)
  - `/add_owner <user_id>`: add a new owner (owners only)
  - `/delete <phrase>`: delete mapping(s) you own for the given phrase (owners only)
- **Search**: case-insensitive, prefix and fuzzy (subsequence) matching
- **Results**: returns top 10 matches
- **Storage**: SQLite file (no server installs)
- **Packaging**: PEX single-file artifact

### Requirements
- Python 3.8+ (server has 3.8.10 per your note)

### Setup (Local)
1. Create and fill `.env` from example:
```
cp .env.example .env
```
Set `TELEGRAM_BOT_TOKEN` and `OWNER_IDS`.

2. Create virtualenv and install deps (for local dev only):
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Run locally:
```
python -m app
```

### Build PEX
```
./scripts/build_pex.sh
```
Produces `dist/bot.pex`.

### Run on Server (no installs)
1. Copy PEX:
```
scp dist/bot.pex user@server:/opt/bot/
```
2. Set env vars and run:
```
ssh user@server
cd /opt/bot
export TELEGRAM_BOT_TOKEN=YOUR_TOKEN
export OWNER_IDS=123456789,987654321
./bot.pex
```
Data will be stored in `data/bot.db` in the working directory (created automatically).

### Notes
- To teach a video: owner sends a video, then reply to that video with `/remember my phrase`.
- Inline usage for everyone: `@YourBot my phrase`.
- `/status` shows 50 entries per page. Use `/status 2`, `/status 3`, etc.

### Why not Vercel?
Vercel is typically used for HTTP webhook hosting. Since you have a dedicated server and prefer no installs, the PEX approach is sufficient and Vercel is not required. If later you want a webhook endpoint or a web admin UI, we can add a small Vercel (or server-hosted) HTTP service.


