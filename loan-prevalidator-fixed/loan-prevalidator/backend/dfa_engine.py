"""BCS503 - Automata Theory: explicit DFA + equivalent regex validation engine.

Application code language:  L = LOAN [HVPE] [0-9]{6}      (length 11)
Regex (equivalent):         LOAN[HVPE][0-9]{6}
Money fields (regex):       [1-9][0-9]{0,8}(\\.[0-9]{1,2})?  + numeric range check
Money fields (DFA):         14-state DFA built below (s0, d1..d9, dot, f1, f2, qD) - equivalent to the money regex
Contact (regex):            [6-9][0-9]{9}
"""
import re
from decimal import Decimal

TYPE_MAP = {"H": "Home", "V": "Vehicle", "P": "Personal", "E": "Education"}
CATEGORIES = ["Home", "Vehicle", "Personal", "Education", "Invalid"]
CODE_REGEX = re.compile(r"LOAN[HVPE][0-9]{6}")
MONEY_REGEX = re.compile(r"[1-9][0-9]{0,8}(?:\.[0-9]{1,2})?")
CONTACT_REGEX = re.compile(r"[6-9][0-9]{9}")
INCOME_RANGE = (Decimal("10000"), Decimal("100000000"))      # INR / year
AMOUNT_RANGE = (Decimal("50000"), Decimal("500000000"))      # INR

# Deterministic classification priority when several patterns match (documented rule):
#   1) the identifier TYPE letter is authoritative;
#   2) description keyword patterns only ever add a conflict note;
#   3) among keyword-only matches the fixed order Home > Vehicle > Personal > Education applies.
PRIORITY_ORDER = ["Home", "Vehicle", "Personal", "Education"]
KEYWORDS = {   # regex alternatives, matched on word boundaries
    "Home": ["house", "home", "flat", "apartment", "property", "mortgage", "plot"],
    "Vehicle": ["car", "bike", "vehicle", "truck", "scooter", "motorcycle", "(?:two|four)[ -]wheeler"],
    "Personal": ["wedding", "medical", "travel", "personal loan", "debt"],
    "Education": ["tuition", "college", "university", "student", "course fee", "masters", "school fee"],
}


class DFA:
    """M = (Q, Sigma, delta, q0, F) with an explicit absorbing dead state."""

    def __init__(self, states, alphabet, delta, start, accepts, dead):
        self.Q, self.Sigma, self.delta = list(states), set(alphabet), dict(delta)
        self.q0, self.F, self.dead = start, set(accepts), dead

    def step(self, state, ch):
        return self.delta.get((state, ch), self.dead)

    def run(self, text):
        state, trace = self.q0, []
        for i, ch in enumerate(text):
            nxt = self.step(state, ch)
            trace.append({"step": i + 1, "index": i, "symbol": ch, "from": state, "to": nxt,
                          "in_alphabet": ch in self.Sigma})
            state = nxt
            if state == self.dead:
                break
        return {"accepted": state in self.F, "final_state": state, "trace": trace,
                "fail_index": trace[-1]["index"] if state == self.dead else None}


def build_loan_dfa():
    Q = [f"q{i}" for i in range(12)] + ["qD"]
    delta = {}
    for i, ch in enumerate("LOAN"):
        delta[(f"q{i}", ch)] = f"q{i + 1}"
    for t in "HVPE":
        delta[("q4", t)] = "q5"
    for i in range(5, 11):
        for d in "0123456789":
            delta[(f"q{i}", d)] = f"q{i + 1}"
    return DFA(Q, "LOANHVPE0123456789", delta, "q0", {"q11"}, "qD")


LOAN_DFA = build_loan_dfa()
DFA_SPEC = {
    "states": LOAN_DFA.Q, "alphabet": sorted(LOAN_DFA.Sigma), "start": "q0",
    "accepts": sorted(LOAN_DFA.F), "dead": "qD",
    "delta": [{"from": k[0], "symbol": k[1], "to": v} for k, v in sorted(LOAN_DFA.delta.items())],
    "regex": CODE_REGEX.pattern,
}


def build_money_dfa():
    """DFA for [1-9][0-9]{0,8}(\\.[0-9]{1,2})?  -  d_i = i integer digits read, f_j = j fraction digits read."""
    digits, nonzero = "0123456789", "123456789"
    Q = ["s0"] + [f"d{i}" for i in range(1, 10)] + ["dot", "f1", "f2", "qD"]
    delta = {("s0", ch): "d1" for ch in nonzero}
    for i in range(1, 9):
        for ch in digits:
            delta[(f"d{i}", ch)] = f"d{i + 1}"
    for i in range(1, 10):
        delta[(f"d{i}", ".")] = "dot"
    for ch in digits:
        delta[("dot", ch)] = "f1"
        delta[("f1", ch)] = "f2"
    accepts = {f"d{i}" for i in range(1, 10)} | {"f1", "f2"}
    return DFA(Q, digits + ".", delta, "s0", accepts, "qD")


MONEY_DFA = build_money_dfa()
MONEY_DFA_SPEC = {
    "states": MONEY_DFA.Q, "alphabet": sorted(MONEY_DFA.Sigma), "start": "s0", "accepts": sorted(MONEY_DFA.F),
    "dead": "qD", "regex": MONEY_REGEX.pattern,
    "delta": [{"from": k[0], "symbol": k[1], "to": v} for k, v in sorted(MONEY_DFA.delta.items())],
}


def validate_code(code):
    """Run DFA and regex side by side; explain the exact failure point."""
    code = "" if code is None else str(code)
    if code == "":
        return {"ok": False, "reason_code": "E101", "reason": "Application code is required.",
                "dfa_accept": False, "regex_accept": False, "agree": True, "trace": [],
                "final_state": "q0", "fail_index": None, "category": None}
    res = LOAN_DFA.run(code)
    rx = CODE_REGEX.fullmatch(code) is not None
    out = {"dfa_accept": res["accepted"], "regex_accept": rx, "agree": res["accepted"] == rx,
           "trace": res["trace"], "final_state": res["final_state"], "fail_index": res["fail_index"]}
    if res["accepted"]:
        return {**out, "ok": True, "reason_code": None, "reason": None, "category": TYPE_MAP[code[4]]}
    i = res["fail_index"]
    if i is not None:
        ch, frm = code[i], res["trace"][-1]["from"]
        if i < 4:
            code_, msg = "E102", f"Code must start with 'LOAN'; found {ch!r} at position {i + 1} (DFA {frm} -> dead state qD)."
        elif i == 4:
            code_, msg = "E103", f"Unsupported loan type {ch!r} at position 5; allowed types are H, V, P, E."
        elif i < 11:
            code_, msg = "E105", f"Serial must be exactly 6 digits; found {ch!r} at position {i + 1}."
        else:
            code_, msg = "E106", "Code too long: extra characters after the 6-digit serial."
    else:
        left = 11 - int(res["final_state"][1:])
        code_, msg = "E104", f"Incomplete code: DFA halted in non-accepting state {res['final_state']}; {left} more character(s) needed."
    return {**out, "ok": False, "reason_code": code_, "reason": msg, "category": None}


def validate_money(raw, kind):
    """Income/amount: DFA and regex run side by side, then a numeric range check."""
    lo, hi = INCOME_RANGE if kind == "income" else AMOUNT_RANGE
    miss, fmt, rng = {"income": ("E301", "E201", "E202"), "amount": ("E302", "E203", "E204")}[kind]
    s = "" if raw is None else str(raw)
    if s == "":
        return {"ok": False, "reason_code": miss, "reason": f"{kind.capitalize()} is required.", "value": None}
    d = MONEY_DFA.run(s)
    rx = MONEY_REGEX.fullmatch(s) is not None
    eng = {"dfa_accept": d["accepted"], "regex_accept": rx, "agree": d["accepted"] == rx, "final_state": d["final_state"]}
    if not (d["accepted"] and rx):
        return {"ok": False, "reason_code": fmt, "value": None, **eng,
                "reason": f"{kind.capitalize()} must be a positive plain number (no commas/symbols/leading zeros, max 2 decimals)."}
    v = Decimal(s)
    if not lo <= v <= hi:
        return {"ok": False, "reason_code": rng, "value": float(v), **eng,
                "reason": f"{kind.capitalize()} must be between {lo:,} and {hi:,}."}
    return {"ok": True, "reason_code": None, "reason": None, "value": float(v), **eng}


def validate_contact(raw):
    s = "" if raw is None else str(raw).strip()
    if s == "":
        return {"ok": False, "reason_code": "E306", "reason": "Reporter contact number is required."}
    if CONTACT_REGEX.fullmatch(s) is None:
        return {"ok": False, "reason_code": "E306", "reason": "Contact must be a 10-digit mobile number starting with 6-9."}
    return {"ok": True, "reason_code": None, "reason": None}


def keyword_matches(description):
    d = (description or "").lower()
    return [c for c in PRIORITY_ORDER if any(re.search(rf"\b(?:{k})\b", d) for k in KEYWORDS[c])]


def classify(code_category, description=""):
    """Returns (category, note). Exactly five categories; an unmapped identifier is NEVER given a valid category."""
    hits = keyword_matches(description)
    if code_category not in PRIORITY_ORDER:
        note = (f"Identifier is not mapped to a loan type; description suggests {hits[0]} but a valid category is "
                "never assigned from keywords alone.") if hits else None
        return "Invalid", note
    other = [c for c in hits if c != code_category]
    note = (f"Pattern conflict: identifier says {code_category}, description also matches {', '.join(other)}. "
            "Rule applied: identifier wins; keyword ties break Home > Vehicle > Personal > Education.") if other else None
    return code_category, note


def validate_application(code, income, amount, reporter=None, zone=None, contact=None):
    cr = validate_code(code)
    inc, amt = validate_money(income, "income"), validate_money(amount, "amount")
    errors = []
    if not cr["ok"]:
        errors.append({"field": "application_code", "code": cr["reason_code"], "reason": cr["reason"]})
    for f, r in (("income", inc), ("amount", amt)):
        if not r["ok"]:
            errors.append({"field": f, "code": r["reason_code"], "reason": r["reason"]})
    if reporter is not None and len(reporter.strip()) < 2:
        errors.append({"field": "reporter_name", "code": "E303", "reason": "Reporter name is required."})
    if zone is not None and not zone.strip():
        errors.append({"field": "zone", "code": "E304", "reason": "Zone is required."})
    if contact is not None:
        ct = validate_contact(contact)
        if not ct["ok"]:
            errors.append({"field": "reporter_contact", "code": ct["reason_code"], "reason": ct["reason"]})
    return {"is_valid": not errors, "category": cr["category"] if not errors else "Invalid",
            "reason_code": errors[0]["code"] if errors else None,
            "reason_text": errors[0]["reason"] if errors else None,
            "errors": errors, "code_result": cr, "income": inc, "amount": amt}
