#!/usr/bin/env python3
"""review_search.py - SerpApi/TripAdvisor review lookup for review-agent."""

from __future__ import annotations

from dataclasses import dataclass
import html
import json
import os
from pathlib import Path
import re
import time
from typing import Dict, Iterable, List, Optional, Sequence
from urllib.parse import quote_plus, urljoin

import requests


SCHEMA = json.loads(
    (Path(__file__).with_name("schema.json")).read_text(encoding="utf-8")
)

TRIPADVISOR_HOST = "https://www.tripadvisor.com"
TRIPADVISOR_SEARCH_URL = f"{TRIPADVISOR_HOST}/Search"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"
TRIPADVISOR_MAX_ATTEMPTS = 3
TRIPADVISOR_RETRY_DELAY_SECONDS = 1.0
SERPAPI_MAX_ATTEMPTS = 3
SERPAPI_RETRY_DELAY_SECONDS = 1.0
TRIPADVISOR_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
MATCH_STOPWORDS = {
    "and",
    "the",
    "restaurant",
    "restaurants",
    "cafe",
    "coffee",
    "bar",
    "kitchen",
    "dining",
}
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
    source: str = "TripAdvisor"
    place_url: str = ""


@dataclass
class Review:
    author: str
    rating: Optional[float] = None
    published: str = ""
    content: str = ""
    translated_content_en: str = ""
    source: str = "TripAdvisor"


def _get_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value.strip() if value else None


def _tripadvisor_search_link(*parts: str) -> str:
    query = " ".join(part.strip() for part in parts if part and part.strip())
    return f"{TRIPADVISOR_SEARCH_URL}?q={quote_plus(query)}" if query else ""


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


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _normalize_match_text(text: str) -> str:
    return _normalize_whitespace(re.sub(r"[^a-z0-9]+", " ", html.unescape((text or "").lower())))


def _match_tokens(text: str) -> List[str]:
    return [
        token
        for token in _normalize_match_text(text).split()
        if len(token) > 1 and token not in MATCH_STOPWORDS
    ]


def _infer_gl(destination: str) -> Optional[str]:
    normalized = _normalize_match_text(destination)
    if any(token in normalized for token in ("johor", "bahru", "kuala lumpur", "penang", "malaysia")):
        return "my"
    if "singapore" in normalized:
        return "sg"
    if any(token in normalized for token in ("tokyo", "osaka", "kyoto", "japan")):
        return "jp"
    if any(token in normalized for token in ("bangkok", "chiang mai", "phuket", "thailand")):
        return "th"
    return None


def _decode_json_escaped_text(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return html.unescape(value)


def _request_text(url: str, params: Optional[Dict[str, str]] = None) -> str:
    last_error: Optional[Exception] = None
    for attempt in range(1, TRIPADVISOR_MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=TRIPADVISOR_HEADERS,
                timeout=30,
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= TRIPADVISOR_MAX_ATTEMPTS:
                break
            time.sleep(TRIPADVISOR_RETRY_DELAY_SECONDS)
    if last_error is not None:
        raise last_error
    raise RuntimeError("TripAdvisor request failed without a specific error")


def _request_json(
    url: str,
    params: Dict[str, str],
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    max_attempts: int = 3,
    retry_delay_seconds: float = 1.0,
) -> Dict[str, object]:
    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return data
            raise RuntimeError("Expected JSON object response")
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            time.sleep(retry_delay_seconds)
    if last_error is not None:
        raise last_error
    raise RuntimeError("JSON request failed without a specific error")


def _serpapi_key() -> Optional[str]:
    return _get_env("SERPAPI_API_KEY") or _get_env("SERP_API_KEY")


def _serpapi_place_score(candidate: Dict[str, object], place_name: str, destination: str) -> int:
    title = str(candidate.get("title") or "")
    address = str(candidate.get("address") or "")
    candidate_text = " ".join([title, address])
    requested_norm = _normalize_match_text(place_name)
    destination_tokens = _match_tokens(destination)
    candidate_norm = _normalize_match_text(candidate_text)
    candidate_tokens = set(_match_tokens(candidate_text))

    score = 0
    if requested_norm and requested_norm in candidate_norm:
        score += 50
    requested_tokens = _match_tokens(place_name)
    score += sum(5 for token in requested_tokens if token in candidate_tokens)
    score += sum(1 for token in destination_tokens if token in candidate_tokens)
    if str(candidate.get("type") or "").lower().endswith("restaurant"):
        score += 2
    if str(candidate.get("type") or "").lower().endswith("cafe"):
        score += 2
    if str(candidate.get("type") or "").lower().endswith("coffee shop"):
        score += 2
    return score


def _pick_serpapi_result(destination: str, place_name: str) -> Optional[Dict[str, object]]:
    api_key = _serpapi_key()
    if not api_key:
        return None

    queries = [
        f"{place_name} {destination}",
        f"{place_name} restaurant {destination}",
        f"{place_name}, {destination}",
        place_name,
    ]
    gl = _infer_gl(destination)
    best_candidate: Optional[Dict[str, object]] = None
    best_score = -1
    for query in queries:
        params = {
            "engine": "google_maps",
            "type": "search",
            "q": query,
            "hl": "en",
            "no_cache": "true",
            "api_key": api_key,
        }
        if gl:
            params["gl"] = gl
        data = _request_json(
            SERPAPI_SEARCH_URL,
            params,
            timeout=45,
            max_attempts=SERPAPI_MAX_ATTEMPTS,
            retry_delay_seconds=SERPAPI_RETRY_DELAY_SECONDS,
        )
        place_result = data.get("place_results")
        if isinstance(place_result, dict):
            return place_result
        for item in data.get("local_results") or []:
            if not isinstance(item, dict):
                continue
            score = _serpapi_place_score(item, place_name, destination)
            if score > best_score:
                best_score = score
                best_candidate = item
        if best_score >= 50:
            break
    return best_candidate


def _serpapi_place_url(candidate: Dict[str, object], destination: str) -> str:
    query = " ".join(
        part.strip()
        for part in (str(candidate.get("title") or ""), str(candidate.get("address") or ""), destination)
        if part and part.strip()
    )
    if not query:
        return ""
    return f"https://www.google.com/maps/search/{quote_plus(query)}"


def _place_from_serpapi(candidate: Dict[str, object], requested_name: str, destination: str) -> Place:
    return Place(
        name=str(candidate.get("title") or requested_name),
        address=str(candidate.get("address") or ""),
        rating=_safe_float(candidate.get("rating")),
        review_count=_safe_int(candidate.get("reviews")),
        source="Google Maps (SerpApi)",
        place_url=_serpapi_place_url(candidate, destination),
    )


def _review_from_serpapi(review_data: Dict[str, object]) -> Optional[Review]:
    snippets = []
    for key in ("snippet", "text", "summary", "description"):
        value = str(review_data.get(key) or "").strip()
        if value:
            snippets.append(value)
    content = _normalize_whitespace(" ".join(snippets))
    if not content:
        return None

    author = "Anonymous"
    user = review_data.get("user")
    if isinstance(user, dict):
        author = str(user.get("name") or author)
    elif review_data.get("username"):
        author = str(review_data.get("username"))
    elif review_data.get("user_name"):
        author = str(review_data.get("user_name"))

    rating = _safe_float(review_data.get("rating"))
    if rating is None:
        details = review_data.get("details")
        if isinstance(details, dict):
            rating = _safe_float(details.get("rating"))

    published = (
        str(review_data.get("date") or "")
        or str(review_data.get("published") or "")
        or str(review_data.get("date_published") or "")
        or str(review_data.get("date_iso8601") or "")
    )

    return Review(
        author=author,
        rating=rating,
        published=published,
        content=content,
        source="Google Maps (SerpApi)",
    )


def _fetch_serpapi_reviews(candidate: Dict[str, object]) -> List[Review]:
    api_key = _serpapi_key()
    if not api_key:
        return []

    data_id = str(candidate.get("data_id") or "").strip()
    if not data_id:
        return []

    data = _request_json(
        SERPAPI_SEARCH_URL,
        {
            "engine": "google_maps_reviews",
            "data_id": data_id,
            "hl": "en",
            "no_cache": "true",
            "api_key": api_key,
        },
        timeout=45,
        max_attempts=SERPAPI_MAX_ATTEMPTS,
        retry_delay_seconds=SERPAPI_RETRY_DELAY_SECONDS,
    )
    reviews: List[Review] = []
    seen_contents = set()
    review_items: List[object] = []
    direct_reviews = data.get("reviews")
    if isinstance(direct_reviews, list):
        review_items.extend(direct_reviews)
    user_reviews = data.get("user_reviews")
    if isinstance(user_reviews, dict):
        for key in ("most_relevant", "newest"):
            value = user_reviews.get(key)
            if isinstance(value, list):
                review_items.extend(value)

    for item in review_items:
        if not isinstance(item, dict):
            continue
        review = _review_from_serpapi(item)
        if review is None:
            continue
        key = review.content.lower()
        if key in seen_contents:
            continue
        seen_contents.add(key)
        reviews.append(review)
    return reviews


def _place_payload(place: Optional[Place]) -> Optional[Dict[str, object]]:
    if place is None:
        return None
    return {
        "name": place.name,
        "address": place.address,
        "url": place.place_url or _tripadvisor_search_link(place.name, place.address),
        "rating": place.rating,
        "review_count": place.review_count,
        "source": place.source,
    }


def _review_payload(review: Review) -> Dict[str, object]:
    return {
        "author": review.author,
        "rating": review.rating,
        "published": review.published,
        "content": review.content,
        "translated_content_en": review.translated_content_en or None,
        "source": review.source,
    }


def _extract_tripadvisor_paths(page_html: str) -> List[str]:
    normalized_html = page_html.replace("\\/", "/")
    matches = re.findall(r'/Restaurant_Review[^"\'<>\s]+?\.html', normalized_html)
    seen = set()
    paths: List[str] = []
    for path in matches:
        cleaned = path.split("?")[0]
        if cleaned not in seen:
            seen.add(cleaned)
            paths.append(cleaned)
    return paths


def _title_from_tripadvisor_path(path: str) -> str:
    match = re.search(r"-Reviews-(?P<slug>[^./?]+)", path)
    if not match:
        return ""
    return match.group("slug").replace("_", " ").replace("-", " ").strip()


def _score_tripadvisor_candidate(path: str, place_name: str, destination: str) -> int:
    requested_norm = _normalize_match_text(place_name)
    destination_tokens = _match_tokens(destination)
    candidate_text = " ".join([path, _title_from_tripadvisor_path(path)])
    candidate_norm = _normalize_match_text(candidate_text)
    candidate_tokens = set(_match_tokens(candidate_text))

    score = 0
    if requested_norm and requested_norm in candidate_norm:
        score += 50
    requested_tokens = _match_tokens(place_name)
    score += sum(5 for token in requested_tokens if token in candidate_tokens)
    score += sum(1 for token in destination_tokens if token in candidate_tokens)
    return score


def _pick_tripadvisor_page_url(destination: str, place_name: str) -> Optional[str]:
    queries = [
        f"{place_name} {destination}",
        f"{place_name} restaurant {destination}",
        place_name,
    ]
    best_path = ""
    best_score = -1
    for query in queries:
        try:
            page_html = _request_text(TRIPADVISOR_SEARCH_URL, params={"q": query})
        except Exception:
            continue
        for path in _extract_tripadvisor_paths(page_html):
            score = _score_tripadvisor_candidate(path, place_name, destination)
            if score > best_score:
                best_score = score
                best_path = path
        if best_score >= 50:
            break
    return urljoin(TRIPADVISOR_HOST, best_path) if best_path else None


def _extract_jsonld_objects(page_html: str) -> List[object]:
    objects: List[object] = []
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(?P<body>.*?)</script>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        body = match.group("body").strip()
        if not body:
            continue
        body = body.replace("<!--", "").replace("-->", "").strip()
        try:
            objects.append(json.loads(html.unescape(body)))
        except json.JSONDecodeError:
            continue
    return objects


def _iter_nodes(value: object) -> Iterable[object]:
    yield value
    if isinstance(value, dict):
        for nested in value.values():
            yield from _iter_nodes(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_nodes(nested)


def _schema_type_matches(node: Dict[str, object], expected: Sequence[str]) -> bool:
    actual = node.get("@type")
    if isinstance(actual, list):
        types = {str(item).lower() for item in actual}
    else:
        types = {str(actual).lower()}
    return any(item.lower() in types for item in expected)


def _format_address(value: object) -> str:
    if isinstance(value, str):
        return _normalize_whitespace(value)
    if not isinstance(value, dict):
        return ""
    parts = [
        value.get("streetAddress"),
        value.get("addressLocality"),
        value.get("addressRegion"),
        value.get("postalCode"),
        value.get("addressCountry"),
    ]
    return _normalize_whitespace(", ".join(str(part).strip() for part in parts if part))


def _parse_tripadvisor_place_from_jsonld(
    jsonld_objects: Sequence[object],
    page_url: str,
    requested_name: str,
) -> Optional[Place]:
    for node in _iter_nodes(list(jsonld_objects)):
        if not isinstance(node, dict):
            continue
        if not _schema_type_matches(node, ("Restaurant", "FoodEstablishment", "LocalBusiness")):
            continue
        aggregate = node.get("aggregateRating") if isinstance(node.get("aggregateRating"), dict) else {}
        return Place(
            name=str(node.get("name") or requested_name or _title_from_tripadvisor_path(page_url)),
            address=_format_address(node.get("address")),
            rating=_safe_float(aggregate.get("ratingValue")),
            review_count=_safe_int(aggregate.get("reviewCount") or aggregate.get("ratingCount")),
            source="TripAdvisor",
            place_url=page_url,
        )
    return None


def _parse_tripadvisor_review_from_schema(node: Dict[str, object]) -> Optional[Review]:
    author_field = node.get("author")
    if isinstance(author_field, dict):
        author = str(author_field.get("name") or "Anonymous")
    elif author_field:
        author = str(author_field)
    else:
        author = "Anonymous"

    rating_field = node.get("reviewRating")
    rating = None
    if isinstance(rating_field, dict):
        rating = _safe_float(rating_field.get("ratingValue"))
    elif rating_field is not None:
        rating = _safe_float(rating_field)

    content = _normalize_whitespace(
        str(node.get("reviewBody") or node.get("description") or node.get("text") or "")
    )
    if not content:
        return None

    return Review(
        author=author,
        rating=rating,
        published=str(node.get("datePublished") or node.get("published") or ""),
        content=content,
        source="TripAdvisor",
    )


def _extract_tripadvisor_reviews_from_jsonld(jsonld_objects: Sequence[object]) -> List[Review]:
    reviews: List[Review] = []
    seen_contents = set()
    for node in _iter_nodes(list(jsonld_objects)):
        if not isinstance(node, dict):
            continue
        if not _schema_type_matches(node, ("Review",)):
            continue
        review = _parse_tripadvisor_review_from_schema(node)
        if review is None:
            continue
        key = review.content.lower()
        if key in seen_contents:
            continue
        seen_contents.add(key)
        reviews.append(review)
    return reviews


def _extract_tripadvisor_review_from_regex(page_html: str) -> Optional[Review]:
    content_match = re.search(
        r'"reviewBody"\s*:\s*"(?P<content>(?:\\.|[^"\\])*)"',
        page_html,
        flags=re.DOTALL,
    )
    if not content_match:
        return None
    author_match = re.search(
        r'"author"\s*:\s*\{[^{}]*"name"\s*:\s*"(?P<author>(?:\\.|[^"\\])*)"',
        page_html,
        flags=re.DOTALL,
    )
    published_match = re.search(r'"datePublished"\s*:\s*"(?P<date>[^"]+)"', page_html)
    rating_match = re.search(r'"reviewRating"\s*:\s*\{[^{}]*"ratingValue"\s*:\s*"?(?P<rating>[0-9.]+)', page_html)
    return Review(
        author=_decode_json_escaped_text(author_match.group("author")) if author_match else "Anonymous",
        rating=_safe_float(rating_match.group("rating")) if rating_match else None,
        published=published_match.group("date") if published_match else "",
        content=_normalize_whitespace(_decode_json_escaped_text(content_match.group("content"))),
        source="TripAdvisor",
    )


def _extract_tripadvisor_place_from_regex(
    page_html: str,
    page_url: str,
    requested_name: str,
) -> Optional[Place]:
    name_match = re.search(r'"name"\s*:\s*"(?P<name>(?:\\.|[^"\\])*)"', page_html)
    rating_match = re.search(r'"ratingValue"\s*:\s*"?(?P<rating>[0-9.]+)', page_html)
    count_match = re.search(r'"reviewCount"\s*:\s*"?(?P<count>[0-9,]+)', page_html)
    address_match = re.search(r'"streetAddress"\s*:\s*"(?P<address>(?:\\.|[^"\\])*)"', page_html)
    return Place(
        name=_decode_json_escaped_text(name_match.group("name")) if name_match else requested_name,
        address=_decode_json_escaped_text(address_match.group("address")) if address_match else "",
        rating=_safe_float(rating_match.group("rating")) if rating_match else None,
        review_count=_safe_int(count_match.group("count")) if count_match else None,
        source="TripAdvisor",
        place_url=page_url,
    )


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


def _quote_for_inline(review: Optional[Dict[str, object]]) -> str:
    if not isinstance(review, dict):
        return ""
    text = str(review.get("translated_content_en") or review.get("content") or "").strip()
    text = _normalize_whitespace(text)
    if not text:
        return ""
    if len(text) > 180:
        text = text[:177].rstrip() + "..."
    return text


def _build_inline_summary(
    requested_place_name: str,
    place: Optional[Dict[str, object]],
    review: Optional[Dict[str, object]],
    fallback_summary: Optional[Dict[str, object]],
) -> str:
    place_name = str((place or {}).get("name") or requested_place_name or "").strip()
    rating = (place or {}).get("rating")
    review_count = (place or {}).get("review_count")
    if rating is None and isinstance(fallback_summary, dict):
        rating = fallback_summary.get("average_rating")
    if review_count is None and isinstance(fallback_summary, dict):
        review_count = fallback_summary.get("total_reviews")

    parts = [place_name] if place_name else []
    rating_value = _safe_float(rating)
    review_total = _safe_int(review_count)
    if rating_value is not None and review_total is not None:
        parts.append(f"{rating_value:.1f} stars from {review_total:,} reviews")
    elif rating_value is not None:
        parts.append(f"{rating_value:.1f} stars")
    elif review_total is not None:
        parts.append(f"{review_total:,} reviews")

    sentence = ", ".join(parts)
    quote = _quote_for_inline(review)
    if quote:
        if sentence:
            sentence = f'{sentence}. "{quote}"'
        else:
            sentence = f'"{quote}"'
    return sentence


def search_recent_reviews(
    destination: str,
    place_name: str,
    limit: int = 1,
    translate_to_english: bool = True,
) -> Dict[str, object]:
    serpapi_error: Optional[str] = None
    try:
        serpapi_candidate = _pick_serpapi_result(destination, place_name)
    except Exception as exc:
        serpapi_candidate = None
        serpapi_error = f"SerpApi Google Maps review lookup failed: {exc}"

    if isinstance(serpapi_candidate, dict):
        place = _place_from_serpapi(serpapi_candidate, place_name, destination)
        try:
            selected_reviews = _fetch_serpapi_reviews(serpapi_candidate)[:limit]
        except Exception as exc:
            selected_reviews = []
            serpapi_error = f"SerpApi Google Maps review lookup failed: {exc}"
        if translate_to_english and selected_reviews:
            _translate_reviews_to_english(selected_reviews)

        payload: Dict[str, object] = {
            "restaurant": _place_payload(place),
            "reviews": [_review_payload(review) for review in selected_reviews],
            "used_fallback_summary": False,
            "review_source": place.source,
        }
        if not selected_reviews:
            fallback = _fallback_review_summary(place)
            if fallback is not None:
                payload["fallback_summary"] = fallback
                payload["used_fallback_summary"] = True
            else:
                payload["review_error"] = "SerpApi Google Maps lookup returned no usable review quote or summary."
        return payload

    page_url = _pick_tripadvisor_page_url(destination, place_name)
    if not page_url:
        payload = {
            "restaurant": {
                "name": place_name,
                "address": "",
                "url": _tripadvisor_search_link(place_name, destination),
                "source": "TripAdvisor",
            },
            "reviews": [],
            "used_fallback_summary": False,
            "review_source": "TripAdvisor",
            "review_error": "TripAdvisor review lookup failed to resolve a venue page.",
        }
        if serpapi_error:
            payload["review_error"] = f"{serpapi_error} | {payload['review_error']}"
        return payload

    try:
        page_html = _request_text(page_url)
    except Exception as exc:
        payload = {
            "restaurant": {
                "name": place_name,
                "address": "",
                "url": page_url,
                "source": "TripAdvisor",
            },
            "reviews": [],
            "used_fallback_summary": False,
            "review_source": "TripAdvisor",
            "review_error": f"TripAdvisor page fetch failed: {exc}",
        }
        if serpapi_error:
            payload["review_error"] = f"{serpapi_error} | {payload['review_error']}"
        return payload

    jsonld_objects = _extract_jsonld_objects(page_html)
    place = _parse_tripadvisor_place_from_jsonld(jsonld_objects, page_url, place_name)
    if place is None:
        place = _extract_tripadvisor_place_from_regex(page_html, page_url, place_name)

    reviews = _extract_tripadvisor_reviews_from_jsonld(jsonld_objects)
    if not reviews:
        regex_review = _extract_tripadvisor_review_from_regex(page_html)
        if regex_review is not None:
            reviews.append(regex_review)

    selected_reviews = reviews[:limit]
    if translate_to_english and selected_reviews:
        _translate_reviews_to_english(selected_reviews)

    payload: Dict[str, object] = {
        "restaurant": _place_payload(place),
        "reviews": [_review_payload(review) for review in selected_reviews],
        "used_fallback_summary": False,
        "review_source": "TripAdvisor",
    }
    if not selected_reviews:
        fallback = _fallback_review_summary(place)
        if fallback is not None:
            payload["fallback_summary"] = fallback
            payload["used_fallback_summary"] = True
        else:
            payload["review_error"] = "TripAdvisor page found but no structured review summary was available."
    if serpapi_error and not payload.get("reviews"):
        payload["review_error"] = f"{serpapi_error} | {payload.get('review_error', '')}".strip(" |")
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
                    "review_source": "TripAdvisor",
                    "inline_summary": None,
                    "merge_ready_line": None,
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
        inline_summary = _build_inline_summary(
            requested_place_name=place_name,
            place=review_result.get("restaurant") if isinstance(review_result.get("restaurant"), dict) else None,
            review=review_payload if isinstance(review_payload, dict) else None,
            fallback_summary=review_result.get("fallback_summary")
            if isinstance(review_result.get("fallback_summary"), dict)
            else None,
        )
        merge_ready_line = (
            f"{meal_type.title()}: {inline_summary}"
            if meal_type and inline_summary
            else inline_summary or None
        )
        results.append(
            {
                "day": day or None,
                "meal_type": meal_type or None,
                "requested_place_name": place_name,
                "place": review_result.get("restaurant"),
                "review": review_payload,
                "review_source": review_result.get("review_source") or "TripAdvisor",
                "inline_summary": inline_summary or None,
                "merge_ready_line": merge_ready_line,
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
        lines.append("")
        merge_ready_line = str(item.get("merge_ready_line") or "").strip()
        if merge_ready_line:
            lines.append(f"{item.get('day', 'Day')} - {merge_ready_line}")
        elif item.get("requested_place_name"):
            lines.append(
                f"{item.get('day', 'Day')} - {item.get('meal_type', 'meal').title()}: {item.get('requested_place_name')}"
            )
        if item.get("review_error"):
            lines.append(f"Error: {item.get('review_error')}")
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
