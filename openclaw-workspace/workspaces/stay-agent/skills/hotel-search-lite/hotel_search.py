import os
import requests
import argparse
from typing import Any, Dict, List, Optional

SERPAPI_URL = "https://serpapi.com/search.json"


class HotelSearchError(Exception):
    pass


class SerpApiHotelSearch:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            raise HotelSearchError("Missing SERPAPI_API_KEY")

    def _request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        merged = {
            "engine": "google_hotels",
            "api_key": self.api_key,
            **params,
        }
        response = requests.get(SERPAPI_URL, params=merged, timeout=30)
        response.raise_for_status()
        data = response.json()

        status = data.get("search_metadata", {}).get("status")
        if status and status != "Success":
            raise HotelSearchError(data.get("error") or f"SerpApi status: {status}")
        if data.get("error"):
            raise HotelSearchError(data["error"])
        return data

    def search_hotels(
        self,
        destination: str,
        check_in_date: str,
        check_out_date: str,
        adults: int = 2,
        children: int = 0,
        children_ages: Optional[List[int]] = None,
        currency: str = "USD",
        gl: str = "us",
        hl: str = "en",
        sort_by: Optional[int] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        rating: Optional[int] = None,
        hotel_class: Optional[str] = None,
        amenities: Optional[str] = None,
        brands: Optional[str] = None,
        property_types: Optional[str] = None,
        free_cancellation: Optional[bool] = None,
        special_offers: Optional[bool] = None,
        eco_certified: Optional[bool] = None,
        next_page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "q": destination,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "children": children,
            "currency": currency,
            "gl": gl,
            "hl": hl,
        }

        if children_ages:
            if len(children_ages) != children:
                raise HotelSearchError("children_ages must match children")
            params["children_ages"] = ",".join(str(age) for age in children_ages)

        optional_fields = {
            "sort_by": sort_by,
            "min_price": min_price,
            "max_price": max_price,
            "rating": rating,
            "hotel_class": hotel_class,
            "amenities": amenities,
            "brands": brands,
            "property_types": property_types,
            "free_cancellation": free_cancellation,
            "special_offers": special_offers,
            "eco_certified": eco_certified,
            "next_page_token": next_page_token,
        }
        for key, value in optional_fields.items():
            if value is not None:
                params[key] = value

        return self._request(params)

    def get_property_details(
        self,
        property_token: str,
        destination: str,
        check_in_date: str,
        check_out_date: str,
        adults: int = 2,
        children: int = 0,
        currency: str = "USD",
        gl: str = "us",
        hl: str = "en",
    ) -> Dict[str, Any]:
        return self._request(
            {
                "property_token": property_token,
                "q": destination,
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "adults": adults,
                "children": children,
                "currency": currency,
                "gl": gl,
                "hl": hl,
            }
        )

    @staticmethod
    def _extract_price_block(item: Dict[str, Any]) -> Dict[str, Optional[float]]:
        total_rate = item.get("total_rate") or {}
        nightly = item.get("rate_per_night") or {}
        return {
            "total_price": total_rate.get("extracted_lowest"),
            "nightly_price": nightly.get("extracted_lowest"),
            "total_price_before_taxes": total_rate.get("extracted_before_taxes_fees"),
            "nightly_price_before_taxes": nightly.get("extracted_before_taxes_fees"),
        }

    def normalize_property(self, item: Dict[str, Any]) -> Dict[str, Any]:
        price_block = self._extract_price_block(item)
        return {
            "name": item.get("name"),
            "property_token": item.get("property_token"),
            "type": item.get("type"),
            "description": item.get("description"),
            "link": item.get("link"),
            "address": item.get("address"),
            "overall_rating": item.get("overall_rating"),
            "reviews": item.get("reviews"),
            "hotel_class": item.get("extracted_hotel_class") or item.get("hotel_class"),
            "check_in_time": item.get("check_in_time"),
            "check_out_time": item.get("check_out_time"),
            "amenities": item.get("amenities", []),
            "excluded_amenities": item.get("excluded_amenities", []),
            "nearby_places": item.get("nearby_places", []),
            "images": item.get("images", []),
            "prices": item.get("prices", []),
            "featured_prices": item.get("featured_prices", []),
            "deal": item.get("deal"),
            "deal_description": item.get("deal_description"),
            "free_cancellation": item.get("free_cancellation"),
            "free_cancellation_until_date": item.get("free_cancellation_until_date"),
            "free_cancellation_until_time": item.get("free_cancellation_until_time"),
            "serpapi_property_details_link": item.get("serpapi_property_details_link"),
            **price_block,
        }

    def shortlist(self, data, limit=10):
        properties = data.get("properties", [])
        normalized = [self.normalize_property(p) for p in properties]

        def score(x: Dict[str, Any]) -> tuple:
            price = x.get("total_price")
            if price is None:
                price = x.get("nightly_price")
            return (
                -float(x.get("overall_rating") or 0),
                -int(x.get("reviews") or 0),
                float(price) if price is not None else float("inf"),
            )

        return sorted(normalized, key=score)[:limit]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hotel search via SerpApi Google Hotels")
    parser.add_argument("--destination", required=True, help="Destination city or query (e.g. Tokyo, Bangkok)")
    parser.add_argument("--check_in", required=True, help="Check-in date (YYYY-MM-DD)")
    parser.add_argument("--check_out", required=True, help="Check-out date (YYYY-MM-DD)")
    parser.add_argument("--adults", type=int, default=1, help="Number of adults (default: 1)")
    parser.add_argument("--children", type=int, default=0, help="Number of children (default: 0)")
    parser.add_argument("--currency", default="USD", help="Currency code (default: USD)")
    parser.add_argument("--gl", default="us", help="Country code for localization (default: us)")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to return (default: 5)")
    args = parser.parse_args()

    client = SerpApiHotelSearch()
    results = client.search_hotels(
        destination=args.destination,
        check_in_date=args.check_in,
        check_out_date=args.check_out,
        adults=args.adults,
        children=args.children,
        currency=args.currency,
        gl=args.gl,
    )
    top = client.shortlist(results, limit=args.limit)
    if not top:
        print("No hotels found for the given search parameters.")
    else:
        for hotel in top:
            print({
                "name": hotel["name"],
                "rating": hotel["overall_rating"],
                "reviews": hotel["reviews"],
                "total_price": hotel["total_price"],
                "nightly_price": hotel["nightly_price"],
                "property_token": hotel["property_token"],
                "address": hotel.get("address"),
                "free_cancellation": hotel.get("free_cancellation"),
            })

