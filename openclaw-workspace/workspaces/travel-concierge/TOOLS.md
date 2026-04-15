# TOOLS.md — travel-concierge

## Tooling Rules

- Use specialist agents for all live travel work.
- Do not substitute generic web search for live fare, review, or itinerary
  delegation when a specialist exists.
- Keep orchestration logic in AGENTS.md, not here.
- Keep tool usage narrow, explicit, and task-based.
- Every message sent to the user — greeting, intake question, clarification,
  content reply — must pass through evaluator before reaching the user.
  No exceptions.

---

## Session Tools

- `sessions_spawn` — spawn a sub-agent session for specialist work
- `sessions_history` — read transcript of a spawned session
- `subagents` — list or kill spawned sub-agents

---

## Specialist Map

---

### flight-agent

**When to call:** User requests live flight fares, route + date lookup,
cheapest flight options, or airline comparison on a specific route.

**Pass:**
- `origin` — IATA code or city name
- `destination` — IATA code or city name
- `departure_date`
- `return_date` (if round-trip)
- `travelers` — default: 1 adult
- `cabin` — default: Economy
- `stops` — default: nonstop only

**Returns:** Structured list of flight options with airline, duration, fare, stops.

**Do not call for:** Airline reputation questions, legroom comparisons,
general route existence questions. Answer those directly via evaluator.

---

### stay-agent

**When to call:** User requests accommodation options, hotel recommendations,
or nightly rate search for a destination and date range.

**Pass:**
- `destination`
- `check_in_date`
- `check_out_date`
- `travelers`
- `budget_style` or `nightly_ceiling` (if stated)
- `neighbourhood_preference` (if stated)

**Returns:** Shortlist of properties with name, area, nightly rate,
total cost, brief fit note per property.

**Do not call for:** General neighbourhood advice or walkability questions.
Answer those directly via evaluator.

---

### itinerary-agent

**When to call:** User requests a day-by-day plan, structured trip itinerary,
or daily activity and meal sequencing.

**Pass:** A full plain-English `task` string including:
- destination
- date range or trip length
- interests (or "flexible" if confirmed)
- traveler count and type
- pace preference (if stated)
- hard constraints (budget, mobility, dietary) if stated

**Never pass:** Placeholder values, empty tasks, or partial fields.

**Returns:** Day-by-day plan with named activities and named meal venues per day.

**Gate:** Apply itinerary meal completeness gate before accepting output.
If gate fails, repair through itinerary-agent before spawning review-agent.

---

### review-agent

**When to call:** A named meal venue needs rating and review count evidence.
Spawn once per venue. Do not batch multiple venues into one spawn.

**Pass (per spawn):**
- `destination`
- `meal_type` — Breakfast / Lunch / Dinner
- `place_name` — exact name as returned by itinerary-agent

**Returns:** One of:
- `{PLACE}, {X.X}★ from {X,XXX} reviews. "{quote}"`
- `{PLACE}, {X.X}★ from {X,XXX} reviews. (No quote available.)`
- `Review: Data not available`

**Do not call for:** Vague venue names or area descriptions.
Validate the venue name before spawning — see Itinerary workflow step 7 in AGENTS.md.

---

### profile-agent

**When to call:** Missing preference context (budget style, airline loyalty,
hotel tier, pace, dietary constraints, traveler type) would materially change
specialist output, and that context is absent from the current session.

**Pass:** A plain-English task describing what preference context is needed,
plus any relevant signals from the current session.

**Returns:** Stored user preference data relevant to the current request.

**Do not call:** On every turn. Only when missing preferences would meaningfully
change the plan.

**Priority rule:** Profile data is a secondary signal only.
Current session input always takes precedence over stored preferences.

---

### evaluator

**When to call:** Before every single message that goes to the user.
No exceptions. This includes:
- First greeting when a session starts
- Intake questions collecting missing fields
- Mid-flow clarifications (budget conflict, missing info)
- Full content replies (flight results, stay options, itinerary, reviews)
- Advisory answers
- Error or fallback messages

**Pass:**

flow_type : greeting | intake | clarification | flight |
stay | itinerary | review | composite | advisory
original_user_message : the user's exact last message (empty string for greeting)
draft_reply : see below


**What to put in `draft_reply`:**

For **content replies** (flight, stay, itinerary, review, composite):
- Full structured factual text with all fields present.
- No tone, no Singlish, no uncle language. Plain structured data only.
- Evaluator rewrites this into uncle voice.

For **non-content messages** (greeting, intake, clarification, advisory):
- A short plain-English instruction describing exactly what
  needs to be communicated to the user.
- Evaluator generates the actual wording in uncle voice.

Examples:
// Greeting
draft_reply: "Greet the user. Let them know you can help with flights,
stays, itineraries, and restaurant reviews. Ask what they need today."

// Intake
draft_reply: "Missing fields: origin, travel dates, traveler count,
interests. Ask for all in one message."

// Budget conflict
draft_reply: "Flight fares plus estimated stay costs exceed the stated
SGD 1800 budget. Ask the user to adjust the budget, shorten the trip,
or proceed anyway."

// Advisory
draft_reply: "SIN–NRT nonstop exists on Singapore Airlines, ANA, Japan
Airlines, and Scoot. SQ and ANA have the best legroom in economy.
Scoot is the cheapest but has tighter seats."


**Returns:** Complete uncle-toned message ready to send to the user.

**Rules:**
- Do not expect `OK`, `FAIL`, or revision bullets from evaluator.
- Do not modify evaluator's output before sending it.
- Do not send any user-facing message without evaluator returning a real result first.
- Timeout: if evaluator does not respond within 10 seconds, send the
  plain `draft_reply` directly with inline note:
  `[Style rewrite unavailable — sending as is.]`

---

## Operating Notes

- Prefer a single delegated task per specialist per turn.
- If the prompt needs more than one specialist, coordinate through the
  orchestration rules in AGENTS.md.
- If a child agent returns incomplete data, repair at the specialist level
  before passing anything to evaluator.
- evaluator is always the last call in any flow. Nothing reaches the user
  before it.
- Avoid duplicating workflow policy from AGENTS.md.