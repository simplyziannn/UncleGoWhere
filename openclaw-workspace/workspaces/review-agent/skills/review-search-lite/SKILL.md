---
name: review-search-lite
description: Retrieve one recent Google Maps review per meal suggestion, plus average rating and review count, with optional English translation.
---

# review-search-lite

Purpose
- A lightweight review enrichment skill for meal suggestions inside a trip plan.
- It uses SerpApi Google Maps data to find the correct place, retrieve recent reviews, and translate non-English content into English when configured.

Primary goal
- Given a destination and a list of breakfast/lunch/dinner places, return one recent review for each meal.
- Include the place name, address, Google search link, average rating, and total review count.
- If review text is unavailable, fall back to average rating and total review count instead of inventing content.

Core output format
- Meal reviews for {DESTINATION}
- Day 1 - Breakfast: {PLACE}
- Address: ...
- Link: ...
- Average: 4.5 stars from 4000 reviews
- Review by {AUTHOR} ({DATE})
- Raw: ...
- English: ...

Inputs
- destination: string
- meals: array of objects
  - day: string (optional)
  - meal_type: string (breakfast, lunch, dinner, optional)
  - place_name: string
- translate_to_english: boolean (default true)

Behavior
- Resolve each place through SerpApi Google Maps / Google Local.
- Prefer recent Google Maps reviews via SerpApi `google_maps_reviews`.
- Retry the Google/SerpApi path up to 3 times before treating it as failed.
- Return one review per meal suggestion.
- Translate review text into English with the OpenAI API when `OPENAI_API_KEY` is configured and translation is enabled.
- Return a fallback summary with average stars and review count when review text is not available.
- Include a Google search link for the reviewed place.
- Reject vague meal placeholders such as `food anchors`, `lunch near ...`, or `near your base`; this skill expects named establishments.
- If Google/SerpApi is still unavailable after retries, TripAdvisor is an allowed fallback source for one clearly labeled review block.

Required environment variables
- SERPAPI_API_KEY

Optional environment variables
- OPENAI_API_KEY
- OPENAI_TRANSLATION_MODEL
- OPENAI_MODEL

Notes
- Do not invent review text.
- Do not quote unsupported sources when Google/SerpApi is the requested source.
- If translation fails, still return the raw review text when available.
