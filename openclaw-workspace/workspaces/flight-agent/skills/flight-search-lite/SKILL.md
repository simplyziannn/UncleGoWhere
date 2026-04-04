---
name: flight-search-lite
description: Search nonstop flights using SerpAPI Google Flights data and return concise top options.
---


# flight-search-lite

Purpose
- A lightweight flight search skill that returns nonstop options for user queries when live fares are unreliable. It uses fresh search results and never reuses or fabricates prices for different dates.

Primary goal
- Given origin, destination, and date window, return a concise list of nonstop options with up-to-date prices if visible. If prices aren’t readable for the exact dates, return the same format with price not available.

Core output format (always used when nonstop data is available):
Direct nonstop options for {ORIGIN} → {DESTINATION} ({DATES})

• Airline — Duration — Nonstop — from $Price
• Airline — Duration — Nonstop — from $Price

Fallback output format (when prices are not readable):
Direct nonstop options for {ORIGIN} → {DESTINATION} ({DATES})

• Airline — Duration — Nonstop — price not available
• Airline — Duration — Nonstop — price not available

Inputs
- origin: string (IATA or city, e.g., SIN)
- destination: string (IATA or city, e.g., ICN)
- depart_date: string (YYYY-MM-DD)
- return_date: string (YYYY-MM-DD, optional for round-trip)
- cabin: string (economy, premium_economy, business) [default: economy]
- passengers: int (default: 1)
- nonstop_only: boolean (default: true)

Behavior
- Treat every query as fresh; never reuse prior prices or results unless the exact route/date match is requested again by the user.
- If nonstop_only is true, filter to nonstop options only.
- If prices are readable on the current data sources, include them; otherwise show price not available.
- Do not include links in the output; output is plain text only.
- Prefer data from simple, readable sources (e.g., aggregator snippets) and avoid hard-to-scrape dynamic pages.

Data sources (priority)
- Primary: simple web search results (Google-like flight listings) for the requested route/date.
- Secondary: airline or aggregator pages that display non-stop options in readable form.
- Tertiary: other trusted route listings if needed.

Examples
- Example 1 (round-trip, Dec 7–Dec 10, 2026):
  - Direct nonstop options for SIN → ICN (2026-12-07 to 2026-12-10)
  - Scoot — 6h 15m — Nonstop — from $635
  - Singapore Airlines — 6h 25m — Nonstop — from $817

- Example 2 (one-way, Jun 7, 2026):
  - Direct nonstop options for SIN → ICN (Jun 7, 2026)
  - Scoot — 6h 15m — Nonstop — price not available

Notes
- The skill is designed to operate without exposing live links in responses.
- Prices are not guaranteed and may change; verify on the source page when you see a price.

End of SKILL.md
