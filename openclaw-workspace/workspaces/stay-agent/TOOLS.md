# TOOLS.md — stay-agent

## Primary tool

SerpAPI Google Hotels via:
skills/hotel-search-lite/hotel_search.py

Tool path:
/home/ubuntu/tripclaw-monorepo/openclaw-workspace/workspaces/stay-agent/skills/hotel-search-lite/hotel_search.py

Exec example:
python3 hotel_search.py --destination "Chiang Mai" \
  --check_in 2026-12-16 --check_out 2026-12-20 \
  --adults 1 --currency USD

---

## Authentication

Environment variable: SERPAPI_API_KEY
Do not hardcode. Read from environment.

If auth fails:
- state live hotel pricing temporarily unavailable
- do not invent prices

---

## SerpAPI engines

Primary: engine=google_hotels
Detail lookup: engine=google_hotels + property_token
Reviews (optional, only if user explicitly requests): engine=google_hotels_reviews
Photos (optional): engine=google_hotels_photos

---

## Required parameters

Destination search:
- engine=google_hotels (required)
- q (required — destination string, e.g. "Chiang Mai")
- check_in_date (required, YYYY-MM-DD)
- check_out_date (required, YYYY-MM-DD)
- adults (default: 1)
- currency (default: USD)
- gl (default: sg)
- hl (default: en)
- api_key (required)

Property detail lookup (for shortlisted hotels only):
- engine=google_hotels (required)
- property_token (required)
- check_in_date and check_out_date (required)

---

## Defaults (silent)

| Arg | Default |
|-----|---------|
| adults | 1 |
| children | 0 |
| rooms | 1 |
| currency | USD |
| gl | sg |
| hl | en |

---

## Execution order

1. Run destination search with exact dates.
2. Extract candidates from `properties` array.
3. Reduce to shortlist of 3–5 hotels.
4. Run property detail lookup for shortlisted hotels only.
5. Rerank after pricing enrichment.
6. Return structured output.

Never finalize rankings before pricing data is processed.

---

## Shortlist rule

3–5 hotels including:
- 1 strongest balanced option
- 1 lowest-cost option
- 1 location-strong option
- up to 2 backups

---

## Reranking buckets

Best overall: balance price, location fit, quality signals.
Cheapest: lowest total_rate.extracted_lowest or rate_per_night.extracted_lowest.
Best location/value: strongest location fit at reasonable price.

---

## Price output rules

Preferred fields:
- total_rate.extracted_lowest
- rate_per_night.extracted_lowest

If price missing: label as "price unavailable". Do not guess.

---

## Return format

For each property:
- name
- area / neighbourhood
- nightly rate
- total cost for stay
- one brief fit note

---

## Failure handling

SerpAPI fails: return shortlist without prices, note pricing unavailable.
No results: state no results found for those dates.
Do not claim sold out unless source explicitly states it.

---

## Never

- Never use generic web search for hotel pricing
- Never invent prices
- Never rank cheapest without confirmed pricing data
- Never output unfiltered long hotel lists