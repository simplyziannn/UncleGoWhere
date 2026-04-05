#!/usr/bin/env python3
"""Local smoke tests for itinerary meal enforcement."""

from __future__ import annotations

import os
import unittest

import itinerary_search as itinerary


def _stub_place(name: str, category: str, address: str, lat: float) -> itinerary.Place:
    return itinerary.Place(
        name=name,
        category=category,
        address=address,
        rating=4.6,
        review_count=500,
        latitude=lat,
        longitude=139.70,
        source="stub",
    )


class ItineraryMealContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.originals = {
            "search_attractions": itinerary.search_attractions,
            "search_restaurants": itinerary.search_restaurants,
            "search_events": itinerary.search_events,
            "_forecast_by_day": itinerary._forecast_by_day,
        }
        self.previous_api_key = os.environ.get("SERPAPI_API_KEY")
        os.environ["SERPAPI_API_KEY"] = "test-key"

    def tearDown(self) -> None:
        itinerary.search_attractions = self.originals["search_attractions"]
        itinerary.search_restaurants = self.originals["search_restaurants"]
        itinerary.search_events = self.originals["search_events"]
        itinerary._forecast_by_day = self.originals["_forecast_by_day"]
        if self.previous_api_key is None:
            os.environ.pop("SERPAPI_API_KEY", None)
        else:
            os.environ["SERPAPI_API_KEY"] = self.previous_api_key

    def test_build_itinerary_requires_named_meals(self) -> None:
        itinerary.search_attractions = lambda destination, interests, must_see: [
            _stub_place("Senso-ji", "attraction", "Asakusa, Tokyo, Japan", 35.7148),
            _stub_place("Ueno Park", "attraction", "Ueno, Tokyo, Japan", 35.7147),
            _stub_place("Meiji Jingu", "attraction", "Shibuya, Tokyo, Japan", 35.6764),
        ]
        itinerary.search_restaurants = lambda destination, dietary_constraints, budget_style, interests: {
            "breakfast": [_stub_place("Coffee Supreme", "restaurant", "Shibuya, Tokyo, Japan", 35.6595)],
            "lunch": [_stub_place("Sometaro", "restaurant", "Asakusa, Tokyo, Japan", 35.7144)],
            "dinner": [_stub_place("Kagari Ginza", "restaurant", "Ginza, Tokyo, Japan", 35.6717)],
            "budget": [_stub_place("Tsujihan", "restaurant", "Nihonbashi, Tokyo, Japan", 35.6834)],
            "best": [_stub_place("Ise Sueyoshi", "restaurant", "Roppongi, Tokyo, Japan", 35.6627)],
        }
        itinerary.search_events = lambda destination: []
        itinerary._forecast_by_day = lambda latitude, longitude: {}

        plan = itinerary.build_itinerary(
            destination="Tokyo",
            start_date="2026-12-16",
            end_date="2026-12-18",
            traveler_type="6 adults",
            interests=["culture"],
            pace="relaxed",
        )

        self.assertEqual(len(plan["days"]), 3)
        for day in plan["days"]:
            self.assertTrue(day["breakfast_place"]["name"])
            self.assertTrue(day["lunch_place"]["name"])
            self.assertTrue(day["dinner_place"]["name"])
            self.assertIn("Breakfast at", day["breakfast"])
            self.assertIn("Lunch at", day["lunch"])
            self.assertIn("Dinner at", day["dinner"])

    def test_build_itinerary_fails_if_no_concrete_meals_exist(self) -> None:
        itinerary.search_attractions = lambda destination, interests, must_see: [
            _stub_place("Senso-ji", "attraction", "Asakusa, Tokyo, Japan", 35.7148),
        ]
        itinerary.search_restaurants = lambda destination, dietary_constraints, budget_style, interests: {
            "breakfast": [],
            "lunch": [],
            "dinner": [],
            "budget": [],
            "best": [],
        }
        itinerary.search_events = lambda destination: []
        itinerary._forecast_by_day = lambda latitude, longitude: {}

        with self.assertRaisesRegex(RuntimeError, "Concrete meal planning incomplete"):
            itinerary.build_itinerary(
                destination="Tokyo",
                start_date="2026-12-16",
                days=1,
                interests=["culture"],
            )


if __name__ == "__main__":
    unittest.main()
