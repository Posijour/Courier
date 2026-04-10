from dataclasses import dataclass
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    supabase_url: str
    supabase_key: str
    supabase_timeout_seconds: float
    default_city: str
    default_account_slug: str
    weather_lat: float
    weather_lon: float
    weather_timezone: str
    project_timezone: ZoneInfo


def _with_default(name: str, default: str | None = None) -> str:
    value = os.getenv(name)
    if value:
        return value
    if default is not None:
        return default
    raise RuntimeError(f"Missing required environment variable: {name}")


def _load_timezone(name: str, value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(
            f"Invalid or unsupported timezone in {name}: {value}. "
            "Install the 'tzdata' package on Windows or provide a valid IANA timezone."
        ) from exc


settings = Settings(
    bot_token=_with_default("BOT_TOKEN"),
    supabase_url=_with_default("SUPABASE_URL"),
    supabase_key=_with_default("SUPABASE_KEY"),
    supabase_timeout_seconds=float(os.getenv("SUPABASE_TIMEOUT_SECONDS", "15")),
    default_city=os.getenv("DEFAULT_CITY", "Nis"),
    default_account_slug=os.getenv("DEFAULT_ACCOUNT_SLUG", "default-account"),
    weather_lat=float(os.getenv("WEATHER_LAT", "43.3209")),
    weather_lon=float(os.getenv("WEATHER_LON", "21.8958")),
    weather_timezone=os.getenv("WEATHER_TIMEZONE", "Europe/Belgrade"),
    project_timezone=_load_timezone("WEATHER_TIMEZONE", os.getenv("WEATHER_TIMEZONE", "Europe/Belgrade")),
)
