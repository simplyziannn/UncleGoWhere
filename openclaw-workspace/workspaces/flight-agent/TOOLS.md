# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## Primary Tool

**Local SerpAPI Script** (run via `exec`):

python3 /home/ubuntu/openclaw-workspace/workspaces/flight-agent/skills/flight-search-lite/flight_search.py --origin {IATA} --destination {IATA} --departure YYYY-MM-DD [--return YYYY-MM-DD] [--nonstop] [--cabin economy] [--passengers 1]

**Args**:
- Required: `--origin`, `--destination`, `--departure`.
- Defaults: 2026 year, 1 adult, economy, nonstop.
- SerpAPI: Google Flights via SerpAPI (configured in script).

**Examples**:

Nonstop SIN-NRT
python3 ... --origin SIN --destination NRT --departure 2026-12-16 --nonstop

Round-trip with return
python3 ... --origin SIN --destination LAX --departure 2026-12-16 --return 2026-12-26


## Tool Rules

- **Run FIRST** for live pricing.
- **Parse**: airline, duration, price, times, nonstop.
- **Fail**: Return "Live pricing unavailable".
- **No web/browse**: Script only.
- **Output**: JSON/table for concierge parsing.

## Fallbacks (Last Resort)

- No SerpAPI → "Tool unavailable".
- No results → "No {nonstop} flights found".

**No invention**. No generic search snippets.