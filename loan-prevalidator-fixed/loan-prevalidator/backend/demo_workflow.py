"""Item 13: full workflow demo.  Run: python demo_workflow.py"""
import os, tempfile
import database as db, routing_engine as eng

c = db.init_db(os.path.join(tempfile.mkdtemp(), "demo.db"))
def show(title, rid):
    r = c.execute("SELECT r.*, h.name hn FROM reports r LEFT JOIN handlers h ON h.id=r.handler_id WHERE report_id=?", (rid,)).fetchone()
    print(f"\n== {title}\n   id={rid} valid={bool(r['is_valid'])} category={r['category']} status={r['status']} queue={r['queue']} handler={r['hn']}")
    print("   decision:", r["route_decision"])
P = dict(reporter_name="Officer A", reporter_contact="9876543210", income="1800000", amount="6500000", zone="North", urgency="Normal", description="2BHK flat")
rid = eng.submit_report(c, {**P, "application_code": "LOANH104920"}); show("1 submit -> validate -> classify -> table lookup -> assign", rid)
for _ in range(2):
    print("   advance ->", eng.advance_status(c, rid))
show("2 resolved", rid)
show("3 malformed code -> correction queue", eng.submit_report(c, {**P, "application_code": "LOANH12A456"}))
show("4 unknown zone -> central fallback", eng.submit_report(c, {**P, "application_code": "LOANP220033", "zone": "Atlantis"}))
eng.set_handler(c, c.execute("SELECT id FROM handlers WHERE name='Rohit Sharma'").fetchone()[0], available=False)
show("5 primary offline -> escalation to backup", eng.submit_report(c, {**P, "application_code": "LOANH555555"}))
print("\nrouting log:"); [print("  ", e["event"], "|", (e["detail"] or "")[:90]) for e in c.execute("SELECT * FROM routing_log ORDER BY id")]
