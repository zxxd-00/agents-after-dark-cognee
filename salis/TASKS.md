# Team tasks — build ends 8:00 PM

Everyone: clone, `pip install -r requirements.txt`, add `.env`, run `python -m pytest tests/`.
Work on your own branch, open a PR into `main`. Run the tests before every PR.

| Who | Owns (only edit these) | Task | Done when |
|---|---|---|---|
| **muneebsyed321** (lead) | `salis/nightshift.py`, merging PRs | Upload starter, get one real Run Now working end to end with a real key; merge everyone's PRs | Run Now shows a real report in the dashboard |
| **zxxd-00** | `salis/memory.py`, `salis/data.py` (rules) | Make Cognee recall reliable: test the seeded rule comes back; add 2–3 more confirmed rules / past lessons | `recall` returns the shipment-ID rule every time |
| **almajna** | `salis/builder.py` | Tune the construct/repair prompts with the real model; make sure output always validates | 5 Run Nows in a row produce valid workflows |
| **renogear** | `app.py` | Make the morning report clear for a non-technical judge: summary first, pass/fail colors, "what Cognee remembered" panel | A stranger understands the report in 20 seconds |
| **5th teammate** | demo + submission | Write the pitch, rehearse the 2-minute demo, record the video by 7:40, submit at foundersquare.org/submit (Cognee track) | Submitted before 8:00 |

## Checkpoints
- **6:45** — everyone has it running locally
- **7:15** — real end-to-end Run Now works on `main`
- **7:30** — feature freeze; only fixes
- **7:40** — record the demo video
- **7:55** — submitted

## Stretch (only if done early)
- Fo: after approval, send a carrier follow-up through Fo (needs Wajo access; ask at their table)
- Voice: text box → speech input (label it honestly; it's not a phone call)
