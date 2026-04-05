#!/usr/bin/env python3
"""Tiny FastAPI app wrapping itinerary-planner-lite."""

from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from itinerary_search import build_itinerary


class ItineraryRequest(BaseModel):
    destination: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    days: Optional[int] = None
    traveler_type: Optional[str] = None
    budget_style: Optional[str] = "balanced"
    interests: Optional[List[str]] = None
    pace: Optional[str] = "balanced"
    must_see: Optional[List[str]] = None
    dietary_constraints: Optional[List[str]] = None
    review_place: Optional[str] = None
    translate_reviews_to_english: Optional[bool] = False


app = FastAPI(title="Itinerary Planner Lite API")


@app.post("/itinerary-plan")
async def itinerary_plan(req: ItineraryRequest):
    try:
        return build_itinerary(
            destination=req.destination,
            start_date=req.start_date,
            end_date=req.end_date,
            days=req.days,
            traveler_type=req.traveler_type,
            budget_style=req.budget_style or "balanced",
            interests=req.interests or [],
            pace=req.pace or "balanced",
            must_see=req.must_see or [],
            dietary_constraints=req.dietary_constraints or [],
            review_place=req.review_place,
            translate_reviews_to_english=bool(req.translate_reviews_to_english),
        )
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/internal-itinerary-plan")
async def internal_itinerary_plan(req: ItineraryRequest):
    return await itinerary_plan(req)
