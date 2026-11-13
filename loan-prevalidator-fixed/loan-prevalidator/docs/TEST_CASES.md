# Test cases (run: `cd backend && pytest -v`)  - 32 test functions, 90+ parametrised cases

| # | Area | Input / scenario | Expected |
|---|---|---|---|
| 01 | DFA+regex | LOANH104920, LOANV000000, LOANP999999, LOANE123456 | both accept, final state q11 |
| 02 | DFA+regex | "", LOAN, LOANH12345, LOANH1234567, LOANX123456, loanh123456, spaces, newline, Arabic digits | both reject, E1xx reason |
| 03 | Agreement | 4000 random strings + boundary strings | DFA result == regex result |
| 04 | DFA definition | 13 states, F={q11}, dead state absorbs | holds |
| 05 | Failure point | LOANX123456 / LOANH12A456 / LOANH1234567 | E103 idx4 / E105 idx7 / E106 idx11 |
| 06-07 | Money regex | 10000, 9999.99, 100000001, 0, -5, 1,00,000, 012345, 1e6 | accept/reject with E201-E204, E301/E302 |
| 08 | Five categories | H, V, P, E codes + invalid code | Home, Vehicle, Personal, Education, Invalid |
| 09 | Conflicting patterns | Home code + "car and tuition" description | Home, conflict note (identifier wins) |
| 10 | Unmapped code | LOANZ123456 | Invalid, never a valid category |
| 11 | Malformed | LOANH12A456 | rejected before dispatch, correction queue, trace ends qD |
| 12 | Missing fields | blank income/amount/name/zone, bad urgency, bad contact | E301, E302, E303, E304, E305, E306 |
| 13 | Routing table | same loan from South/North/West/East, 4 branches | zone-specific handler, 40-row table |
| 14 | Unknown zone | zone = Atlantis | Central Fallback, E401 |
| 15 | Capacity overflow | 4th report to a capacity-3 desk | escalated to backup |
| 16 | Handler unavailable | primary goes offline | re-queued work moves to backup |
| 17 | All offline | every Home handler offline | Pending/WAITING, dispatched on recovery |
| 18 | Priority override | all Home handlers full, Critical report | PRIORITY_OVERRIDE, capacity exceeded |
| 19 | Queue ordering | Normal, High, Critical, Normal queued | Critical, High, then FIFO |
| 20 | Duplicate ID | same LOANH555555 twice | E501, one assignment only |
| 21 | Lifecycle | Assigned -> In Progress -> Resolved, illegal transition | allowed / ValueError, resolved_at stored |
| 22 | Capacity freed | resolve a report with one waiting | waiting report assigned |
| 23 | Seed + persistence | seed data, 20 handlers | all 5 categories, no invalid report assigned |
| 24 | API end-to-end | submit, track, duplicate, advance, stats | all via Flask + SQLite |
| 25 | Money DFA | 5000 random strings + boundaries | money DFA == money regex |
| 26 | Routing key | invalid report | ValueError; valid -> (Home, STANDARD, South) |
| 27 | Timestamps | assign, start | assigned_at kept, started_at set |
| 28 | Statuses | seed data | only Pending/Assigned/In Progress/Resolved |
| 29 | Fallback resubmit | Atlantis then South, same code | second is accepted (no E501) |
| 30 | Contact | 12345, 5876543210, 98765432101 | E306 |
| 31 | Escalation chain | primary+backup down, then other-band down | other-band same zone, then cross-zone |
| 32 | Classifier | "of course ... house", unmapped code + "car" | no false conflict; Invalid with note |
