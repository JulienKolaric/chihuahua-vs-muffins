"""Travel desk MCP — public APIs (Open-Meteo + REST Countries). No API key."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from typing import Any

import uvicorn
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

PORT = int(os.environ.get("PORT", "8080"))
TIMEOUT = 15

WMO = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "rime fog",
    51: "light drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "snow",
    80: "rain showers",
    95: "thunderstorm",
}

mcp = FastMCP(
    "travel-desk",
    instructions=(
        "Call get_trip_brief for weather. Call get_public_holidays for national holidays. "
        "Do not invent weather, capitals, or holiday dates."
    ),
)


def _http_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "genai-agent-travel-mcp/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"error": f"HTTP {exc.code} for {url}"}
    except Exception as exc:  # noqa: BLE001 — lab: show any egress/DNS failure
        return {"error": f"{type(exc).__name__}: {exc}"}


def _geocode(query: str) -> dict:
    q = urllib.parse.quote(query.strip())
    data = _http_json(
        f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1&language=en&format=json"
    )
    if data.get("error"):
        return data
    results = data.get("results") or []
    if not results:
        return {"error": f"No place found for {query!r}"}
    r = results[0]
    return {
        "name": r.get("name"),
        "country": r.get("country"),
        "admin1": r.get("admin1"),
        "latitude": r.get("latitude"),
        "longitude": r.get("longitude"),
        "timezone": r.get("timezone"),
        "country_code": r.get("country_code"),
    }


@mcp.tool
def lookup_place(query: str) -> str:
    """Geocode a city or place name (Open-Meteo, no API key). Returns name, country, lat, lon."""
    geo = _geocode(query)
    return json.dumps(geo, ensure_ascii=False)


@mcp.tool
def get_trip_brief(destination: str) -> str:
    """Travel brief for a destination: coordinates, 3-day weather (Open-Meteo), capital/currency (REST Countries)."""
    geo = _geocode(destination)
    if geo.get("error"):
        return json.dumps(geo, ensure_ascii=False)
    lat, lon = geo["latitude"], geo["longitude"]
    wx = _http_json(
        "https://api.open-meteo.com/v1/forecast?"
        + urllib.parse.urlencode(
            {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
                "forecast_days": 3,
            }
        )
    )
    country = geo.get("country") or destination
    cq = urllib.parse.quote(str(country))
    ctry = _http_json(
        f"https://restcountries.com/v3.1/name/{cq}?fields=name,capital,region,currencies"
    )
    country_bit: dict = {}
    if isinstance(ctry, list) and ctry:
        item = ctry[0]
        curr = item.get("currencies") or {}
        country_bit = {
            "official_name": (item.get("name") or {}).get("official"),
            "capital": (item.get("capital") or [None])[0],
            "region": item.get("region"),
            "currencies": list(curr.keys()),
        }
    elif isinstance(ctry, dict) and ctry.get("error"):
        country_bit = {"error": ctry["error"]}

    daily = (wx.get("daily") or {}) if isinstance(wx, dict) else {}
    days = []
    dates = daily.get("time") or []
    for i, day in enumerate(dates):
        days.append(
            {
                "date": day,
                "tmax_c": (daily.get("temperature_2m_max") or [None])[i]
                if i < len(daily.get("temperature_2m_max") or [])
                else None,
                "tmin_c": (daily.get("temperature_2m_min") or [None])[i]
                if i < len(daily.get("temperature_2m_min") or [])
                else None,
                "precip_mm": (daily.get("precipitation_sum") or [None])[i]
                if i < len(daily.get("precipitation_sum") or [])
                else None,
            }
        )
    current = (wx.get("current_weather") or {}) if isinstance(wx, dict) else {}
    code = current.get("weathercode")
    brief = {
        "place": geo,
        "now": {
            "temp_c": current.get("temperature"),
            "wind_kmh": current.get("windspeed"),
            "weather": WMO.get(code, code),
        },
        "next_days": days,
        "country": country_bit,
        "sources": ["Open-Meteo", "REST Countries"],
    }
    if isinstance(wx, dict) and wx.get("error"):
        brief["weather_error"] = wx["error"]
    return json.dumps(brief, ensure_ascii=False)


@mcp.tool
def get_public_holidays(country_or_city: str, year: int | None = None) -> str:
    """National public holidays (Nager.Date, no API key). Pass ISO-2 like PT or a city like Lisbon."""
    raw = str(country_or_city).strip()
    code = raw.upper()
    if len(code) != 2 or not code.isalpha():
        geo = _geocode(raw)
        if geo.get("error"):
            return json.dumps(geo, ensure_ascii=False)
        code = str(geo.get("country_code") or "").upper()
        if len(code) != 2:
            return json.dumps(
                {"error": f"No ISO country code for {raw!r}", "place": geo},
                ensure_ascii=False,
            )
    y = date.today().year
    if year is not None:
        try:
            y = int(year)
        except (TypeError, ValueError):
            pass
    data = _http_json(f"https://date.nager.at/api/v3/PublicHolidays/{y}/{code}")
    if isinstance(data, dict) and data.get("error"):
        return json.dumps(data, ensure_ascii=False)
    if not isinstance(data, list):
        return json.dumps({"error": "Unexpected Nager.Date payload", "raw": data}, ensure_ascii=False)
    holidays = [
        {
            "date": h.get("date"),
            "name": h.get("name"),
            "local_name": h.get("localName"),
            "global": h.get("global"),
        }
        for h in data
        if isinstance(h, dict)
    ]
    return json.dumps(
        {
            "country_code": code,
            "year": y,
            "count": len(holidays),
            "holidays": holidays,
            "source": "Nager.Date",
        },
        ensure_ascii=False,
    )


async def health(_request):
    return JSONResponse(
        {
            "status": "ok",
            "mcp": "/mcp",
            "hint": "Tools: lookup_place, get_trip_brief, get_public_holidays. Public APIs, no key.",
        }
    )


_http_kw: dict = {
    "transport": "streamable-http",
    "path": "/mcp",
    "stateless_http": True,
}
try:
    mcp_asgi = mcp.http_app(**_http_kw, host_origin_protection=False)
except TypeError:
    mcp_asgi = mcp.http_app(**_http_kw)
app = Starlette(
    routes=[
        Route("/", health),
        Route("/healthz", health),
        Mount("/", app=mcp_asgi),
    ],
    lifespan=mcp_asgi.lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["mcp-session-id", "Mcp-Session-Id"],
)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
