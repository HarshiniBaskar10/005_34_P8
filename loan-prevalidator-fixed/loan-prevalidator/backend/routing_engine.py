"""BCS502 - Computer Networks: explicit routing table, dispatch algorithm, queues, escalation.

ROUTING TABLE (table `routing_table`, 40 rows):  key (category, band, zone) -> branch, team, primary handler, backup handler.
  4 approval branches (Home / Vehicle / Personal / Education), each with a STANDARD and a HIGH-value desk, per zone.
  Band: amount >= BAND_LIMIT -> HIGH, else STANDARD  (assumption: Rs 25,00,000).

DISPATCH (per report, routing key extracted ONLY from a validated report):
  0 unknown zone / no table row -> CENTRAL_FALLBACK queue (status Pending, reason E401)
  1 table primary eligible       -> ROUTED
  2 branch backup eligible       -> ESCALATION
  3 other-band desk, same zone   -> ESCALATION
  4 any branch handler (cross-zone, least loaded) -> ESCALATION
  5 PRIORITY OVERRIDE (documented emergency rule): urgency Critical may exceed the capacity of an available
    branch handler (primary preferred, else least loaded)
  6 otherwise                    -> WAITING queue (status Pending)
Eligible = available AND current_load < max_capacity.
Queue order is deterministic: (priority, created_at, id); Critical=0 < High=1 < Normal=2.
Statuses are exactly: Pending -> Assigned -> In Progress -> Resolved. Rejected reports stay Pending in a
correction/fallback QUEUE (never dispatched).
"""
import json
import uuid
from database import ZONES, get_conn, now
from dfa_engine import classify, validate_application

URGENCY_PRIORITY = {"Critical": 0, "High": 1, "Normal": 2}
BAND_LIMIT = 2_500_000          # amount >= limit -> HIGH band
NEXT_STATUS = {"Assigned": "In Progress", "In Progress": "Resolved"}


def band_for(amount):
    return "HIGH" if float(amount) >= BAND_LIMIT else "STANDARD"


def extract_routing_key(r):
    """Routing key (category, band, zone) - only a validated report has one."""
    if not r["is_valid"]:
        raise ValueError("Routing key can only be extracted from a validated report")
    return r["category"], r["band"], r["zone"]


def log(conn, rid, event, detail):
    conn.execute("INSERT INTO routing_log(ts,report_id,event,detail) VALUES(?,?,?,?)", (now(), rid, event, detail))


def refresh_loads(conn):
    conn.execute("""UPDATE handlers SET current_load=(SELECT COUNT(*) FROM reports r
                    WHERE r.handler_id=handlers.id AND r.status IN ('Assigned','In Progress'))""")


def _route(conn, category, band, zone):
    return conn.execute("SELECT * FROM routing_table WHERE category=? AND band=? AND zone=?", (category, band, zone)).fetchone()


def _assign(conn, r, h, event, why):
    others = conn.execute("SELECT COUNT(*) FROM reports WHERE queue='WAITING' AND category=? AND priority>? AND id!=?",
                          (r["category"], r["priority"], r["id"])).fetchone()[0]
    decision = (f"key=({r['category']},{r['band']},{r['zone']}) -> {h['branch']} / {h['team']} / {h['name']} "
                f"[{h['zones']}, {'backup' if h['is_backup'] else 'primary'}] priority={r['urgency']}; {why}")
    ts = now()
    conn.execute("""UPDATE reports SET handler_id=?,branch=?,status='Assigned',queue=NULL,route_decision=?,
                    assigned_at=?,updated_at=? WHERE id=?""", (h["id"], h["branch"], decision, ts, ts, r["id"]))
    refresh_loads(conn)
    log(conn, r["report_id"], event, decision)
    if r["priority"] == 0 and event != "PRIORITY_OVERRIDE" and others:
        log(conn, r["report_id"], "PRIORITY_OVERRIDE", f"Critical report dispatched ahead of {others} lower-priority queued report(s).")
    return True


def _attempt(conn, r):
    category, band, zone = extract_routing_key(r)
    hs = {h["id"]: dict(h) for h in conn.execute("SELECT * FROM handlers WHERE category=? ORDER BY id", (category,))}
    ok = lambda h: h["available"] and h["current_load"] < h["max_capacity"]
    ratio = lambda h: h["current_load"] / max(h["max_capacity"], 1)
    row = _route(conn, category, band, zone)
    if row is None:
        return False
    primary, backup = hs[row["primary_id"]], hs[row["backup_id"]]
    if ok(primary):
        return _assign(conn, r, primary, "ROUTED", "routing-table primary available")
    if ok(backup):
        return _assign(conn, r, backup, "ESCALATION", "primary unavailable/at capacity -> branch backup")
    other = _route(conn, category, "HIGH" if band == "STANDARD" else "STANDARD", zone)
    if other and ok(hs[other["primary_id"]]):
        return _assign(conn, r, hs[other["primary_id"]], "ESCALATION", "backup unavailable -> other-band desk, same zone")
    pool = sorted([h for h in hs.values() if not h["is_backup"] and ok(h)], key=lambda h: (ratio(h), h["id"]))
    if pool:
        return _assign(conn, r, pool[0], "ESCALATION", "no same-zone handler free -> cross-zone handler in branch")
    if r["priority"] == 0:
        pool = sorted([h for h in hs.values() if h["available"]], key=lambda h: (0 if h["id"] == primary["id"] else 1, ratio(h), h["id"]))
        if pool:
            return _assign(conn, r, pool[0], "PRIORITY_OVERRIDE", "Critical urgency overrides capacity limit")
    return False


def drain_queue(conn, new_rid=None):
    waiting = conn.execute("SELECT * FROM reports WHERE queue='WAITING' AND handler_id IS NULL ORDER BY priority, created_at, id").fetchall()
    for r in waiting:
        if not _attempt(conn, r) and r["report_id"] == new_rid:
            log(conn, r["report_id"], "WAITING", f"No eligible handler in {r['category']} branch; placed in waiting queue (priority {r['urgency']}).")


def _insert(conn, f):
    cols = ",".join(f)
    conn.execute(f"INSERT INTO reports({cols}) VALUES({','.join('?' * len(f))})", list(f.values()))


def submit_report(conn, p):
    """Full pipeline: validate -> classify -> (dedupe) -> route -> assign. Returns report_id."""
    ts, rid = now(), "RPT-" + uuid.uuid4().hex[:8].upper()
    code, zone = (p.get("application_code") or ""), (p.get("zone") or "").strip().title()
    urgency = p.get("urgency") or "Normal"
    contact = (p.get("reporter_contact") or "").strip()
    v = validate_application(code, p.get("income"), p.get("amount"), p.get("reporter_name") or "", zone, contact)
    errors = list(v["errors"])
    if urgency not in URGENCY_PRIORITY:
        errors.append({"field": "urgency", "code": "E305", "reason": "Urgency must be Normal, High or Critical."})
    if not errors and conn.execute("SELECT 1 FROM reports WHERE application_code=? AND is_valid=1 AND COALESCE(queue,'')<>'CENTRAL_FALLBACK'", (code,)).fetchone():
        errors.append({"field": "application_code", "code": "E501", "reason": f"Duplicate application ID {code}: already submitted."})
    cr = v["code_result"]
    base = dict(report_id=rid, reporter_name=(p.get("reporter_name") or "").strip(), reporter_contact=contact,
                application_code=code, income=str(p.get("income") or ""), amount=str(p.get("amount") or ""), zone=zone,
                description=p.get("description") or "", urgency=urgency, priority=URGENCY_PRIORITY.get(urgency, 2),
                dfa_accept=int(cr["dfa_accept"]), regex_accept=int(cr["regex_accept"]),
                dfa_trace=json.dumps(cr["trace"]), created_at=ts, updated_at=ts)
    if errors:   # rejected BEFORE dispatch: stays Pending in the correction queue
        _, note = classify(None, p.get("description"))
        _insert(conn, {**base, "is_valid": 0, "category": "Invalid", "reason_code": errors[0]["code"],
                       "reason_text": errors[0]["reason"], "status": "Pending", "queue": "CENTRAL_CORRECTION",
                       "conflict_note": note, "route_decision": f"Rejected before dispatch: {errors[0]['code']}"})
        log(conn, rid, "REJECTED", f"{errors[0]['code']}: {errors[0]['reason']}")
        conn.commit()
        return rid
    category, note = classify(cr["category"], p.get("description"))
    band = band_for(p["amount"])
    row = {**base, "is_valid": 1, "category": category, "band": band, "conflict_note": note,
           "routing_key": f"{category}|{band}|{zone}", "status": "Pending", "queue": "WAITING"}
    if zone not in ZONES:   # unknown routing key -> documented central fallback
        row.update(queue="CENTRAL_FALLBACK", reason_code="E401",
                   reason_text=f"Unknown zone '{zone}'. Valid zones: {', '.join(ZONES)}.",
                   route_decision="Unknown zone -> Central Fallback Queue")
        _insert(conn, row)
        log(conn, rid, "FALLBACK", row["reason_text"])
    else:
        _insert(conn, row)
        if note:
            log(conn, rid, "CLASSIFY", note)
        drain_queue(conn, rid)
    conn.commit()
    return rid


def advance_status(conn, rid):
    r = conn.execute("SELECT * FROM reports WHERE report_id=?", (rid,)).fetchone()
    if r is None:
        raise LookupError("Report not found")
    if r["queue"] in ("CENTRAL_CORRECTION", "CENTRAL_FALLBACK"):
        raise ValueError("Report is in the correction/fallback queue; correct it and resubmit - it cannot be worked.")
    nxt = NEXT_STATUS.get(r["status"])
    if nxt is None:
        raise ValueError(f"Illegal transition from '{r['status']}'. Allowed: Assigned -> In Progress -> Resolved.")
    ts = now()
    conn.execute("UPDATE reports SET status=?,updated_at=?,started_at=COALESCE(?,started_at),resolved_at=? WHERE id=?",
                 (nxt, ts, ts if nxt == "In Progress" else None, ts if nxt == "Resolved" else None, r["id"]))
    refresh_loads(conn)
    log(conn, rid, "STATUS", f"{r['status']} -> {nxt}")
    drain_queue(conn)
    conn.commit()
    return nxt


def set_handler(conn, hid, available=None, max_capacity=None):
    h = conn.execute("SELECT * FROM handlers WHERE id=?", (hid,)).fetchone()
    if h is None:
        raise LookupError("Handler not found")
    if max_capacity is not None:
        if isinstance(max_capacity, bool) or not isinstance(max_capacity, int) or not 0 <= max_capacity <= 50:
            raise ValueError("max_capacity must be an integer between 0 and 50")
        conn.execute("UPDATE handlers SET max_capacity=? WHERE id=?", (max_capacity, hid))
        log(conn, None, "CAPACITY", f"{h['name']} max capacity -> {max_capacity}")
    if available is not None:
        conn.execute("UPDATE handlers SET available=? WHERE id=?", (int(bool(available)), hid))
        log(conn, None, "AVAILABILITY", f"{h['name']} -> {'Available' if available else 'Offline'}")
        if not available:   # re-queue work not yet started
            for r in conn.execute("SELECT * FROM reports WHERE handler_id=? AND status='Assigned'", (hid,)).fetchall():
                conn.execute("UPDATE reports SET handler_id=NULL,branch=NULL,assigned_at=NULL,status='Pending',queue='WAITING',updated_at=? WHERE id=?", (now(), r["id"]))
                log(conn, r["report_id"], "ESCALATION", f"Handler {h['name']} went offline; report re-queued for backup/escalation.")
    refresh_loads(conn)
    drain_queue(conn)
    conn.commit()


def reset_reports(conn):
    conn.execute("DELETE FROM reports")
    conn.execute("DELETE FROM routing_log")
    refresh_loads(conn)
    conn.commit()
