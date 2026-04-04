"""
flight_search.py - Lightweight, reusable nonstop flight search skeleton

Notes:
- This is a stable, reusable core for the flight-search-lite skill.
- It is designed to be fed user inputs (origin, destination, dates, etc.)
- It normalizes cities to IATA codes when possible and returns a small,
  consistent table of nonstop options. Prices are included only when fresh data
  is readable from sources; otherwise they are shown as not available.
"""

from typing import Optional, List, Dict
import datetime as dt

try:
    from . import helpers
except ImportError:
    import helpers

import json
import os
from pathlib import Path

SCHEMA = json.loads(
    (Path(__file__).with_name("schema.json")).read_text(encoding="utf-8")
)

def search_flights(
    origin: str,
    destination: str,
    depart_date: str,
    return_date: Optional[str] = None,
    cabin: str = "economy",
    passengers: int = 1,
    nonstop_only: bool = True,
) -> List[str]:

    import os
    import requests

    api_key = os.getenv("SERPAPI_API_KEY")

    if not api_key:
        return ["API key not configured"]

    # Allow currency override via environment variable; default to USD
    currency = os.getenv("SERPAPI_CURRENCY", "USD")
    # Fallback: allow a simple file-based override if environment flags are unavailable
    if currency == "USD":
        override_path = Path(__file__).with_name("CURRENCY_OVERRIDE")
        if override_path.exists():
            try:
                with open(override_path, "r", encoding="utf-8") as f:
                    file_currency = f.read().strip()
                    if file_currency:
                        currency = file_currency
            except Exception:
                pass

    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": depart_date,
        "currency": currency,
        "hl": "en",
        "gl": "sg",
        "api_key": api_key,
    }

    if return_date:
        params["return_date"] = return_date

    if nonstop_only:
        params["stops"] = "0"

    try:
        response = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return [f"API request failed: {str(e)}"]

    results = []
    seen = set()

    for group in data.get("best_flights", []):
        price = group.get("price")

        flights = group.get("flights", [])
        if not flights:
            continue

        # Filter nonstop (1 leg only)
        if nonstop_only and len(flights) != 1:
            continue

        first = flights[0]

        airline = first.get("airline", "Unknown")
        duration_mins = group.get("total_duration") or first.get("duration")

        # Convert minutes → "6h 25m"
        if isinstance(duration_mins, int):
            hours = duration_mins // 60
            mins = duration_mins % 60
            duration = f"{hours}h {mins}m"
        else:
            duration = "duration not available"

        if price is not None:
            line = f"• {airline} — {duration} — Nonstop — from ${price}"
        else:
            line = f"• {airline} — {duration} — Nonstop — price not available"

        if line not in seen:
            seen.add(line)
            results.append(line)

    if not results:
        return ["No nonstop flights found"]

    return results[:5] 

def _header(origin: str, destination: str, depart_date: str, return_date: Optional[str]) -> str:
    if depart_date and return_date:
        return_date_str = return_date
    else:
        return_date_str = None
    dates = depart_date if not return_date_str else f"{depart_date} to {return_date_str}"
    return f"Direct nonstop options for {origin} → {destination} ({dates})"


def main(origin: str, destination: str, depart_date: str,
         return_date: Optional[str] = None,
         cabin: str = "economy", passengers: int = 1,
         nonstop_only: bool = True) -> str:
    header = _header(origin, destination, depart_date, return_date)
    lines = search_flights(origin, destination, depart_date, return_date, cabin, passengers, nonstop_only)
    if not lines:
        return f"{header}\nprice not available"
    return "\n".join([header] + lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--departure", required=True)
    parser.add_argument("--return", dest="return_date", default=None)
    parser.add_argument("--cabin", default="economy")
    parser.add_argument("--passengers", type=int, default=1)
    parser.add_argument("--nonstop", action="store_true")

    args = parser.parse_args()

    print(
        main(
            args.origin,
            args.destination,
            args.departure,
            args.return_date,
            args.cabin,
            args.passengers,
            args.nonstop,
        )
    )
