# TOOLS.md — travel-concierge

## Tooling rules

- Use specialist agents for all live travel work.
- Do not substitute generic web search when a specialist exists.
- Every outbound user message passes through evaluator. No exceptions.

---

## Session tools

- `sessions_spawn` — spawn a sub-agent session
- `sessions_history` — read transcript of a spawned session
- `subagents` — list or kill spawned sub-agents

---

## Specialist spawn contracts

### flight-agent
When: user requests live fares, route lookup, airline comparison on a specific route.

task format:
"Search nonstop economy flights from {ORIGIN} to {DEST}.
 Departure: {DEPARTURE_DATE}. Return: {RETURN_DATE} (omit if one-way).
 Travelers: {PAX} adult(s). Cabin: {CABIN}. Nonstop only: {YES/NO}.
 Return top 3 options with airline, departure time, arrival time,
 total duration, and price in SGD."

---

### stay-agent
When: user requests accommodation options or hotel shortlist.

task format:
"Find 3–5 mid-range hotels in {DEST}.
 Check-in: {CHECK_IN}. Check-out: {CHECK_OUT}.
 Travelers: {PAX} adult(s). Budget style: {BUDGET_STYLE}.
 Preferred neighbourhood: {NEIGHBOURHOOD} (omit if not stated).
 Return property name, area, nightly rate, total cost,
 and one brief fit note per property."

---

### itinerary-agent
When: user requests a day-by-day plan or structured itinerary.

task format:
"Plan a {N}-day itinerary for {DEST}.
 Dates: {START_DATE} to {END_DATE}.
 Travelers: {PAX} adult(s). Interests: {INTERESTS}.
 Preferred area: {AREA} (omit if not stated).
 Pace: {PACE} (omit if not stated).
 Constraints: {CONSTRAINTS} (omit if none).
 Name specific venues for Breakfast, Lunch, and Dinner every day.
 No vague placeholders — every meal must be a specific named place."

---

### review-agent
When: a named meal venue needs rating and review count evidence.
One spawn per venue. Do not batch.

task format:
"Find the Google Maps or TripAdvisor rating and review count
 for {PLACE_NAME} in {DEST}.
 Meal type: {MEAL_TYPE}.
 Return: place name, star rating, total review count,
 and one short representative quote.
 If no data found, return exactly: Review: Data not available"

---

### profile-agent
When: budget style, airline loyalty, hotel tier, pace, or traveler type
is absent from the current session and would materially change the plan.

task format:
"Retrieve stored preferences for this user.
 Current session context: {CONTEXT_SUMMARY}.
 Return relevant preferences: budget style, airline loyalty,
 hotel tier, pace, dietary constraints, traveler type."

Do not call on every turn.

---

### evaluator
When: before every single message sent to the user. No exceptions.

task format:
"flow_type: {greeting|intake|clarification|flight|stay|
            itinerary|review|composite|advisory}
 original_user_message: {user's exact last message, empty for greeting}
 draft_reply: {full plain structured reply OR plain-English instruction}"

For content replies: full factual structured data, no tone.
For non-content (greeting, intake, clarification):
  short plain-English instruction of what to communicate.
  Evaluator generates the wording.

Returns: complete uncle-toned message. Send it unchanged.
Timeout: 10 seconds. On timeout send draft_reply with:
[Style rewrite unavailable — sending as is.]

---

## Operating notes

- Never pass a task label or placeholder. Every task string must contain
  actual field values.
- Subagents have no access to conversation context. Everything they need
  must be inside the task string.
- evaluator is always the final call. Nothing reaches the user before it.