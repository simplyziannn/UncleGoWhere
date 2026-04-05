---
name: review-search-lite
description: Retrieve one recent TripAdvisor review per meal suggestion, plus average rating and review count, with optional English translation.
---

# review-search-lite

Purpose
- A lightweight review enrichment skill for meal suggestions inside a trip plan.
- It uses TripAdvisor venue search and venue pages to find the correct place, retrieve one review, and translate non-English content into English when configured.

Primary goal
- Given a destination and a list of breakfast/lunch/dinner places, return one recent review for each meal.
- Include the place name, address, TripAdvisor link, average rating, and total review count.
- If review text is unavailable, fall back to average rating and total review count instead of inventing content.
- Also produce a merge-ready inline meal line for the final itinerary:
  - `Breakfast: PLACE, 4.4 stars from 4,000 reviews. "Quote if available."`

Core output format
- Meal reviews for {DESTINATION}
- Day 1 - Breakfast: {PLACE}, 4.5 stars from 4,000 reviews. "Quote if available."

Inputs
- destination: string
- meals: array of objects
  - day: string (optional)
  - meal_type: string (breakfast, lunch, dinner, optional)
  - place_name: string
- translate_to_english: boolean (default true)

Behavior
- Resolve each place through TripAdvisor search and restaurant pages.
- Retry the TripAdvisor path up to 3 times before treating it as failed.
- Return one review per meal suggestion.
- Translate review text into English with the OpenAI API when `OPENAI_API_KEY` is configured and translation is enabled.
- Return a fallback summary with average stars and review count when review text is not available.
- Include a TripAdvisor venue link or TripAdvisor search link for the reviewed place.
- Reject vague meal placeholders such as `food anchors`, `lunch near ...`, or `near your base`; this skill expects named establishments.

Optional environment variables
- OPENAI_API_KEY
- OPENAI_TRANSLATION_MODEL
- OPENAI_MODEL

Notes
- Do not invent review text.
- TripAdvisor is the primary source for this skill.
- Do not drift into DuckDuckGo, generic web search, or other review sites.
- If translation fails, still return the raw review text when available.
