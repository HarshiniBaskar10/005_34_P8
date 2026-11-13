"""Generates docs/DESIGN.md (DFA tables, routing table, algorithm).  Run: python gen_docs.py"""
import os, tempfile
import database as db
from dfa_engine import LOAN_DFA, MONEY_DFA, CODE_REGEX, MONEY_REGEX

def trans(d):
    rows = {}
    for (f, ch), t in sorted(d.delta.items()):
        rows.setdefault((f, t), []).append(ch)
    out = ["| From | Symbols | To |", "|---|---|---|"]
    for (f, t), chs in rows.items():
        s = "".join(chs)
        s = "0-9" if s == "0123456789" else "1-9" if s == "123456789" else ",".join(s)
        out.append(f"| {f} | {s} | {t} |")
    out.append(f"| any other (incl. every unlisted pair) | - | {d.dead} |")
    return "\n".join(out)

c = db.init_db(os.path.join(tempfile.mkdtemp(), "d.db"))
rt = "\n".join(f"| {r['category']} | {r['band']} | {r['zone']} | {r['branch']} | {r['team']} | {r['p']} | {r['b']} |" for r in c.execute(
    "SELECT t.*,p.name p,b.name b FROM routing_table t JOIN handlers p ON p.id=t.primary_id JOIN handlers b ON b.id=t.backup_id ORDER BY t.id"))
md = f"""# Design document - P8 Loan Application Pre-Validator

## 1. Application-code DFA (BCS503)
Regex `{CODE_REGEX.pattern}` - M = (Q, Sigma, delta, q0, F): Q = q0..q11 + qD (13 states), Sigma = {{L,O,A,N,H,V,P,E,0-9}}, q0 start, F = {{q11}}.

```mermaid
stateDiagram-v2
  [*] --> q0
  q0 --> q1: L
  q1 --> q2: O
  q2 --> q3: A
  q3 --> q4: N
  q4 --> q5: H,V,P,E
  q5 --> q6: 0-9
  q6 --> q7: 0-9
  q7 --> q8: 0-9
  q8 --> q9: 0-9
  q9 --> q10: 0-9
  q10 --> q11: 0-9
  q11 --> [*]
```
{trans(LOAN_DFA)}

## 2. Money-field DFA (income / amount)
Regex `{MONEY_REGEX.pattern}` plus range check (income 10,000-10 Cr, amount 50,000-50 Cr). States: s0, d1..d9 (integer digits read), dot, f1, f2 (fraction digits), qD. F = {{d1..d9, f1, f2}}.

{trans(MONEY_DFA)}

## 3. Routing table (BCS502) - 40 rows
Routing key = (category, amount band, zone). 4 approval branches x 2 band desks x 5 zones. HIGH band: amount >= Rs 25,00,000 (assumption).

| Category | Band | Zone | Branch | Team | Primary | Backup |
|---|---|---|---|---|---|---|
{rt}

## 4. Dispatch algorithm
1. Extract routing key (category, band, zone) - only from a validated report (`extract_routing_key`).
2. Unknown zone / no table row -> Central Fallback queue (E401). Invalid report -> Correction queue (E1xx/E2xx/E3xx/E501), never dispatched.
3. Table primary eligible (available and load < capacity) -> ROUTED.
4. Else branch backup -> ESCALATION. Else other-band desk in same zone -> ESCALATION. Else least-loaded cross-zone handler -> ESCALATION.
5. Else if urgency = Critical -> PRIORITY_OVERRIDE (documented emergency rule: may exceed capacity of an available branch handler).
6. Else WAITING queue. Queue order = (priority Critical<High<Normal, submitted time, id). Re-run on every status/availability/capacity change.
7. Every decision is stored (route_decision, assigned_at, started_at, resolved_at) and logged in `routing_log`.
Statuses: Pending -> Assigned -> In Progress -> Resolved.

## 5. Reason codes
E101 missing code | E102 bad prefix | E103 unsupported type | E104 incomplete | E105 serial not 6 digits | E106 too long |
E201/E203 income/amount format | E202/E204 income/amount range | E301/E302 income/amount missing | E303 reporter | E304 zone missing |
E305 urgency | E306 contact | E401 unknown zone | E501 duplicate application ID
"""
os.makedirs("../docs", exist_ok=True)
open("../docs/DESIGN.md", "w").write(md)
print("written docs/DESIGN.md", len(md), "bytes")
