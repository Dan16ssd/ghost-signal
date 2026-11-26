"""Trusted public sources: Wikipedia (English + Lao) and Open-Meteo weather.

Both are free, need no API key and allow automated use with a clear User-Agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import httpx

from .config import settings


@dataclass
class Source:
    title: str
    text: str
    url: str


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=settings.http_timeout,
        headers={"User-Agent": settings.user_agent},
        follow_redirects=True,
    )


def wikipedia(query: str, lang: str = "en", limit: int = 3) -> list[Source]:
    """Search Wikipedia and return the intro summary of the best pages."""
    base = f"https://{lang}.wikipedia.org"
    out: list[Source] = []
    with _client() as http:
        r = http.get(
            f"{base}/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": limit,
                "format": "json",
            },
        )
        if r.status_code == 403:
            raise RuntimeError("Wikipedia refused the request: set GHOST_CONTACT (repo URL or email) in .env")
        r.raise_for_status()
        hits = r.json().get("query", {}).get("search", [])
        for hit in hits:
            title = hit["title"]
            s = http.get(f"{base}/api/rest_v1/page/summary/{quote(title.replace(' ', '_'), safe='')}")
            if s.status_code != 200:
                continue
            data = s.json()
            extract = (data.get("extract") or "").strip()
            if not extract:
                continue
            page = data.get("content_urls", {}).get("mobile", {}).get("page") or f"{base}/wiki/{quote(title)}"
            out.append(Source(title=title, text=extract, url=page))
    return out


WEATHER_CODES = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "cloudy",
    45: "fog", 48: "fog", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 80: "rain showers",
    81: "rain showers", 82: "violent rain showers", 95: "thunderstorm",
    96: "thunderstorm with hail", 99: "thunderstorm with hail",
}


def weather(city: str) -> str | None:
    """Short forecast text for a city, or None if the city is unknown."""
    with _client() as http:
        g = http.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "format": "json"},
        )
        g.raise_for_status()
        results = g.json().get("results") or []
        if not results:
            return None
        place = results[0]
        f = http.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                "timezone": "auto",
                "forecast_days": 2,
            },
        )
        f.raise_for_status()
        data = f.json()
    cur = data["current"]
    day = data["daily"]
    now = WEATHER_CODES.get(cur["weather_code"], "mixed")
    tmr = WEATHER_CODES.get(day["weather_code"][1], "mixed")
    return (
        f"{place['name']}: now {round(cur['temperature_2m'])}C, {now}. "
        f"Tomorrow {round(day['temperature_2m_min'][1])}-{round(day['temperature_2m_max'][1])}C, {tmr}, "
        f"rain chance {day['precipitation_probability_max'][1] or 0}%. (Open-Meteo)"
    )
