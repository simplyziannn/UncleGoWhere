"""Helpers for flight-search-lite: input normalization and location handling."""

from typing import Tuple

# Simple mapping for common city names to IATA codes. This can be extended as needed.
CITY_TO_AIRPORT = {
    "singapore": "SIN",
    "sg": "SIN",
    "singapore changi": "SIN",
    "incheon": "ICN",
    "seoul": "ICN",  # prefer ICN for direct SIN-ICN flights
}


def normalize_location(name_or_code: str) -> Tuple[str, str]:
    """Return (code, label) for a given origin/destination input.
    If a known IATA code is provided, it's returned as-is. If a city name is
    provided, it is mapped to an IATA code when possible.
    """
    key = (name_or_code or "").strip().lower()
    code = name_or_code
    label = name_or_code
    if not code:
        return ("", "")
    if len(name_or_code) == 3 and name_or_code.isalpha():
        code = name_or_code.upper()
        label = name_or_code.upper()
    else:
        code = CITY_TO_AIRPORT.get(key, name_or_code.upper())
        label = name_or_code.title()
    return code, label


def normalize_locations(origin: str, destination: str) -> Tuple[str, str, str, str]:
    o_code, o_label = normalize_location(origin)
    d_code, d_label = normalize_location(destination)
    return o_code, d_code, o_label, d_label

