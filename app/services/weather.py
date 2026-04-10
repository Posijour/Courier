from dataclasses import dataclass
from decimal import Decimal

import httpx

from app.config import settings


@dataclass
class WeatherSnapshot:
    summary: str | None
    temp: Decimal | None
    rain: bool | None


WEATHER_CODES = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy rain showers",
    95: "Thunderstorm",
}


async def fetch_weather_snapshot() -> WeatherSnapshot:
    return await fetch_weather_snapshot_for_timezone(settings.weather_timezone)


async def fetch_weather_snapshot_for_timezone(timezone_name: str) -> WeatherSnapshot:
    params = {
        "latitude": settings.weather_lat,
        "longitude": settings.weather_lon,
        "current": "temperature_2m,rain,weather_code",
        "timezone": timezone_name,
    }
    url = "https://api.open-meteo.com/v1/forecast"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
        payload = response.json().get("current", {})
    except Exception:
        return WeatherSnapshot(summary=None, temp=None, rain=None)

    weather_code = payload.get("weather_code")
    summary = WEATHER_CODES.get(weather_code, "Unknown") if weather_code is not None else None
    temp = payload.get("temperature_2m")
    rain = payload.get("rain")
    return WeatherSnapshot(
        summary=summary,
        temp=Decimal(str(temp)) if temp is not None else None,
        rain=bool(rain) if rain is not None else None,
    )
