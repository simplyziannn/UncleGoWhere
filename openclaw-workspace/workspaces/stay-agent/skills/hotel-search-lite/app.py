#!/usr/bin/env python3
"""FastAPI wrapper for hotel-search-lite (SerpApi Google Hotels).

Usage:
  uvicorn app:app --host 0.0.0.0 --port 8001
  POST /hotel-search with JSON body:
  {
    "destination": "Tokyo",
    "check_in_date": "2026-12-16",
    "check_out_date": "2026-12-20",
    "adults": 1,
    "children": 0,
    "currency": "USD"
  }
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optionalfrom hotel_search import SerpApiHotelSearch

class HotelSearchRequest(BaseModel):
    destination: str
    check_in_date: str
    check_out_date: str
    adults: Optional[int] = 1
    children: Optional[int] = 0
    currency: Optional[str] = "USD"

app = FastAPI(title="Hotel Search Lite API")

@app.post("/hotel-search")
async def hotel_search(req: HotelSearchRequest):
    try:
        client = SerpApiHotelSearch()
        results = client.search(
            destination=req.destination,
            check_in_date=req.check_in_date,
            check_out_date=req.check_out_date,
            adults=req.adults,
            children=req.children,
            currency=req.currency
        )
        return {"header": f"Stays for {req.destination} ({req.check_in_date} to {req.check_out_date})", "results": results}
    except Exception as e:
        return {"error": str(e)}
