https://www.perplexity.ai/search/1f106747-c4f8-4667-86bf-17d5be55d2fa?0=c
https://www.perplexity.ai/search/1f106747-c4f8-4667-86bf-17d5be55d2fa?0=c
# Hotel Search Skill

This skill performs hotel search using **only SerpApi Google Hotels**. Xotelo is not used anywhere in this skill.[page:1][page:2]

## Scope

Use SerpApi's `google_hotels` engine as the single hotel data source for search results and property details.[page:2][page:1]
The same endpoint supports destination-style searches with `q` and detailed property lookup with `property_token`.[page:2][page:1]

## Required inputs

- `destination`: user-facing search text such as a city, neighborhood, landmark, or hotel name.[page:2]
- `check_in_date`: required in `YYYY-MM-DD` format.[page:2]
- `check_out_date`: required in `YYYY-MM-DD` format.[page:2]
- `adults`: optional, defaults to 2.[page:2]
- `children`: optional, defaults to 0.[page:2]
- `children_ages`: optional, must match the number of children when provided.[page:2]
- `currency`: optional, defaults to `USD` in SerpApi.[page:2]
- `gl`: optional country code for localization.[page:2]
- `hl`: optional language code for localization.[page:2]

## Search flow

1. Run a Google Hotels destination search with `engine=google_hotels`, `q`, `check_in_date`, and `check_out_date`.[page:2]
2. Read hotel candidates from `properties`; sponsored placements may also appear in `ads` and should be treated separately.[page:2]
3. Use each result's `property_token` as the canonical identifier for follow-up detail retrieval.[page:2]
4. When deeper validation is needed, call the same engine again with `property_token` to fetch property details such as address, phone, amenities, prices, nearby places, ratings, and review breakdowns.[page:1][page:2]
5. Rank candidates using structured SerpApi fields rather than scraping raw text.[page:2][page:1]

## Preferred pricing fields

Use price fields in this order when available:
- `total_rate.extracted_lowest`.[page:1][page:2]
- `rate_per_night.extracted_lowest`.[page:1][page:2]
- Fallback search-level fields like `extracted_price` on ads if needed.[page:2]

If discount metadata exists, preserve `original_rate_per_night`, `original_total_rate`, and `discount_remarks` in the normalized result.[page:1]
If cancellation data exists, preserve `free_cancellation`, `free_cancellation_until_date`, and `free_cancellation_until_time`.[page:1][page:2]

## Important fields to normalize

Normalize these fields when present:
- `name`.[page:1][page:2]
- `property_token`.[page:1][page:2]
- `type`.[page:1][page:2]
- `overall_rating` and `reviews`.[page:1][page:2]
- `hotel_class` or `extracted_hotel_class`.[page:1][page:2]
- `rate_per_night` and `total_rate`.[page:1][page:2]
- `prices` and `featured_prices`.[page:1]
- `amenities` and `excluded_amenities`.[page:1][page:2]
- `nearby_places`.[page:1][page:2]
- `images`.[page:1][page:2]
- `deal` and `deal_description`.[page:1]
- `serpapi_property_details_link` for reproducible detail lookup.[page:2]

## Filtering

SerpApi supports structured filters directly in the request, including:
- `sort_by` with `3` for lowest price, `8` for highest rating, and `13` for most reviewed.[page:2]
- `min_price` and `max_price`.[page:2]
- `rating` thresholds such as `7`, `8`, and `9`.[page:2]
- `hotel_class` such as `2`, `3`, `4`, or `5`.[page:2]
- `free_cancellation`, `special_offers`, and `eco_certified` for hotel results.[page:2]
- `amenities`, `brands`, and `property_types` where applicable.[page:2]

## Pagination

When more results are needed, continue with `next_page_token` from `serpapi_pagination`.[page:2]
Do not invent page numbers; use the provided token chain.[page:2]

## Failure handling

Check `search_metadata.status` first.[page:2]
If the status is not successful, surface the returned `error` message and stop rather than guessing.[page:2]
If a destination search returns a single-property detail view, rely on the indicated property-details response pattern rather than assuming a missing result set.[page:2]

## Non-goals

- Do not call Xotelo.
- Do not mix hotel inventory from other hotel APIs.
- Do not invent prices when SerpApi omits them.
