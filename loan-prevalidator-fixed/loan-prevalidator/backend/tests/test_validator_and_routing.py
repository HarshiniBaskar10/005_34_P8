"""Run:  cd backend && pytest -v      (32 test functions, ~90 parametrised cases)"""
import os, sys, random, json
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db
import routing_engine as eng
from dfa_engine import (CODE_REGEX, LOAN_DFA, MONEY_DFA, MONEY_REGEX, classify, validate_application, validate_code, validate_money)
from seed_data import seed


@pytest.fixture
def conn(tmp_path):
    c = db.init_db(str(tmp_path / "t.db"))
    yield c
    c.close()


_n = [0]
def sub(c, code=None, income="1500000", amount="1000000", zone="South", urg="Normal", desc="", name="Test User", contact="9876543210"):
    _n[0] += 1
    code = code or f"LOANH{_n[0]:06d}"
    rid = eng.submit_report(c, dict(reporter_name=name, reporter_contact=contact, application_code=code, income=income, amount=amount, zone=zone, urgency=urg, description=desc))
    return c.execute("SELECT * FROM reports WHERE report_id=?", (rid,)).fetchone()

def hid(c, name): return c.execute("SELECT id FROM handlers WHERE name=?", (name,)).fetchone()[0]
def home_handlers(c, keep=()):
    return [x["id"] for x in c.execute("SELECT id FROM handlers WHERE category='Home' AND name NOT IN (%s)" % ",".join("?" * len(keep)) if keep else "SELECT id FROM handlers WHERE category='Home'", keep)]
def hname(c, r): return c.execute("SELECT name FROM handlers WHERE id=?", (r["handler_id"],)).fetchone()[0]
def fresh(c, r): return c.execute("SELECT * FROM reports WHERE id=?", (r["id"],)).fetchone()
def events(c, rid): return [e["event"] for e in c.execute("SELECT event FROM routing_log WHERE report_id=? ORDER BY id", (rid,))]

VALID = ["LOANH104920", "LOANV000000", "LOANP999999", "LOANE123456"]
INVALID = ["", "LOAN", "LOANH", "LOANH12345", "LOANH1234567", "LOANX123456", "loanh123456", "LOANH12A456",
           "LOAN H123456", " LOANH123456", "LOANH123456 ", "LOANH123456\n", "XLOANH123456", "LOANHH23456", "LOANH١٢٣٤٥٦"]


# ---------------- Part A: BCS503 ----------------
@pytest.mark.parametrize("code", VALID)
def test_01_valid_codes_accepted_by_dfa_and_regex(code):
    r = validate_code(code)
    assert r["dfa_accept"] and r["regex_accept"] and r["agree"] and r["ok"]
    assert r["final_state"] == "q11" and len(r["trace"]) == 11

@pytest.mark.parametrize("code", INVALID)
def test_02_invalid_codes_rejected_by_both_engines(code):
    r = validate_code(code)
    assert not r["dfa_accept"] and not r["regex_accept"] and r["agree"] and not r["ok"]
    assert r["reason_code"].startswith("E1") and r["reason"]

def test_03_dfa_regex_agreement_on_random_strings():
    rnd, alphabet = random.Random(503), "LOANHVPE0123456789 xl"
    for _ in range(4000):
        s = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 13)))
        assert LOAN_DFA.run(s)["accepted"] == (CODE_REGEX.fullmatch(s) is not None), s
    for t in "HVPEXZ":
        for tail in ("000000", "12345", "1234567", "12345a"):
            s = f"LOAN{t}{tail}"
            assert LOAN_DFA.run(s)["accepted"] == (CODE_REGEX.fullmatch(s) is not None), s

def test_04_dfa_formal_definition():
    assert len(LOAN_DFA.Q) == 13 and LOAN_DFA.q0 == "q0" and LOAN_DFA.F == {"q11"}
    assert LOAN_DFA.step("qD", "L") == "qD"                      # dead state absorbs
    assert LOAN_DFA.step("q4", "H") == "q5" and LOAN_DFA.step("q4", "X") == "qD"

@pytest.mark.parametrize("code,reason,idx", [
    ("LOA", "E104", None), ("LOANH12345", "E104", None), ("", "E101", None),
    ("LXAN123456", "E102", 1), ("LOANX123456", "E103", 4),
    ("LOANH12A456", "E105", 7), ("LOANH1234567", "E106", 11)])
def test_05_reason_codes_and_exact_failure_point(code, reason, idx):
    r = validate_code(code)
    assert r["reason_code"] == reason and r["fail_index"] == idx

@pytest.mark.parametrize("raw,ok,rc", [
    ("10000", True, None), ("9999.99", False, "E202"), ("100000000", True, None), ("100000001", False, "E202"),
    ("0", False, "E201"), ("-5", False, "E201"), ("1,00,000", False, "E201"), ("abc", False, "E201"),
    ("012345", False, "E201"), ("123456.789", False, "E201"), ("50000.50", True, None), ("", False, "E301")])
def test_06_income_regex_and_boundaries(raw, ok, rc):
    r = validate_money(raw, "income")
    assert r["ok"] is ok and r["reason_code"] == rc

@pytest.mark.parametrize("raw,ok,rc", [("50000", True, None), ("49999", False, "E204"), ("500000000", True, None),
                                       ("500000001", False, "E204"), ("1e6", False, "E203"), ("", False, "E302")])
def test_07_amount_regex_and_boundaries(raw, ok, rc):
    r = validate_money(raw, "amount")
    assert r["ok"] is ok and r["reason_code"] == rc

def test_08_all_five_categories(conn):
    got = {sub(c := conn, f"LOAN{t}{i:06d}")["category"] for i, t in enumerate("HVPE", 1)}
    got.add(sub(conn, "LOANX123456")["category"])
    assert got == {"Home", "Vehicle", "Personal", "Education", "Invalid"}

def test_09_conflicting_patterns_use_documented_priority(conn):
    cat, note = classify("Home", "buying a car and tuition for college")
    assert cat == "Home" and "identifier wins" in note
    r = sub(conn, "LOANV111111", desc="house renovation")
    assert r["category"] == "Vehicle" and r["conflict_note"]

def test_10_unmapped_identifier_never_gets_valid_category(conn):
    r = sub(conn, "LOANZ123456")
    assert r["category"] == "Invalid" and r["is_valid"] == 0 and r["reason_code"] == "E103"
    assert classify(None)[0] == "Invalid" and classify("Bogus")[0] == "Invalid"

def test_11_malformed_rejected_before_dispatch_and_persisted(conn):
    r = sub(conn, "LOANH12A456")
    assert r["handler_id"] is None and r["queue"] == "CENTRAL_CORRECTION" and r["status"] == "Pending"
    trace = json.loads(r["dfa_trace"])
    assert r["reason_code"] == "E105" and trace[-1]["to"] == "qD" and r["dfa_accept"] == 0 and r["regex_accept"] == 0
    assert events(conn, r["report_id"]) == ["REJECTED"]

def test_12_missing_fields_rejected_with_messages(conn):
    assert sub(conn, income="")["reason_code"] == "E301"
    assert sub(conn, amount="")["reason_code"] == "E302"
    assert sub(conn, name=" ")["reason_code"] == "E303"
    assert sub(conn, zone=" ")["reason_code"] == "E304"
    assert sub(conn, contact="12345")["reason_code"] == "E306"
    assert sub(conn, urg="Whenever")["reason_code"] == "E305"
    assert validate_application("LOANH104920", "1500000", "1000000")["is_valid"]


# ---------------- Part B: BCS502 ----------------
def test_13_routing_table_is_zone_aware(conn):
    assert conn.execute("SELECT COUNT(*) FROM routing_table").fetchone()[0] == 40
    assert hname(conn, sub(conn, zone="South")) == "Meera Iyer"
    assert hname(conn, sub(conn, zone="North")) == "Kiran Joshi"
    assert hname(conn, sub(conn, zone="West", amount="9000000")) == "Neha Kapoor"
    b = sub(conn, zone="East", amount="9000000")
    assert b["band"] == "HIGH" and hname(conn, b) == "Rohit Sharma" and b["routing_key"] == "Home|HIGH|East"
    assert sub(conn, "LOANV100001")["branch"] == "Auto Finance Hub"
    assert sub(conn, "LOANP100001")["branch"] == "Personal Credit Desk"
    assert sub(conn, "LOANE100001")["branch"] == "Education & Student Wing"

def test_14_unknown_zone_goes_to_central_fallback(conn):
    r = sub(conn, zone="Atlantis")
    assert r["queue"] == "CENTRAL_FALLBACK" and r["status"] == "Pending" and r["reason_code"] == "E401"
    assert r["handler_id"] is None and r["is_valid"] == 1

def test_15_capacity_overflow_escalates_to_backup(conn):
    rs = [sub(conn) for _ in range(4)]
    assert [hname(conn, x) for x in rs[:3]] == ["Meera Iyer"] * 3
    assert hname(conn, rs[3]) == "Ananya Rao" and "ESCALATION" in events(conn, rs[3]["report_id"])

def test_16_unavailable_handler_uses_backup_and_requeues_assigned(conn):
    first = sub(conn)
    eng.set_handler(conn, hid(conn, "Meera Iyer"), available=False)
    assert hname(conn, fresh(conn, first)) == "Ananya Rao"        # re-queued then escalated
    nxt = sub(conn)
    assert hname(conn, nxt) == "Ananya Rao"

def test_17_all_handlers_offline_waits_then_dispatches_on_recovery(conn):
    for i in home_handlers(conn):
        eng.set_handler(conn, i, available=False)
    r = sub(conn)
    assert r["status"] == "Pending" and r["queue"] == "WAITING" and "WAITING" in events(conn, r["report_id"])
    eng.set_handler(conn, hid(conn, "Meera Iyer"), available=True)
    assert fresh(conn, r)["status"] == "Assigned"

def test_18_critical_priority_override_exceeds_capacity(conn):
    for i in home_handlers(conn):
        eng.set_handler(conn, i, max_capacity=1)
    for _ in range(5):
        assert sub(conn)["status"] == "Assigned"           # primary, backup, other-band, cross-zone x2
    waiting = sub(conn)
    assert waiting["status"] == "Pending"
    crit = sub(conn, urg="Critical")
    assert crit["status"] == "Assigned" and "PRIORITY_OVERRIDE" in events(conn, crit["report_id"])
    assert conn.execute("SELECT MAX(current_load - max_capacity) FROM handlers").fetchone()[0] >= 1

def test_19_queue_order_is_priority_then_timestamp(conn):
    for i in home_handlers(conn):
        eng.set_handler(conn, i, available=False)
    n1, hi, crit, n2 = sub(conn), sub(conn, urg="High"), sub(conn, urg="Critical"), sub(conn)
    eng.set_handler(conn, hid(conn, "Meera Iyer"), max_capacity=1, available=True)
    assert fresh(conn, crit)["status"] == "Assigned" and fresh(conn, hi)["status"] == "Pending"
    eng.set_handler(conn, hid(conn, "Meera Iyer"), max_capacity=2)
    assert fresh(conn, hi)["status"] == "Assigned" and fresh(conn, n1)["status"] == "Pending"
    eng.set_handler(conn, hid(conn, "Meera Iyer"), max_capacity=3)
    assert fresh(conn, n1)["status"] == "Assigned" and fresh(conn, n2)["status"] == "Pending"   # FIFO among equals

def test_20_duplicate_application_id_prevented(conn):
    a = sub(conn, "LOANH555555")
    b = sub(conn, "LOANH555555")
    assert a["status"] == "Assigned" and b["reason_code"] == "E501" and b["handler_id"] is None
    assert conn.execute("SELECT COUNT(*) FROM reports WHERE application_code='LOANH555555' AND handler_id IS NOT NULL").fetchone()[0] == 1

def test_21_lifecycle_transitions_and_persistence(conn):
    r = sub(conn)
    assert eng.advance_status(conn, r["report_id"]) == "In Progress"
    assert eng.advance_status(conn, r["report_id"]) == "Resolved"
    with pytest.raises(ValueError):
        eng.advance_status(conn, r["report_id"])
    done = fresh(conn, r)
    assert done["resolved_at"] and conn.execute("SELECT current_load FROM handlers WHERE id=?", (r["handler_id"],)).fetchone()[0] == 0
    bad = sub(conn, "LOANX000001")
    with pytest.raises(ValueError):
        eng.advance_status(conn, bad["report_id"])

def test_22_resolving_frees_capacity_for_waiting_report(conn):
    for i in home_handlers(conn, keep=("Meera Iyer",)):
        eng.set_handler(conn, i, available=False)
    eng.set_handler(conn, hid(conn, "Meera Iyer"), max_capacity=1)
    a, b = sub(conn), sub(conn)
    assert b["status"] == "Pending"
    eng.advance_status(conn, a["report_id"]); eng.advance_status(conn, a["report_id"])
    assert fresh(conn, b)["status"] == "Assigned"

def test_23_seed_and_clean_start(conn):
    assert conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM handlers").fetchone()[0] == 20
    assert len(seed(conn)) > 15
    cats = {r[0] for r in conn.execute("SELECT DISTINCT category FROM reports")}
    assert cats == {"Home", "Vehicle", "Personal", "Education", "Invalid"}
    assert conn.execute("SELECT COUNT(*) FROM reports WHERE handler_id IS NOT NULL AND is_valid=0").fetchone()[0] == 0

def test_24_api_end_to_end(tmp_path):
    from app import create_app
    cl = create_app(str(tmp_path / "api.db")).test_client()
    body = dict(reporter_name="Asha", reporter_contact="9123456780", application_code="LOANE424242", income="800000", amount="900000", zone="North", urgency="High")
    rep = cl.post("/api/reports", json=body).get_json()["report"]
    assert rep["status"] == "Assigned" and rep["category"] == "Education"
    assert cl.get(f"/api/reports/{rep['report_id']}").get_json()["log"]
    assert cl.post("/api/reports", json=body).get_json()["report"]["reason_code"] == "E501"
    assert cl.post(f"/api/reports/{rep['report_id']}/advance").get_json()["status"] == "In Progress"
    assert cl.get("/api/stats").get_json()["total"] == 2


# ---------------- added: fixes for review findings ----------------
def test_25_money_dfa_equals_money_regex():
    assert len(MONEY_DFA.Q) == 14
    rnd = random.Random(502)
    for _ in range(5000):
        s = "".join(rnd.choice("0123456789..,-e ") for _ in range(rnd.randint(0, 13)))
        assert MONEY_DFA.run(s)["accepted"] == (MONEY_REGEX.fullmatch(s) is not None), s
    for s in ("1", "123456789", "1234567890", "12.5", "12.", ".5", "0.5", "12.345", "007"):
        assert MONEY_DFA.run(s)["accepted"] == (MONEY_REGEX.fullmatch(s) is not None), s
    assert validate_money("50000.50", "amount")["agree"]

def test_26_routing_key_only_from_validated_report(conn):
    bad, good = sub(conn, "LOANX000002"), sub(conn)
    with pytest.raises(ValueError):
        eng.extract_routing_key(bad)
    assert eng.extract_routing_key(good) == ("Home", "STANDARD", "South")

def test_27_assignment_and_start_timestamps_recorded(conn):
    r = sub(conn)
    assert r["assigned_at"] and not r["started_at"]
    eng.advance_status(conn, r["report_id"])
    after = fresh(conn, r)
    assert after["assigned_at"] == r["assigned_at"] and after["started_at"]

def test_28_only_four_statuses_ever_used(conn):
    seed(conn)
    assert {x[0] for x in conn.execute("SELECT DISTINCT status FROM reports")} <= {"Pending", "Assigned", "In Progress", "Resolved"}
    assert conn.execute("SELECT COUNT(*) FROM reports WHERE queue IN ('CENTRAL_CORRECTION','CENTRAL_FALLBACK')").fetchone()[0] >= 8

def test_29_fallback_report_can_be_resubmitted_with_corrected_zone(conn):
    first = sub(conn, "LOANH777777", zone="Atlantis")
    assert first["queue"] == "CENTRAL_FALLBACK"
    again = sub(conn, "LOANH777777", zone="South")
    assert again["status"] == "Assigned" and again["reason_code"] is None

def test_30_contact_validation():
    assert validate_application("LOANH104920", "1500000", "1000000", "Asha", "South", "9876543210")["is_valid"]
    for bad in ("", "12345", "5876543210", "98765432101", "98765abcde"):
        r = validate_application("LOANH104920", "1500000", "1000000", "Asha", "South", bad)
        assert not r["is_valid"] and r["reason_code"] == "E306"

def test_31_cross_band_then_cross_zone_escalation(conn):
    eng.set_handler(conn, hid(conn, "Meera Iyer"), available=False)
    eng.set_handler(conn, hid(conn, "Ananya Rao"), available=False)
    r = sub(conn)                                                   # South STANDARD: primary + backup down
    assert hname(conn, r) == "Neha Kapoor" and "other-band" in r["route_decision"]
    eng.set_handler(conn, hid(conn, "Neha Kapoor"), available=False)
    r2 = sub(conn)
    assert r2["status"] == "Assigned" and "cross-zone" in r2["route_decision"]

def test_32_keyword_false_positives_removed_and_unmapped_noted():
    assert classify("Home", "of course I want a house") == ("Home", None)
    assert classify("Vehicle", "bike for personal use")[1] is None
    cat, note = classify(None, "new car purchase")
    assert cat == "Invalid" and "Vehicle" in note
