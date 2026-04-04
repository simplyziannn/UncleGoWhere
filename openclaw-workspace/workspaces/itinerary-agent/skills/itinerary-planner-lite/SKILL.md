---
name: itinerary-planner-lite
description: Build practical day-by-day itineraries using local discovery, events, route grouping, and weather-aware pacing.
---

# itinerary-planner-lite

Purpose
- A lightweight itinerary planning skill that turns a destination and trip window into a practical, day-by-day plan.
- It uses live place discovery, optional local events, approximate route grouping, and weather checks to avoid generic plans.

Primary goal
- Given a destination, dates or number of days, and traveler preferences, return a compact itinerary with morning, afternoon, evening, and planning notes for each day.

Core output format
- Itinerary for {DESTINATION} ({DATES})
- Day 1 - {AREA / THEME}
- Morning: ...
- Afternoon: ...
- Evening: ...
- Notes: ...

Inputs
- destination: string
- start_date: string (YYYY-MM-DD, optional if days provided)
- end_date: string (YYYY-MM-DD, optional)
- days: integer (optional if date range provided)
- traveler_type: string (solo, couple, family, friends, business, optional)
- budget_style: string (budget, balanced, premium; default balanced)
- interests: string list
- pace: string (slow, balanced, fast; default balanced)
- must_see: string list
- dietary_constraints: string list

Behavior
- Search live places for attractions and restaurants using SerpApi.
- Search local events when available and fold strong candidates into the plan.
- Group nearby places to reduce backtracking.
- Use weather data when available to favor indoor backups on poor-weather days.
- Never claim exact opening hours, reservation guarantees, or exact transit times unless verified.

Data sources
- Primary: SerpApi Google Local / Google Maps style results for attractions and restaurants.
- Secondary: SerpApi Google Events results for city events.
- Weather: OpenWeather forecast when configured.

Required environment variables
- SERPAPI_API_KEY

Optional environment variables
- OPENWEATHER_API_KEY

Notes
- If weather is unavailable, the itinerary still works and notes that weather checks were skipped.
- Route grouping uses coordinates when available and falls back to area-based grouping when needed.

End of SKILL.md
