import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> list[int]:
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            ids.append(int(part))
    return ids


@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    payments_provider_token: str = os.getenv("PAYMENTS_PROVIDER_TOKEN", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    admin_ids: list[int] = field(
        default_factory=lambda: _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    )
    admin_login: str = os.getenv("ADMIN_LOGIN", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    restaurant_name: str = os.getenv("RESTAURANT_NAME", "Заведение")
    currency: str = os.getenv("CURRENCY", "RUB")  # ISO 4217 code for Telegram Payments


config = Config()

if not config.bot_token:
    raise RuntimeError("BOT_TOKEN не задан. Проверьте файл .env")
if not config.database_url:
    raise RuntimeError("DATABASE_URL не задан. Проверьте файл .env")
