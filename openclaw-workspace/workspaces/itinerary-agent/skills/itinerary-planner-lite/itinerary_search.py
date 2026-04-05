"""
itinerary_search.py - Lightweight itinerary builder for itinerary-agent

Builds practical day-by-day plans using:
- SerpApi place discovery for attractions and restaurants
- SerpApi events search for local events
- Coordinate-based clustering to reduce backtracking
- Optional OpenWeather forecast checks for indoor / outdoor guidance
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import json
import math
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus

import requests


SCHEMA = json.loads(
    (Path(__file__).with_name("schema.json")).read_text(encoding="utf-8")
)

SERPAPI_URL = "https://serpapi.com/search"
OPENWEATHER_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


@dataclass
class Place:
    name: str
    category: str
    address: str = ""
    rating: Optional[float] = None
    review_count: Optional[int] = None
    price: Optional[str] = None
    description: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source: str = ""
    place_id: str = ""
    data_id: str = ""
    data_cid: str = ""
    reviews_link: str = ""
    place_url: str = ""


@dataclass
class Event:
    title: str
    when: str = ""
    venue: str = ""
    description: str = ""


def _google_search_link(*parts: str) -> str:
    query = " ".join(part.strip() for part in parts if part and part.strip())
    return f"https://www.google.com/search?q={quote_plus(query)}" if query else ""


def _get_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value.strip() if value else None


def _serpapi_search(params: Dict[str, object]) -> Dict[str, object]:
    api_key = _get_env("SERPAPI_API_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_API_KEY not configured")

    enriched = dict(params)
    enriched["api_key"] = api_key
    enriched.setdefault("hl", "en")

    response = requests.get(SERPAPI_URL, params=enriched, timeout=30)
    response.raise_for_status()
    return response.json()


def _safe_float(value: object) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> Optional[int]:
    try:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        text = str(value).replace(",", "").strip()
        if not text:
            return None
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _extract_coordinates(item: Dict[str, object]) -> Tuple[Optional[float], Optional[float]]:
    gps = item.get("gps_coordinates")
    if isinstance(gps, dict):
        return _safe_float(gps.get("latitude")), _safe_float(gps.get("longitude"))
    coordinates = item.get("coordinates")
    if isinstance(coordinates, dict):
        return _safe_float(coordinates.get("latitude")), _safe_float(coordinates.get("longitude"))
    return None, None


def _parse_place(item: Dict[str, object], category: str, source: str) -> Place:
    lat, lng = _extract_coordinates(item)
    name = str(item.get("title") or item.get("name") or "Unknown place")
    address = str(item.get("address") or item.get("formatted_address") or "")
    return Place(
        name=name,
        category=category,
        address=address,
        rating=_safe_float(item.get("rating")),
        review_count=_safe_int(item.get("reviews")),
        price=str(item.get("price") or item.get("price_level") or "") or None,
        description=str(item.get("description") or item.get("snippet") or ""),
        latitude=lat,
        longitude=lng,
        source=source,
        place_id=str(item.get("place_id") or ""),
        data_id=str(item.get("data_id") or ""),
        data_cid=str(item.get("data_cid") or ""),
        reviews_link=str(item.get("reviews_link") or ""),
        place_url=_google_search_link(name, address),
    )


def _parse_event(item: Dict[str, object]) -> Event:
    schedule = item.get("date") or item.get("schedule") or item.get("when") or ""
    venue = item.get("venue") or item.get("address") or item.get("location") or ""
    return Event(
        title=str(item.get("title") or item.get("name") or "Local event"),
        when=str(schedule),
        venue=str(venue),
        description=str(item.get("description") or item.get("snippet") or ""),
    )


def _search_local(query: str, location: str, limit: int = 10) -> List[Place]:
    data = _serpapi_search(
        {
            "engine": "google_local",
            "q": query,
            "location": location,
            "gl": "sg",
        }
    )

    local_results = data.get("local_results") or data.get("places_results") or []
    places: List[Place] = []
    for item in local_results[:limit]:
        if isinstance(item, dict):
            places.append(_parse_place(item, category=query, source="google_local"))
    return places


def _search_maps(query: str, limit: int = 10) -> List[Place]:
    data = _serpapi_search(
        {
            "engine": "google_maps",
            "type": "search",
            "q": query,
        }
    )

    places: List[Place] = []
    place_results = data.get("place_results")
    if isinstance(place_results, dict):
        places.append(_parse_place(place_results, category=query, source="google_maps"))

    local_results = data.get("local_results") or []
    for item in local_results:
        if isinstance(item, dict):
            places.append(_parse_place(item, category=query, source="google_maps"))
        if len(places) >= limit:
            break
    return places


def _search_maps_place(
    *,
    data_id: Optional[str] = None,
    place_id: Optional[str] = None,
    query: Optional[str] = None,
) -> Optional[Place]:
    try:
        if data_id:
            data = _serpapi_search(
                {
                    "engine": "google_maps",
                    "type": "place",
                    "data_id": data_id,
                }
            )
            place_results = data.get("place_results")
            if isinstance(place_results, dict):
                return _parse_place(place_results, category=query or "place", source="google_maps")

        if place_id:
            data = _serpapi_search(
                {
                    "engine": "google_maps",
                    "type": "place",
                    "place_id": place_id,
                }
            )
            place_results = data.get("place_results")
            if isinstance(place_results, dict):
                return _parse_place(place_results, category=query or "place", source="google_maps")

        if query:
            matches = _search_maps(query, limit=1)
            if matches:
                return matches[0]
    except Exception:
        return None

    return None


def search_attractions(destination: str, interests: Sequence[str], must_see: Sequence[str]) -> List[Place]:
    queries = [f"top attractions in {destination}", f"museums in {destination}", f"best neighborhoods to explore in {destination}"]
    queries.extend(f"{interest} in {destination}" for interest in interests[:3])
    queries.extend(f"{item} in {destination}" for item in must_see[:3])

    seen: set[str] = set()
    places: List[Place] = []
    for query in queries:
        try:
            for place in _search_local(query, destination, limit=6):
                key = place.name.lower()
                if key not in seen:
                    seen.add(key)
                    places.append(place)
        except Exception:
            continue
    return places[:18]


def search_restaurants(destination: str, dietary_constraints: Sequence[str], budget_style: str) -> Dict[str, List[Place]]:
    diet = " ".join(dietary_constraints[:2]).strip()
    breakfast_query = f"{diet} breakfast cafes in {destination}".strip()
    budget_query = f"{diet} budget restaurants in {destination}".strip()
    best_query = f"{diet} best restaurants in {destination}".strip()
    if budget_style == "premium":
        budget_query = f"{diet} casual restaurants in {destination}".strip()

    try:
        breakfast_results = _search_local(breakfast_query, destination, limit=8)
    except Exception:
        breakfast_results = []

    try:
        budget_results = _search_local(budget_query, destination, limit=8)
    except Exception:
        budget_results = []

    try:
        best_results = _search_local(best_query, destination, limit=8)
    except Exception:
        best_results = []

    return {
        "breakfast": breakfast_results,
        "budget": budget_results,
        "best": best_results,
    }


def search_events(destination: str) -> List[Event]:
    try:
        data = _serpapi_search(
            {
                "engine": "google_events",
                "q": f"events in {destination}",
                "location": destination,
                "gl": "sg",
            }
        )
    except Exception:
        return []

    results = data.get("events_results") or data.get("event_results") or []
    events: List[Event] = []
    for item in results[:8]:
        if isinstance(item, dict):
            events.append(_parse_event(item))
    return events


def _daterange(start_date: dt.date, days: int) -> List[dt.date]:
    return [start_date + dt.timedelta(days=offset) for offset in range(days)]


def _resolve_trip_days(
    start_date: Optional[str],
    end_date: Optional[str],
    days: Optional[int],
) -> Tuple[Optional[dt.date], int]:
    if days and days > 0:
        parsed_start = dt.date.fromisoformat(start_date) if start_date else None
        return parsed_start, days

    if start_date and end_date:
        start = dt.date.fromisoformat(start_date)
        end = dt.date.fromisoformat(end_date)
        span = (end - start).days + 1
        return start, max(span, 1)

    if start_date:
        return dt.date.fromisoformat(start_date), 3

    return None, max(days or 3, 1)


def _haversine_km(a: Place, b: Place) -> float:
    if a.latitude is None or a.longitude is None or b.latitude is None or b.longitude is None:
        return 9999.0

    radius = 6371.0
    lat1 = math.radians(a.latitude)
    lon1 = math.radians(a.longitude)
    lat2 = math.radians(b.latitude)
    lon2 = math.radians(b.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def _cluster_places(places: Sequence[Place], days: int) -> List[List[Place]]:
    if not places:
        return [[] for _ in range(days)]

    sorted_places = sorted(
        places,
        key=lambda item: (
            item.rating is None,
            -(item.rating or 0),
            item.name,
        ),
    )

    clusters: List[List[Place]] = [[] for _ in range(days)]
    seeds = sorted_places[:days]

    for index, seed in enumerate(seeds):
        clusters[index].append(seed)

    for place in sorted_places[days:]:
        best_index = min(
            range(days),
            key=lambda idx: min((_haversine_km(place, existing) for existing in clusters[idx]), default=9999.0),
        )
        clusters[best_index].append(place)

    for cluster in clusters:
        cluster.sort(key=lambda item: (item.address, item.name))
    return clusters


def _forecast_by_day(latitude: float, longitude: float) -> Dict[str, Dict[str, object]]:
    api_key = _get_env("OPENWEATHER_API_KEY")
    if not api_key:
        return {}

    response = requests.get(
        OPENWEATHER_FORECAST_URL,
        params={"lat": latitude, "lon": longitude, "appid": api_key, "units": "metric"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    grouped: Dict[str, Dict[str, object]] = {}
    for item in data.get("list", []):
        timestamp = item.get("dt_txt")
        if not isinstance(timestamp, str):
            continue
        date_key = timestamp.split(" ")[0]
        weather = item.get("weather") or []
        label = ""
        if weather and isinstance(weather[0], dict):
            label = str(weather[0].get("main") or weather[0].get("description") or "")
        rain = item.get("rain")
        pop = item.get("pop", 0)
        temp = None
        main = item.get("main")
        if isinstance(main, dict):
            temp = main.get("temp")

        existing = grouped.setdefault(
            date_key,
            {"labels": [], "max_pop": 0.0, "temps": []},
        )
        if label:
            existing["labels"].append(label)
        if isinstance(temp, (int, float)):
            existing["temps"].append(float(temp))
        if isinstance(pop, (int, float)):
            existing["max_pop"] = max(float(existing["max_pop"]), float(pop))
        if isinstance(rain, dict) and rain:
            existing["max_pop"] = max(float(existing["max_pop"]), 0.7)

    summary: Dict[str, Dict[str, object]] = {}
    for date_key, values in grouped.items():
        labels = [str(label) for label in values["labels"]]
        common_label = labels[0] if labels else "Unknown"
        temps = [float(temp) for temp in values["temps"]]
        avg_temp = round(sum(temps) / len(temps), 1) if temps else None
        summary[date_key] = {
            "label": common_label,
            "avg_temp_c": avg_temp,
            "max_pop": values["max_pop"],
        }
    return summary


def _weather_note(day: Optional[dt.date], weather_summary: Dict[str, Dict[str, object]]) -> str:
    if day is None:
        return "Weather check skipped."

    info = weather_summary.get(day.isoformat())
    if not info:
        return "Weather forecast not available for this day."

    label = str(info.get("label") or "Unknown conditions")
    avg_temp = info.get("avg_temp_c")
    pop = float(info.get("max_pop") or 0.0)

    parts = [label]
    if avg_temp is not None:
        parts.append(f"around {avg_temp} C")
    if pop >= 0.5:
        parts.append("higher chance of rain; keep an indoor backup")

    return ", ".join(parts)


def _dedupe_places(places: Sequence[Place]) -> List[Place]:
    seen: set[str] = set()
    output: List[Place] = []
    for place in places:
        key = place.name.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        output.append(place)
    return output


def _pick_restaurant(
    restaurants: Dict[str, List[Place]],
    budget_style: str,
    slot: str,
    used_names: Optional[set[str]] = None,
) -> Optional[Place]:
    breakfast_pool = restaurants.get("breakfast") or []
    budget_pool = restaurants.get("budget") or []
    best_pool = restaurants.get("best") or []

    if slot == "breakfast":
        pool = _dedupe_places(list(breakfast_pool) + list(budget_pool[:3]) + list(best_pool[:2]))
    elif slot == "dinner":
        if budget_style == "budget":
            pool = _dedupe_places(list(budget_pool) + list(best_pool[:3]))
        elif budget_style == "premium":
            pool = _dedupe_places(list(best_pool) + list(budget_pool[:3]))
        else:
            pool = _dedupe_places(list(best_pool[:5]) + list(budget_pool[:4]))
    else:
        if budget_style == "budget":
            pool = _dedupe_places(list(budget_pool) + list(best_pool[:3]))
        elif budget_style == "premium":
            pool = _dedupe_places(list(best_pool[:4]) + list(budget_pool[:4]))
        else:
            pool = _dedupe_places(list(budget_pool[:4]) + list(best_pool[:4]))

    if not pool:
        return None

    used_names = used_names or set()
    for place in pool:
        if place.name.lower() not in used_names:
            return place
    return pool[0]


def _place_label(place: Place) -> str:
    parts = [place.name]
    if place.address:
        parts.append(place.address)
    if place.rating is not None:
        parts.append(f"rating {place.rating:.1f}")
    return ", ".join(parts)


def _place_payload(place: Optional[Place]) -> Optional[Dict[str, object]]:
    if place is None:
        return None
    return {
        "name": place.name,
        "address": place.address,
        "url": place.place_url or _google_search_link(place.name, place.address),
        "rating": place.rating,
        "review_count": place.review_count,
        "price": place.price,
        "category": place.category,
        "source": place.source,
        "place_id": place.place_id or None,
        "data_id": place.data_id or None,
        "data_cid": place.data_cid or None,
    }


def _build_day_title(index: int, places: Sequence[Place], destination: str) -> str:
    if not places:
        return f"Day {index} - Flexible {destination} day"
    anchor = places[0].address or places[0].name
    return f"Day {index} - {anchor}"


def build_itinerary(
    destination: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: Optional[int] = None,
    traveler_type: Optional[str] = None,
    budget_style: str = "balanced",
    interests: Optional[Sequence[str]] = None,
    pace: str = "balanced",
    must_see: Optional[Sequence[str]] = None,
    dietary_constraints: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    if not _get_env("SERPAPI_API_KEY"):
        raise RuntimeError("SERPAPI_API_KEY not configured")

    interests = list(interests or [])
    must_see = list(must_see or [])
    dietary_constraints = list(dietary_constraints or [])
    if not interests:
        interests = ["landmarks", "food", "neighborhood walks", "culture"]

    start, total_days = _resolve_trip_days(start_date, end_date, days)
    trip_dates = _daterange(start, total_days) if start else [None] * total_days

    attractions = search_attractions(destination, interests, must_see)
    restaurants = search_restaurants(destination, dietary_constraints, budget_style)
    events = search_events(destination)

    weather_summary: Dict[str, Dict[str, object]] = {}
    first_located_place = next((place for place in attractions if place.latitude is not None and place.longitude is not None), None)
    if first_located_place is not None:
        try:
            weather_summary = _forecast_by_day(first_located_place.latitude, first_located_place.longitude)
        except Exception:
            weather_summary = {}

    clusters = _cluster_places(attractions, total_days)
    days_output: List[Dict[str, object]] = []

    for idx in range(total_days):
        cluster = clusters[idx] if idx < len(clusters) else []
        daytime_places = cluster[:2]
        evening_place = cluster[2] if len(cluster) > 2 else None
        used_meal_names: set[str] = set()
        breakfast = _pick_restaurant(restaurants, budget_style, slot="breakfast", used_names=used_meal_names)
        if breakfast:
            used_meal_names.add(breakfast.name.lower())
        lunch = _pick_restaurant(restaurants, budget_style, slot="lunch", used_names=used_meal_names)
        if lunch:
            used_meal_names.add(lunch.name.lower())
        dinner = _pick_restaurant(restaurants, budget_style, slot="dinner", used_names=used_meal_names)
        if dinner:
            used_meal_names.add(dinner.name.lower())
        event = events[idx] if idx < len(events) else None
        date_value = trip_dates[idx] if idx < len(trip_dates) else None

        if pace == "slow" and len(daytime_places) > 1:
            daytime_places = daytime_places[:1]
        elif pace == "fast" and evening_place is None and len(cluster) > 1:
            evening_place = cluster[-1]

        morning = (
            f"Start with {_place_label(daytime_places[0])}."
            if daytime_places
            else f"Keep the morning flexible for a neighborhood walk in {destination}."
        )

        breakfast_line = (
            f"Breakfast at {_place_label(breakfast)}."
            if breakfast
            else f"Breakfast near your base in {destination}."
        )

        lunch_line = (
            f"Lunch at {_place_label(lunch)}."
            if lunch
            else f"Lunch in a well-rated local area near {destination}."
        )

        afternoon_target = daytime_places[1] if len(daytime_places) > 1 else evening_place
        afternoon = (
            f"Continue to {_place_label(afternoon_target)}."
            if afternoon_target
            else "Use the afternoon for a cafe break, shopping street, or rest block."
        )

        if event:
            evening = f"Anchor the evening around {event.title}"
            if event.venue:
                evening += f" at {event.venue}"
            if event.when:
                evening += f" ({event.when})"
            evening += "."
        elif evening_place:
            evening = f"Spend the evening around {_place_label(evening_place)}."
        elif dinner:
            evening = f"Keep the evening light with a neighborhood stroll near {dinner.name}."
        else:
            evening = f"Keep the evening light with a local dinner and short stroll in {destination}."

        dinner_line = (
            f"Dinner at {_place_label(dinner)}."
            if dinner
            else f"Dinner near your base in {destination}."
        )

        notes = [
            _weather_note(date_value, weather_summary),
            "Transit times are approximate; verify live opening hours before locking bookings.",
        ]
        if traveler_type:
            notes.append(f"Adjusted for {traveler_type} travel style.")
        if must_see:
            notes.append(f"Must-see coverage: {', '.join(must_see[:3])}.")

        days_output.append(
            {
                "title": _build_day_title(idx + 1, cluster, destination),
                "morning": morning,
                "afternoon": afternoon,
                "evening": evening,
                "breakfast": breakfast_line,
                "lunch": lunch_line,
                "dinner": dinner_line,
                "notes": " ".join(notes),
                "morning_place": _place_payload(daytime_places[0] if daytime_places else None),
                "afternoon_place": _place_payload(afternoon_target),
                "breakfast_place": _place_payload(breakfast),
                "lunch_place": _place_payload(lunch),
                "dinner_place": _place_payload(dinner),
            }
        )

    date_label = "flexible dates"
    if start_date and end_date:
        date_label = f"{start_date} to {end_date}"
    elif start_date:
        date_label = start_date
    elif days:
        date_label = f"{days} days"

    return {
        "header": f"Itinerary for {destination} ({date_label})",
        "days": days_output,
        "meta": {
            "attractions_found": len(attractions),
            "events_found": len(events),
            "weather_enabled": bool(_get_env("OPENWEATHER_API_KEY")),
        },
    }


def format_itinerary(plan: Dict[str, object]) -> str:
    header = str(plan.get("header") or "Itinerary")
    lines = [header]
    for day in plan.get("days", []):
        if not isinstance(day, dict):
            continue
        lines.append("")
        lines.append(str(day.get("title") or "Day"))
        lines.append(f"Morning: {day.get('morning', '')}")
        lines.append(f"Afternoon: {day.get('afternoon', '')}")
        lines.append(f"Evening: {day.get('evening', '')}")
        lines.append(f"Breakfast: {day.get('breakfast', '')}")
        lines.append(f"Lunch: {day.get('lunch', '')}")
        lines.append(f"Dinner: {day.get('dinner', '')}")
        lines.append(f"Notes: {day.get('notes', '')}")
    return "\n".join(lines)


def main(
    destination: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: Optional[int] = None,
    traveler_type: Optional[str] = None,
    budget_style: str = "balanced",
    interests: Optional[Sequence[str]] = None,
    pace: str = "balanced",
    must_see: Optional[Sequence[str]] = None,
    dietary_constraints: Optional[Sequence[str]] = None,
) -> str:
    plan = build_itinerary(
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        days=days,
        traveler_type=traveler_type,
        budget_style=budget_style,
        interests=interests,
        pace=pace,
        must_see=must_see,
        dietary_constraints=dietary_constraints,
    )
    return format_itinerary(plan)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--traveler-type", default=None)
    parser.add_argument("--budget-style", default="balanced")
    parser.add_argument("--interests", nargs="*", default=None)
    parser.add_argument("--pace", default="balanced")
    parser.add_argument("--must-see", nargs="*", default=None)
    parser.add_argument("--dietary-constraints", nargs="*", default=None)

    args = parser.parse_args()

    print(
        main(
            destination=args.destination,
            start_date=args.start_date,
            end_date=args.end_date,
            days=args.days,
            traveler_type=args.traveler_type,
            budget_style=args.budget_style,
            interests=args.interests,
            pace=args.pace,
            must_see=args.must_see,
            dietary_constraints=args.dietary_constraints,
        )
    )
