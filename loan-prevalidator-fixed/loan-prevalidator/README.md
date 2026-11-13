# P8 - Loan Application Pre-Validator (BCS503 + BCS502)
Stack: React (Vite, Tailwind, Recharts) + Flask + SQLite (item 10 of the paper). 

## Run
Backend:  `cd backend && pip install -r requirements.txt && python app.py`   (http://127.0.0.1:5000) - delete old `loan.db` first
Frontend: `cd frontend && npm install && npm run dev`   (http://localhost:5173, proxies /api)
Tests:    `cd backend && pytest -v`          Comparison: `python compare_dfa_regex.py`     Demo: `python demo_workflow.py`
Docs:     `docs/DESIGN.md` (DFA tables, routing table, algorithm), `docs/TEST_CASES.md`

## Deploy (one container: Flask serves the built UI)
`docker build -t loan-prevalidator . && docker run -p 8000:8000 -v loan-data:/data loan-prevalidator`
On Render/Railway/Fly: deploy the Dockerfile, mount a persistent disk at `/data` (SQLite), keep ONE gunicorn worker.

## Documented assumptions
* Band: amount >= Rs 25,00,000 -> HIGH. Zones: North, South, East, West, Central.
* Priority-override rule (not specified in the paper): urgency Critical jumps the queue and may exceed an available handler's capacity.
* Identifier letter decides the category; description keywords only add a conflict note (Home > Vehicle > Personal > Education).
* Rejected reports keep status Pending inside the correction/fallback QUEUE; statuses stay Pending/Assigned/In Progress/Resolved.
