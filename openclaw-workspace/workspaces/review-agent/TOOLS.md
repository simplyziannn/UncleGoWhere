# TOOLS.md — review-agent

## Primary tool

SerpAPI Google Maps search via:
skills/review-search-lite/review_search.py

Tool path:
/home/ubuntu/tripclaw-monorepo/openclaw-workspace/workspaces/review-agent/skills/review-search-lite/review_search.py

Exec example:
python3 review_search.py --place "Pho Hoa Pasteur" --destination "Ho Chi Minh City"

---

## Arguments

| Arg | Required | Notes |
|-----|----------|-------|
| --place | YES | Exact venue name in double quotes |
| --destination | YES | City name in double quotes |

---

## Failure handling

If script fails or returns no results:
- Return exactly: Review: Data not available
- Do NOT invent ratings or review counts
- Do NOT search the web as a substitute

---

## Return format

{place_name}, {X.X}★ from {X,XXX} reviews. "{one short quote}"

Example:
Pho Hoa Pasteur, 4.3★ from 1,148 reviews. "A Saigon institution — still a belly-warming bowl worth every visit."