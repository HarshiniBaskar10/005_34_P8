"""Flask API for the P8 Loan Application Pre-Validator."""
import json
import os
import threading
from contextlib import closing
from flask import Flask, jsonify, request, send_from_directory
try:
    from flask_cors import CORS
except ImportError:          # same-origin deployment (Flask serves the UI) does not need CORS
    CORS = lambda app, *a, **k: app
import database as db
import routing_engine as eng
from dfa_engine import (CATEGORIES, DFA_SPEC, MONEY_DFA_SPEC, classify, validate_code, validate_contact, validate_money)
from seed_data import seed


DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")


def rd(r):
    d = dict(r)
    if "dfa_trace" in d:
        d["dfa_trace"] = json.loads(d["dfa_trace"] or "[]")
    return d


def create_app(db_path=None):
    app = Flask(__name__)
    CORS(app)
    path = db_path or db.DB_PATH
    db.init_db(path).close()
    lock = threading.Lock()   # serialises simultaneous submissions -> deterministic order, no duplicate assignment
    conn = lambda: db.get_conn(path)

    @app.get("/api/health")
    def health():
        return jsonify(ok=True)

    @app.get("/api/dfa")
    def dfa():
        return jsonify(**DFA_SPEC, money=MONEY_DFA_SPEC)

    @app.post("/api/validate")
    def validate():
        b = request.get_json(silent=True) or {}
        out = {"code": validate_code(b.get("application_code"))}
        cat, note = classify(out["code"]["category"] if out["code"]["ok"] else None, b.get("description"))
        out["classification"] = {"category": cat, "conflict_note": note}
        if b.get("reporter_contact"):
            out["contact"] = validate_contact(b["reporter_contact"])
        if b.get("income"):
            out["income"] = validate_money(b["income"], "income")
        if b.get("amount"):
            out["amount"] = validate_money(b["amount"], "amount")
        return jsonify(out)

    @app.post("/api/reports")
    def submit():
        b = request.get_json(silent=True)
        if not isinstance(b, dict):
            return jsonify(error="JSON body required"), 400
        with lock, closing(conn()) as c:
            rid = eng.submit_report(c, b)
            return jsonify(report=rd(c.execute("SELECT * FROM reports WHERE report_id=?", (rid,)).fetchone())), 201

    @app.get("/api/reports/<rid>")
    def one(rid):
        with closing(conn()) as c:
            r = c.execute("SELECT r.*, h.name AS handler_name FROM reports r LEFT JOIN handlers h ON h.id=r.handler_id WHERE report_id=?", (rid.upper(),)).fetchone()
            if r is None:
                return jsonify(error=f"No report found with ID {rid}"), 404
            lg = [dict(x) for x in c.execute("SELECT ts,event,detail FROM routing_log WHERE report_id=? ORDER BY id", (r["report_id"],))]
            return jsonify(report=rd(r), log=lg)

    @app.get("/api/reports")
    def many():
        q, args = "SELECT r.*, h.name AS handler_name FROM reports r LEFT JOIN handlers h ON h.id=r.handler_id WHERE 1=1", []
        for col in ("handler_id", "status", "queue"):
            if request.args.get(col):
                q += f" AND r.{col}=?"
                args.append(request.args[col])
        q += (" ORDER BY r.created_at DESC, r.id DESC LIMIT 500" if request.args.get("sort") == "recent"
              else " ORDER BY r.priority, r.created_at, r.id LIMIT 500")
        with closing(conn()) as c:
            return jsonify(reports=[rd(x) for x in c.execute(q, args)])

    @app.post("/api/reports/<rid>/advance")
    def advance(rid):
        with lock, closing(conn()) as c:
            try:
                return jsonify(status=eng.advance_status(c, rid.upper()))
            except LookupError as e:
                return jsonify(error=str(e)), 404
            except ValueError as e:
                return jsonify(error=str(e)), 409

    @app.get("/api/handlers")
    def handlers():
        with closing(conn()) as c:
            return jsonify(handlers=[dict(x) for x in c.execute("SELECT * FROM handlers ORDER BY id")])

    @app.patch("/api/handlers/<int:hid>")
    def patch_handler(hid):
        b = request.get_json(silent=True) or {}
        if "max_capacity" in b and (isinstance(b["max_capacity"], bool) or not isinstance(b["max_capacity"], int)):
            return jsonify(error="max_capacity must be an integer between 0 and 50"), 400
        with lock, closing(conn()) as c:
            try:
                eng.set_handler(c, hid, b.get("available"), b.get("max_capacity"))
            except LookupError as e:
                return jsonify(error=str(e)), 404
            except ValueError as e:
                return jsonify(error=str(e)), 400
            return jsonify(handler=dict(c.execute("SELECT * FROM handlers WHERE id=?", (hid,)).fetchone()))

    @app.get("/api/stats")
    def stats():
        with closing(conn()) as c:
            n = lambda w: c.execute(f"SELECT COUNT(*) FROM reports WHERE {w}").fetchone()[0]
            return jsonify(total=n("1=1"), pending=n("status='Pending' AND queue='WAITING'"), assigned=n("status='Assigned'"),
                           in_progress=n("status='In Progress'"), resolved=n("status='Resolved'"),
                           correction=n("queue IN ('CENTRAL_CORRECTION','CENTRAL_FALLBACK')"))

    @app.get("/api/routing")
    def routing():
        with closing(conn()) as c:
            g = lambda sql: [rd(x) for x in c.execute(sql)]
            return jsonify(
                handlers=[dict(x) for x in c.execute("SELECT * FROM handlers ORDER BY id")],
                table=g("""SELECT t.category,t.band,t.zone,t.branch,t.team,p.name AS primary_name,b.name AS backup_name
                           FROM routing_table t JOIN handlers p ON p.id=t.primary_id JOIN handlers b ON b.id=t.backup_id
                           ORDER BY t.id"""),
                waiting=g("SELECT * FROM reports WHERE queue='WAITING' ORDER BY priority, created_at, id"),
                correction=g("SELECT * FROM reports WHERE queue IN ('CENTRAL_CORRECTION','CENTRAL_FALLBACK') ORDER BY created_at DESC"),
                log=[dict(x) for x in c.execute("SELECT * FROM routing_log ORDER BY id DESC LIMIT 150")],
                band_limit=eng.BAND_LIMIT, zones=db.ZONES)

    @app.get("/api/analytics")
    def analytics():
        with closing(conn()) as c:
            zones = [dict(x) for x in c.execute("SELECT CASE WHEN zone='' THEN '(blank)' ELSE zone END name, COUNT(*) value FROM reports GROUP BY zone ORDER BY value DESC")]
            cat = {r["category"]: r["n"] for r in c.execute("SELECT category, COUNT(*) n FROM reports GROUP BY category")}
            res = c.execute("SELECT SUM(status='Resolved') a, SUM(status!='Resolved') b FROM reports").fetchone()
            return jsonify(zones=zones, categories=[{"name": k, "value": cat.get(k, 0)} for k in CATEGORIES],
                           resolution=[{"name": "Resolved", "value": res["a"] or 0}, {"name": "Unresolved", "value": res["b"] or 0}])

    @app.post("/api/seed")
    def do_seed():
        with lock, closing(conn()) as c:
            if c.execute("SELECT COUNT(*) FROM reports").fetchone()[0]:
                return jsonify(error="Database already contains reports. Reset first to re-seed."), 409
            return jsonify(created=len(seed(c)))

    @app.post("/api/reset")
    def reset():
        with lock, closing(conn()) as c:
            eng.reset_reports(c)
            return jsonify(ok=True)

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def spa(path):   # serves the built React app in production
        if path.startswith("api/"):
            return jsonify(error="Not found"), 404
        if path and os.path.isfile(os.path.join(DIST, path)):
            return send_from_directory(DIST, path)
        if os.path.isfile(os.path.join(DIST, "index.html")):
            return send_from_directory(DIST, "index.html")
        return jsonify(message="API running. Build the frontend (npm run build) or use the Vite dev server."), 200

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
