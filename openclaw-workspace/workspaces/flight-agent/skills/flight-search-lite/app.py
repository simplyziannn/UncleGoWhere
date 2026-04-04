#!/usr/bin/env python3
"""Tiny FastAPI app wrapping flight-search-lite (SerpAPI-based nonstop flights).

Usage:
- Run: uvicorn app:app --host 0.0.0.0 --port 8000
- Then POST to /flight-search with JSON body:
  {
    "origin": "SIN",
    "destination": "ICN",
    "departure": "2026-12-07",
    "return_date": "2026-12-17",
    "nonstop_only": true
  }
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

from flight_search import search_flights


class FlightSearchRequest(BaseModel):
    origin: str
    destination: str
    departure: str
    return_date: Optional[str] = None
    nonstop_only: Optional[bool] = True


def _split_header_and_lines(lines: List[str]):
    if not lines:
        return "", []
    header = lines[0]
    rest = lines[1:]
    return header, rest


app = FastAPI(title="Flight Search Lite API")


@app.post("/flight-search")
async def flight_search(req: FlightSearchRequest):
    origin = (req.origin or "").upper()
    destination = (req.destination or "").upper()
    departure = req.departure
    return_date = req.return_date
    nonstop = True if (req.nonstop_only is None) else bool(req.nonstop_only)

    try:
        lines = search_flights(
            origin,
            destination,
            departure,
            return_date,
            cabin="economy",
            passengers=1,
            nonstop_only=nonstop,
        )
        header, results = _split_header_and_lines(lines)
        if not header:
            header = f"Direct nonstop options for {origin} → {destination} ({departure}{' to ' + return_date if return_date else ''})"
        return {"header": header, "results": results}
    except Exception as e:
        return {"error": str(e)}


@app.post("/internal-flight-search")
async def internal_flight_search(req: FlightSearchRequest):
    origin = (req.origin or "").upper()
    destination = (req.destination or "").upper()
    departure = req.departure
    return_date = req.return_date
    nonstop = True if (req.nonstop_only is None) else bool(req.nonstop_only)

    lines = search_flights(origin, destination, departure, return_date, cabin="economy", passengers=1, nonstop_only=nonstop)
    header, results = _split_header_and_lines(lines)
    if not header:
        header = f"Direct nonstop options for {origin} → {destination} ({departure}{' to ' + return_date if return_date else ''})"
    return {"header": header, "results": results}
