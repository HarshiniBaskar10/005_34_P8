# Design document - P8 Loan Application Pre-Validator

## 1. Application-code DFA (BCS503)
Regex `LOAN[HVPE][0-9]{6}` - M = (Q, Sigma, delta, q0, F): Q = q0..q11 + qD (13 states), Sigma = {L,O,A,N,H,V,P,E,0-9}, q0 start, F = {q11}.

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
| From | Symbols | To |
|---|---|---|
| q0 | L | q1 |
| q1 | O | q2 |
| q10 | 0-9 | q11 |
| q2 | A | q3 |
| q3 | N | q4 |
| q4 | E,H,P,V | q5 |
| q5 | 0-9 | q6 |
| q6 | 0-9 | q7 |
| q7 | 0-9 | q8 |
| q8 | 0-9 | q9 |
| q9 | 0-9 | q10 |
| any other (incl. every unlisted pair) | - | qD |

## 2. Money-field DFA (income / amount)
Regex `[1-9][0-9]{0,8}(?:\.[0-9]{1,2})?` plus range check (income 10,000-10 Cr, amount 50,000-50 Cr). States: s0, d1..d9 (integer digits read), dot, f1, f2 (fraction digits), qD. F = {d1..d9, f1, f2}.

| From | Symbols | To |
|---|---|---|
| d1 | . | dot |
| d1 | 0-9 | d2 |
| d2 | . | dot |
| d2 | 0-9 | d3 |
| d3 | . | dot |
| d3 | 0-9 | d4 |
| d4 | . | dot |
| d4 | 0-9 | d5 |
| d5 | . | dot |
| d5 | 0-9 | d6 |
| d6 | . | dot |
| d6 | 0-9 | d7 |
| d7 | . | dot |
| d7 | 0-9 | d8 |
| d8 | . | dot |
| d8 | 0-9 | d9 |
| d9 | . | dot |
| dot | 0-9 | f1 |
| f1 | 0-9 | f2 |
| s0 | 1-9 | d1 |
| any other (incl. every unlisted pair) | - | qD |

## 3. Routing table (BCS502) - 40 rows
Routing key = (category, amount band, zone). 4 approval branches x 2 band desks x 5 zones. HIGH band: amount >= Rs 25,00,000 (assumption).

| Category | Band | Zone | Branch | Team | Primary | Backup |
|---|---|---|---|---|---|---|
| Home | STANDARD | North | Home Loans Division | Standard Desk | Kiran Joshi | Ananya Rao |
| Home | STANDARD | South | Home Loans Division | Standard Desk | Meera Iyer | Ananya Rao |
| Home | STANDARD | East | Home Loans Division | Standard Desk | Kiran Joshi | Ananya Rao |
| Home | STANDARD | West | Home Loans Division | Standard Desk | Meera Iyer | Ananya Rao |
| Home | STANDARD | Central | Home Loans Division | Standard Desk | Meera Iyer | Ananya Rao |
| Home | HIGH | North | Home Loans Division | High-Value Desk | Rohit Sharma | Ananya Rao |
| Home | HIGH | South | Home Loans Division | High-Value Desk | Neha Kapoor | Ananya Rao |
| Home | HIGH | East | Home Loans Division | High-Value Desk | Rohit Sharma | Ananya Rao |
| Home | HIGH | West | Home Loans Division | High-Value Desk | Neha Kapoor | Ananya Rao |
| Home | HIGH | Central | Home Loans Division | High-Value Desk | Neha Kapoor | Ananya Rao |
| Vehicle | STANDARD | North | Auto Finance Hub | Standard Desk | Manoj Tiwari | Deepa Menon |
| Vehicle | STANDARD | South | Auto Finance Hub | Standard Desk | Karthik Nair | Deepa Menon |
| Vehicle | STANDARD | East | Auto Finance Hub | Standard Desk | Manoj Tiwari | Deepa Menon |
| Vehicle | STANDARD | West | Auto Finance Hub | Standard Desk | Karthik Nair | Deepa Menon |
| Vehicle | STANDARD | Central | Auto Finance Hub | Standard Desk | Karthik Nair | Deepa Menon |
| Vehicle | HIGH | North | Auto Finance Hub | High-Value Desk | Sanjay Gill | Deepa Menon |
| Vehicle | HIGH | South | Auto Finance Hub | High-Value Desk | Vikram Singh | Deepa Menon |
| Vehicle | HIGH | East | Auto Finance Hub | High-Value Desk | Sanjay Gill | Deepa Menon |
| Vehicle | HIGH | West | Auto Finance Hub | High-Value Desk | Vikram Singh | Deepa Menon |
| Vehicle | HIGH | Central | Auto Finance Hub | High-Value Desk | Vikram Singh | Deepa Menon |
| Personal | STANDARD | North | Personal Credit Desk | Standard Desk | Rekha Das | Farhan Ali |
| Personal | STANDARD | South | Personal Credit Desk | Standard Desk | Sneha Kulkarni | Farhan Ali |
| Personal | STANDARD | East | Personal Credit Desk | Standard Desk | Rekha Das | Farhan Ali |
| Personal | STANDARD | West | Personal Credit Desk | Standard Desk | Sneha Kulkarni | Farhan Ali |
| Personal | STANDARD | Central | Personal Credit Desk | Standard Desk | Sneha Kulkarni | Farhan Ali |
| Personal | HIGH | North | Personal Credit Desk | High-Value Desk | Arjun Mehta | Farhan Ali |
| Personal | HIGH | South | Personal Credit Desk | High-Value Desk | Tara Bhatt | Farhan Ali |
| Personal | HIGH | East | Personal Credit Desk | High-Value Desk | Arjun Mehta | Farhan Ali |
| Personal | HIGH | West | Personal Credit Desk | High-Value Desk | Tara Bhatt | Farhan Ali |
| Personal | HIGH | Central | Personal Credit Desk | High-Value Desk | Tara Bhatt | Farhan Ali |
| Education | STANDARD | North | Education & Student Wing | Standard Desk | Amit Saxena | Kavya Reddy |
| Education | STANDARD | South | Education & Student Wing | Standard Desk | Priya Natarajan | Kavya Reddy |
| Education | STANDARD | East | Education & Student Wing | Standard Desk | Amit Saxena | Kavya Reddy |
| Education | STANDARD | West | Education & Student Wing | Standard Desk | Priya Natarajan | Kavya Reddy |
| Education | STANDARD | Central | Education & Student Wing | Standard Desk | Priya Natarajan | Kavya Reddy |
| Education | HIGH | North | Education & Student Wing | High-Value Desk | Rahul Verma | Kavya Reddy |
| Education | HIGH | South | Education & Student Wing | High-Value Desk | Lata Pillai | Kavya Reddy |
| Education | HIGH | East | Education & Student Wing | High-Value Desk | Rahul Verma | Kavya Reddy |
| Education | HIGH | West | Education & Student Wing | High-Value Desk | Lata Pillai | Kavya Reddy |
| Education | HIGH | Central | Education & Student Wing | High-Value Desk | Lata Pillai | Kavya Reddy |

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
