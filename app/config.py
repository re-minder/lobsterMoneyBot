import os
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Config:
    bot_token: str
    owner_ids: List[int]
    db_path: Path
    data_dir: Path
    bot_username: str


def _parse_owner_ids(raw: str) -> List[int]:
    if not raw:
        return []
    ids: List[int] = []
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            ids.append(int(piece))
        except ValueError:
            continue
    return ids


def load_config() -> Config:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    data_dir = Path(os.getenv("DATA_DIR", "data")).resolve()
    db_path = Path(os.getenv("DB_PATH", str(data_dir / "bot.db"))).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    owner_ids = _parse_owner_ids(os.getenv("OWNER_IDS", ""))
    bot_username = os.getenv("BOT_USERNAME", "").strip()

    return Config(
        bot_token=token,
        owner_ids=owner_ids,
        db_path=db_path,
        data_dir=data_dir,
        bot_username=bot_username,
    )


