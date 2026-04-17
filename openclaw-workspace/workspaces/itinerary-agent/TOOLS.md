# TOOLS.md — itinerary-agent

## Primary tool

Local itinerary planner script via exec:

Tool path:
/home/ubuntu/tripclaw-monorepo/openclaw-workspace/workspaces/itinerary-agent/skills/itinerary-planner-lite/itinerary_search.py

Exec example:
python3 /home/ubuntu/tripclaw-monorepo/openclaw-workspace/workspaces/itinerary-agent/skills/itinerary-planner-lite/itinerary_search.py \
  --destination "Ho Chi Minh City" \
  --start-date 2026-12-16 \
  --end-date 2026-12-20 \
  --interests "local cafes" \
  --budget-style mid-range \
  --pace relaxed

---

## Arguments

| Arg | Required | Notes |
|-----|----------|-------|
| --destination | YES | Always wrap in double quotes if it contains spaces |
| --start-date | YES | YYYY-MM-DD |
| --end-date | YES | YYYY-MM-DD |
| --days | NO | Alternative to start/end date |
| --traveler-type | NO | solo, couple, family |
| --budget-style | NO | budget, mid-range, luxury |
| --interests | NO | quoted string, e.g. "local cafes, yoga" |
| --pace | NO | relaxed, moderate, packed |
| --must-see | NO | quoted list |
| --dietary-constraints | NO | quoted list |

---

## Destination quoting rule

Always wrap --destination in double quotes when it contains spaces.

Correct:   --destination "Ho Chi Minh City"
Correct:   --destination "Chiang Mai"
Incorrect: --destination Ho Chi Minh City
Incorrect: --destination Chiang Mai

---

## Failure handling

If the script fails or returns an error:
- Do NOT ask the user A or B options.
- Do NOT ask clarifying questions.
- Generate the itinerary directly from your own knowledge.
- Apply the same output format as the script would return.
- Name specific venues for every meal. No placeholders.

---

## Output format required

Return the itinerary in this exact structure:

Day {N} — {Theme}
Morning: {activity}
Breakfast: {SPECIFIC PLACE NAME}
Afternoon: {activity}
Lunch: {SPECIFIC PLACE NAME}
Evening: {activity}
Dinner: {SPECIFIC PLACE NAME}

Repeat for every day. No vague entries. No "or" options. No fallback wording.

---

## Never

- Never ask the user to choose between options A and B
- Never ask for clarification when the task string contains all required fields
- Never use placeholder meal names like "local café" or "nearby restaurant"
- Never leave a meal slot empty