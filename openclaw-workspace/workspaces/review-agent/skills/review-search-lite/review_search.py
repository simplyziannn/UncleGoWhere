#!/usr/bin/env python3
"""review_search.py - Lightweight review lookup for review-agent."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus

import requests


SCHEMA = json.loads(
    (Path(__file__).with_name("schema.json")).read_text(encoding="utf-8")
)

SERPAPI_URL = "https://serpapi.com/search"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
SERPAPI_MAX_ATTEMPTS = 3
SERPAPI_RETRY_DELAY_SECONDS = 1.0
GENERIC_MEAL_NAME_FRAGMENTS = (
    "food anchors",
    "rough dining ideas",
    "flexible dining",
    "near your base",
    "well-rated local area",
    "lunch near ",
    "dinner near ",
    "breakfast near ",
)


@dataclass
class Place:
    name: str
    address: str = ""
    rating: Optional[float] = None
    review_count: Optional[int] = None
    source: str = ""
    place_id: str = ""
    data_id: str = ""
    data_cid: str = ""
    place_url: str = ""


@dataclass
class Review:
    author: str
    rating: Optional[float] = None
    published: str = ""
    content: str = ""
    translated_content_en: str = ""


def _get_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value.strip() if value else None


def _google_search_link(*parts: str) -> str:
    query = " ".join(part.strip() for part in parts if part and part.strip())
    return f"https://www.google.com/search?q={quote_plus(query)}" if query else ""


def _safe_float(value: object) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> Optional[int]:
    try:
        if value is None:
            return None
        text = str(value).replace(",", "").strip()
        if not text:
            return None
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _serpapi_search(params: Dict[str, object]) -> Dict[str, object]:
    api_key = _get_env("SERPAPI_API_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_API_KEY not configured")

    enriched = dict(params)
    enriched["api_key"] = api_key
    enriched.setdefault("hl", "en")

    last_error: Optional[Exception] = None
    for attempt in range(1, SERPAPI_MAX_ATTEMPTS + 1):
        try:
            response = requests.get(SERPAPI_URL, params=enriched, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt >= SERPAPI_MAX_ATTEMPTS:
                break
            time.sleep(SERPAPI_RETRY_DELAY_SECONDS)
    if last_error is not None:
        raise last_error
    raise RuntimeError("SerpApi search failed without a specific error")


def _extract_coordinates(item: Dict[str, object]) -> Tuple[Optional[float], Optional[float]]:
    gps = item.get("gps_coordinates")
    if isinstance(gps, dict):
        return _safe_float(gps.get("latitude")), _safe_float(gps.get("longitude"))
    coordinates = item.get("coordinates")
    if isinstance(coordinates, dict):
        return _safe_float(coordinates.get("latitude")), _safe_float(coordinates.get("longitude"))
    return None, None


def _parse_place(item: Dict[str, object], source: str) -> Place:
    _extract_coordinates(item)
    name = str(item.get("title") or item.get("name") or "Unknown place")
    address = str(item.get("address") or item.get("formatted_address") or "")
    return Place(
        name=name,
        address=address,
        rating=_safe_float(item.get("rating")),
        review_count=_safe_int(item.get("reviews")),
        source=source,
        place_id=str(item.get("place_id") or ""),
        data_id=str(item.get("data_id") or ""),
        data_cid=str(item.get("data_cid") or ""),
        place_url=_google_search_link(name, address),
    )


def _parse_review(item: Dict[str, object]) -> Review:
    author = str(
        item.get("author")
        or item.get("username")
        or item.get("name")
        or ((item.get("user") or {}).get("name") if isinstance(item.get("user"), dict) else "")
        or "Anonymous"
    )
    published = str(
        item.get("iso_date")
        or item.get("date_iso8601")
        or item.get("iso_date_of_last_edit")
        or item.get("published_at")
        or item.get("published")
        or item.get("date")
        or item.get("date_ago")
        or ""
    )
    content = str(
        item.get("description")
        or item.get("snippet")
        or item.get("excerpt")
        or item.get("summary")
        or ""
    )
    return Review(
        author=author,
        rating=_safe_float(item.get("rating")),
        published=published,
        content=content,
    )


def _place_payload(place: Optional[Place]) -> Optional[Dict[str, object]]:
    if place is None:
        return None
    return {
        "name": place.name,
        "address": place.address,
        "url": place.place_url or _google_search_link(place.name, place.address),
        "rating": place.rating,
        "review_count": place.review_count,
        "source": place.source,
        "place_id": place.place_id or None,
        "data_id": place.data_id or None,
        "data_cid": place.data_cid or None,
    }


def _review_payload(review: Review) -> Dict[str, object]:
    return {
        "author": review.author,
        "rating": review.rating,
        "published": review.published,
        "content": review.content,
        "translated_content_en": review.translated_content_en or None,
    }


def _collect_review_items(data: Dict[str, object]) -> List[Dict[str, object]]:
    candidates: List[object] = [
        data.get("reviews"),
        data.get("user_reviews"),
        data.get("most_relevant_reviews"),
    ]
    place_results = data.get("place_results")
    if isinstance(place_results, dict):
        candidates.extend(
            [
                place_results.get("reviews"),
                place_results.get("user_reviews"),
            ]
        )

    items: List[Dict[str, object]] = []
    for candidate in candidates:
        if isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, dict):
                    items.append(item)
        elif isinstance(candidate, dict):
            for nested_key in ("most_relevant", "newest", "reviews", "summary"):
                nested = candidate.get(nested_key)
                if isinstance(nested, list):
                    for item in nested:
                        if isinstance(item, dict):
                            items.append(item)
    return items


def _review_sort_key(review: Review) -> str:
    return review.published or ""


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
            places.append(_parse_place(item, source="google_local"))
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
        places.append(_parse_place(place_results, source="google_maps"))

    for item in data.get("local_results") or []:
        if isinstance(item, dict):
            places.append(_parse_place(item, source="google_maps"))
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
                return _parse_place(place_results, source="google_maps")

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
                return _parse_place(place_results, source="google_maps")

        if query:
            matches = _search_maps(query, limit=1)
            if matches:
                return matches[0]
    except Exception:
        return None
    return None


def _pick_review_target(destination: str, place_name: str) -> Optional[Place]:
    queries = [
        f"{place_name} in {destination}",
        f"{place_name} {destination}",
        place_name,
    ]
    for query in queries:
        for resolver in (
            lambda: _search_maps(query=query, limit=5),
            lambda: _search_local(query=query, location=destination, limit=5),
        ):
            try:
                matches = resolver()
            except Exception:
                continue
            match = next((place for place in matches if place_name.lower() in place.name.lower()), None)
            if match is None and matches:
                match = matches[0]
            if match is not None:
                enriched = _search_maps_place(
                    data_id=match.data_id or None,
                    place_id=match.place_id or None,
                    query=f"{match.name} {destination}",
                )
                return enriched or match
    return None


def _openai_translate_to_english(text: str) -> str:
    api_key = _get_env("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    content = text.strip()
    if not content:
        return ""

    model = _get_env("OPENAI_TRANSLATION_MODEL") or _get_env("OPENAI_MODEL") or "gpt-5"
    response = requests.post(
        OPENAI_RESPONSES_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": [
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Translate the user's review text into clear natural English. "
                                "Return only the English translation and nothing else."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": content}],
                },
            ],
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    output_text = str(data.get("output_text") or "").strip()
    if output_text:
        return output_text

    parts: List[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content_item in item.get("content") or []:
            if not isinstance(content_item, dict):
                continue
            if content_item.get("type") == "output_text":
                text = str(content_item.get("text") or "").strip()
                if text:
                    parts.append(text)
    return "\n".join(parts).strip()


def _translate_reviews_to_english(reviews: Sequence[Review]) -> None:
    if not _get_env("OPENAI_API_KEY"):
        return
    for review in reviews:
        if not review.content.strip():
            continue
        try:
            review.translated_content_en = _openai_translate_to_english(review.content)
        except Exception:
            review.translated_content_en = ""


def _fallback_review_summary(place: Optional[Place]) -> Optional[Dict[str, object]]:
    if place is None:
        return None
    if place.rating is None and place.review_count is None:
        return None
    return {
        "average_rating": place.rating,
        "total_reviews": place.review_count,
    }


def _is_vague_meal_name(place_name: str) -> bool:
    normalized = " ".join(place_name.lower().split())
    if not normalized:
        return True
    if normalized in {"breakfast", "lunch", "dinner", "meal"}:
        return True
    return any(fragment in normalized for fragment in GENERIC_MEAL_NAME_FRAGMENTS)


def search_recent_reviews(
    destination: str,
    place_name: str,
    limit: int = 1,
    translate_to_english: bool = True,
) -> Dict[str, object]:
    place = _pick_review_target(destination, place_name)
    if place is None:
        return {
            "restaurant": {
                "name": place_name,
                "address": "",
                "url": _google_search_link(place_name, destination),
            },
            "reviews": [],
            "used_fallback_summary": False,
        }

    if not place.data_id and place.place_id:
        place = _search_maps_place(
            place_id=place.place_id,
            query=f"{place.name} {destination}",
        ) or place

    reviews: List[Review] = []
    direct_reviews_failed = False

    if place.data_id or place.place_id:
        try:
            params: Dict[str, object] = {
                "engine": "google_maps_reviews",
                "sort_by": "newestFirst",
            }
            if place.data_id:
                params["data_id"] = place.data_id
            else:
                params["place_id"] = place.place_id

            data = _serpapi_search(params)
            for item in _collect_review_items(data):
                reviews.append(_parse_review(item))
            reviews.sort(key=_review_sort_key, reverse=True)
        except Exception:
            direct_reviews_failed = True

    if not reviews:
        try:
            place_lookup = _search_maps_place(
                data_id=place.data_id or None,
                place_id=place.place_id or None,
                query=f"{place.name} {destination}",
            )
            if place_lookup is not None:
                place = place_lookup
            if place.data_id or place.place_id:
                params: Dict[str, object] = {
                    "engine": "google_maps",
                    "type": "place",
                }
                if place.data_id:
                    params["data_id"] = place.data_id
                else:
                    params["place_id"] = place.place_id
                place_data = _serpapi_search(params)
                place_results = place_data.get("place_results")
                if isinstance(place_results, dict):
                    place = _parse_place(place_results, source="google_maps")
                for item in _collect_review_items(place_data):
                    reviews.append(_parse_review(item))
                reviews.sort(key=_review_sort_key, reverse=True)
        except Exception:
            pass

    selected_reviews = reviews[:limit]
    if translate_to_english and selected_reviews:
        _translate_reviews_to_english(selected_reviews)

    payload: Dict[str, object] = {
        "restaurant": _place_payload(place),
        "reviews": [_review_payload(review) for review in selected_reviews],
        "used_fallback_summary": False,
    }
    if not selected_reviews:
        fallback = _fallback_review_summary(place)
        if fallback is not None:
            payload["fallback_summary"] = fallback
            payload["used_fallback_summary"] = True
        if direct_reviews_failed:
            payload["review_error"] = "Direct review lookup failed; using place summary fallback when available."
    return payload


def search_meal_reviews(
    destination: str,
    meals: Sequence[Dict[str, object]],
    translate_to_english: bool = True,
) -> Dict[str, object]:
    results: List[Dict[str, object]] = []
    for meal in meals:
        day = str(meal.get("day") or "")
        meal_type = str(meal.get("meal_type") or "")
        place_name = str(meal.get("place_name") or "").strip()
        if not place_name or _is_vague_meal_name(place_name):
            results.append(
                {
                    "day": day or None,
                    "meal_type": meal_type or None,
                    "requested_place_name": place_name or None,
                    "place": None,
                    "review": None,
                    "used_fallback_summary": False,
                    "fallback_summary": None,
                    "review_error": "Concrete meal place missing or too vague; itinerary-agent must provide a named restaurant.",
                }
            )
            continue
        review_result = search_recent_reviews(
            destination=destination,
            place_name=place_name,
            limit=1,
            translate_to_english=translate_to_english,
        )
        review_payload = None
        reviews = review_result.get("reviews")
        if isinstance(reviews, list) and reviews:
            review_payload = reviews[0]
        results.append(
            {
                "day": day or None,
                "meal_type": meal_type or None,
                "requested_place_name": place_name,
                "place": review_result.get("restaurant"),
                "review": review_payload,
                "used_fallback_summary": bool(review_result.get("used_fallback_summary")),
                "fallback_summary": review_result.get("fallback_summary"),
                "review_error": review_result.get("review_error"),
            }
        )
    return {
        "destination": destination,
        "meals": results,
    }


def format_meal_reviews(bundle: Dict[str, object]) -> str:
    lines = [f"Meal reviews for {bundle.get('destination', '')}"]
    for item in bundle.get("meals", []):
        if not isinstance(item, dict):
            continue
        place = item.get("place") or {}
        review = item.get("review")
        lines.append("")
        lines.append(
            f"{item.get('day', 'Day')} - {item.get('meal_type', 'meal').title()}: {place.get('name', item.get('requested_place_name', ''))}"
        )
        lines.append(f"Address: {place.get('address', '')}")
        lines.append(f"Link: {place.get('url', '')}")
        if review and isinstance(review, dict):
            lines.append(f"Average: {place.get('rating', '')} stars from {place.get('review_count', '')} reviews")
            lines.append(f"Review by {review.get('author', '')} ({review.get('published', '')})")
            lines.append(f"Raw: {review.get('content', '')}")
            translated = str(review.get("translated_content_en") or "").strip()
            if translated:
                lines.append(f"English: {translated}")
        elif item.get("used_fallback_summary"):
            fallback = item.get("fallback_summary") or {}
            lines.append(
                f"Fallback summary: {fallback.get('average_rating', '')} stars from {fallback.get('total_reviews', '')} reviews"
            )
        elif item.get("review_error"):
            lines.append(f"Error: {item.get('review_error')}")
        else:
            lines.append("No review text found.")
    return "\n".join(lines)


def _parse_cli_meal(value: str) -> Dict[str, object]:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) >= 3:
        return {"day": parts[0], "meal_type": parts[1], "place_name": "|".join(parts[2:]).strip()}
    if len(parts) == 2:
        return {"day": None, "meal_type": parts[0], "place_name": parts[1]}
    return {"day": None, "meal_type": "meal", "place_name": value.strip()}


def main(
    destination: str,
    meals: Sequence[Dict[str, object]],
    translate_to_english: bool = True,
) -> str:
    bundle = search_meal_reviews(destination, meals, translate_to_english=translate_to_english)
    return format_meal_reviews(bundle)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    parser.add_argument("--meal", action="append", default=[])
    parser.add_argument("--no-translate", action="store_true")
    args = parser.parse_args()

    meals = [_parse_cli_meal(value) for value in args.meal]
    print(
        main(
            destination=args.destination,
            meals=meals,
            translate_to_english=not args.no_translate,
        )
    )
