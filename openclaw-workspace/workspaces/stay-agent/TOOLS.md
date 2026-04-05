# Stay Agent Tools

This file defines the exact tool usage notes for stay-agent.

Use this file for:
- hotel search and pricing source details,
- parameter defaults,
- SerpApi hotel search and property-detail rules,
- exact execution behavior,
- fallback handling.

Do not invent alternate APIs or endpoints unless they are explicitly added here.

---

## Primary hotel search and pricing source

Primary hotel search and pricing source for MVP:
- SerpApi Google Hotels

Base API:
- https://serpapi.com/search.json

Relevant engines:
- `google_hotels`
- `google_hotels_reviews` (optional, only when review drill-down is needed)
- `google_hotels_photos` (optional, only when photo drill-down is needed)

Use SerpApi as both:
- the hotel discovery layer, and
- the exact-date pricing enrichment layer.

Do not use any Xotelo endpoints.
Do not reference hotel keys, location keys, RapidAPI Xotelo auth, or Xotelo fallback behavior.

---

## SerpApi authentication

SerpApi requests require an API key.

Pass it as:
- `api_key=${SERPAPI_API_KEY}`

Important:
- Do not hardcode the API key in prompt files.
- Read it from environment or approved local runtime config.
- The environment variable name used by stay-agent should be `SERPAPI_API_KEY`.
- If the local runtime uses a different variable name, normalize it before execution.

If SerpApi authentication is missing or rejected:
- state that live hotel pricing is temporarily unavailable,
- do not invent prices,
- continue with recommendation-only output if possible.

---

## Core architecture rule

Follow this order:

1. Normalize the stay request.
2. Query SerpApi Google Hotels for the destination and exact stay dates.
3. Build a candidate pool from returned hotel/property results.
4. Reduce to a shortlist of 3 to 5 hotels.
5. Fetch property-level detail for shortlisted hotels only when needed.
6. Rerank after pricing and detail enrichment.
7. Return final structured output.

Never finalize best overall / cheapest / best location-value before the SerpApi pricing response is processed.

---

## Required user inputs for pricing

Minimum required to run meaningful hotel pricing:
- destination
- check-in date
- check-out date

Recommended, but defaultable:
- adults
- children
- currency
- rooms

Default values:
- adults = 1
- children = 0
- rooms = 1
- currency = USD
- gl = sg
- hl = en

Do not ask for adults, children, or rooms if missing unless occupancy is likely to materially change the result.
Use defaults and continue.

---

## SerpApi parameter notes

### Destination search

Use SerpApi `engine=google_hotels` to search hotels for a destination and exact dates. SerpApi documents `q`, `check_in_date`, and `check_out_date` as key parameters for hotel searches, with optional occupancy and currency inputs.[web:1090][web:1077]

Expected parameters:
- `engine=google_hotels` (required)
- `q` (required; destination or hotel query)
- `check_in_date` (required, format `YYYY-MM-DD`)
- `check_out_date` (required, format `YYYY-MM-DD`)
- `adults` (optional, default `1`)
- `children` (optional, default `0`)
- `rooms` (optional when supported by workflow; default `1` if used)
- `currency` (optional, default `USD`)
- `gl` (optional, default `sg`)
- `hl` (optional, default `en`)
- `api_key` (required)

Interpretation:
- `q` should usually be destination-first, such as `Tokyo`, `Bangkok`, `Shinjuku Tokyo`, or `Bali resorts`
- use exact dates by default
- use user currency if explicitly stated
- otherwise use the system default currency
- keep `gl=sg` and `hl=en` unless the workflow specifies otherwise

### Property detail lookup

Use SerpApi `engine=google_hotels` with `property_token` when you already know the property identity from a search result and want richer hotel detail. SerpApi exposes `property_token` and a canonical property-details flow for drilling into individual hotel results.[web:1090][web:1100]

Expected parameters:
- `engine=google_hotels` (required)
- `property_token` (required)
- `q` (recommended; preserve original destination query when available)
- `check_in_date` (required)
- `check_out_date` (required)
- `adults` (optional, default `1`)
- `children` (optional, default `0`)
- `currency` (optional, default `USD`)
- `gl` (optional, default `sg`)
- `hl` (optional, default `en`)
- `api_key` (required)

Use property detail lookup only for shortlisted hotels or when hotel-level amenities / pricing detail meaningfully affects the final answer.
Do not do detail lookups for dozens of hotels in one pass unless explicitly needed.

### Reviews and photos

Use these only when the user explicitly asks for deeper hotel validation:
- `engine=google_hotels_reviews`
- `engine=google_hotels_photos`

SerpApi provides dedicated review and photo APIs keyed off `property_token`, but they are optional drill-down tools rather than default search steps.[web:1146][web:1141]

Do not use review or photo drill-down by default.

---

## Hotel identity resolution rules

SerpApi pricing works from destination search results and `property_token`. Search responses can include structured hotel results inside the `properties` array, and those properties can contain names, prices, reviews, amenities, and more.[web:1091]

For each shortlisted candidate, store:
- hotel name
- city or destination
- neighborhood or area if known
- `property_token`
- price status
- pricing payload summary

If `property_token` is already known, go straight to property detail lookup when needed.

If `property_token` is unknown:
1. run destination search with exact dates,
2. extract candidate hotels from returned `properties` first,
3. optionally inspect `ads` if they add useful options,
4. prefer exact or near-exact hotel matches when the user asked for a specific property,
5. avoid weak fuzzy matching when multiple similarly named hotels appear.

If hotel identity is ambiguous:
- do not force pricing onto the wrong hotel,
- mark pricing unavailable for that candidate,
- continue with other candidates.

Never assume two similarly named hotels are the same property without sufficient evidence.

---

## Candidate shortlist rule

Before property-detail enrichment, reduce to 3 to 5 hotels.

The shortlist should usually include:
- 1 strongest balanced option,
- 1 lowest-cost option,
- 1 location-strong option,
- plus up to 2 backups if the search space is noisy.

Do not perform deep lookups for dozens of hotels in one pass unless explicitly needed.
Keep calls focused and efficient.

---

## Reranking rule

After SerpApi pricing returns, rerank the shortlist.

Use these ranking buckets:

### Best overall
Balance:
- total price,
- nightly price,
- location fit,
- quality signals,
- practicality for the trip.

### Cheapest
Choose the lowest valid returned comparable price.
Prefer:
- `total_rate.extracted_lowest` for stay-total comparisons,
- `rate_per_night.extracted_lowest` for nightly comparisons.

SerpApi property results can include both `rate_per_night` and `total_rate`, each with extracted numeric values for comparison.[web:1091][web:1100]

### Best location/value
Choose the hotel with the strongest location fit that still has a reasonable returned price and acceptable review quality.

A hotel that was initially top-ranked may drop after pricing.
That is expected.
Pricing enrichment is allowed to change the final winners.

---

## Output price rules

Only show prices that came from the current SerpApi run.

If returned data includes:
- nightly rate -> show nightly rate
- total rate -> show total rate
- both -> show both if concise

Preferred fields:
- `rate_per_night.lowest`
- `rate_per_night.extracted_lowest`
- `total_rate.lowest`
- `total_rate.extracted_lowest`

SerpApi’s hotel/property responses document these price structures directly in the JSON output.[web:1091][web:1100]

If only one price field is present, use that field and label it clearly.

If price is missing:
- label as `price unavailable`
- do not guess
- do not compare it numerically to priced hotels

If the source returns multiple booking-source prices:
- prefer the clearest lowest comparable price
- optionally mention the booking source if useful
- do not overwhelm the user with too many vendor rows unless specifically asked

---

## Result interpretation rules

Prefer returned `properties` as the main structured hotel result set.
Use `ads` only as supplemental options when they add useful contrast or fill gaps. SerpApi explicitly documents that Google Hotels properties are parsed into the `properties` array in the JSON output.[web:1091]

Useful quality signals may include:
- `overall_rating`
- `reviews`
- `hotel_class` or `extracted_hotel_class`
- amenity lists
- nearby place and transport snippets
- free cancellation flags when present

SerpApi property details can include ratings, review counts, hotel class, amenities, nearby places, and pricing information.[web:1100][web:1091]

Do not over-trust any single signal.
Use price, rating, reviews, and location fit together.

---

## Date rules

Use exact dates by default.

Do not widen dates unless:
- the user explicitly allows flexibility, or
- the calling workflow explicitly asks for alternate-date optimization.

If the user asks:
- “cheapest around these dates”
- “best value that week”
- “is one day earlier cheaper”

then alternate-date exploration may be used through repeated SerpApi hotel searches.

Otherwise stick to exact requested dates.

---

## Currency rules

Use user-requested currency if provided.

If no currency is specified:
- use the system default currency,
- or the workflow default selected by TripClaw.

SerpApi supports a `currency` parameter for returned hotel prices.[web:1090]

Do not silently mix currencies across options.
If the source returns inconsistent currencies, normalize if possible or clearly label them.

---

## Failure handling

### If SerpApi pricing fails completely
Return:
- shortlisted recommendations without live prices,
- a clear note that current hotel pricing is temporarily unavailable.

Do not invent fallback prices.

### If no property token can be resolved
Keep the recommendation if it is still a good qualitative fit.
Label pricing as unavailable due to unresolved hotel identity.

### If SerpApi returns no useful results for the exact dates
Say that no rate data was found for those dates.
Do not claim the hotel is sold out unless the source explicitly indicates that.

### If only some hotels are priced successfully
Keep the successfully priced hotels in final ranking.
Mark others as `price unavailable`.

---

## Bad behavior to avoid

Never:
- use general web search as the main hotel pricing method
- use SEO hotel pages as live price evidence
- blindly map hotel names without identity checks
- rank `cheapest` without returned pricing
- output long unfiltered hotel lists
- ask unnecessary follow-up questions when defaults are enough
- skip reranking after price enrichment
- treat ads as the only hotel source when structured property results exist

---

## Suggested internal record shape

For each candidate, maintain a record like:

- `name`
- `city`
- `area`
- `property_type`
- `fit_notes`
- `property_token`
- `currency`
- `nightly_price`
- `total_price`
- `price_source`
- `price_status`
- `quality_score`
- `location_score`
- `value_score`
- `final_bucket`

This can be stored in memory or local workflow state before the final answer is produced.

---

## Final response pattern

Return:

Stays for {DESTINATION} ({CHECK-IN} to {CHECK-OUT})

Best overall
- Hotel name — area
- nightly and/or total price if available
- why it fits
- one tradeoff

Cheapest
- Hotel name — area
- nightly and/or total price if available
- why it fits
- one tradeoff

Best location/value
- Hotel name — area
- nightly and/or total price if available
- why it fits
- one tradeoff

Optional:
- up to 2 extra shortlisted options if they add useful contrast

Keep it concise.

# TOOLS.md

## Hotel Search

Implemented in `skills/hotel-search/`.

- Source: SerpApi Google Hotels only.
- Environment variable: `SERPAPI_API_KEY`.
- Search mode: `engine=google_hotels` with `q`, `check_in_date`, and `check_out_date`.
- Detail mode: `property_token` lookup on the same SerpApi Google Hotels engine.
- Pagination: use `next_page_token` from `serpapi_pagination` when present.[page:1]
- Pricing preference: prefer `total_rate.extracted_lowest`, then `rate_per_night.extracted_lowest`.[page:1]
- Xotelo: removed entirely.

## Files

- `skills/hotel-search/SKILL.md`: hotel-search workflow and rules.
- `skills/hotel-search/hotel_search.py`: Python implementation for search, normalization, details lookup, and shortlist ranking.

## Usage Notes

- Do not mix hotel inventory from other hotel APIs.
- Do not invent prices when SerpApi omits them.
- Preserve structured fields such as `property_token`, `overall_rating`, `reviews`, `amenities`, `images`, `featured_prices`, and cancellation metadata when available.[page:1]
- Surface SerpApi errors directly instead of guessing or silently falling back, because SerpApi exposes search status through `search_metadata.status` and error messages through `error`.[page:1]

