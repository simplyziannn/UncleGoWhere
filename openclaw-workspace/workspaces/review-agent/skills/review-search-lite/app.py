#!/usr/bin/env python3
"""Tiny FastAPI app wrapping review-search-lite."""

from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from review_search import search_meal_reviews


class MealInput(BaseModel):
    day: Optional[str] = None
    meal_type: Optional[str] = None
    place_name: str


class ReviewRequest(BaseModel):
    destination: str
    meals: List[MealInput]
    translate_to_english: Optional[bool] = True


app = FastAPI(title="Review Search Lite API")


@app.post("/meal-reviews")
async def meal_reviews(req: ReviewRequest):
    try:
        return search_meal_reviews(
            destination=req.destination,
            meals=[meal.model_dump() for meal in req.meals],
            translate_to_english=bool(req.translate_to_english),
        )
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/internal-meal-reviews")
async def internal_meal_reviews(req: ReviewRequest):
    return await meal_reviews(req)
