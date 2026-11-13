"""SQLite persistence. Starts clean: only the pre-configured handlers + routing table exist.

Routing table (BCS502): one explicit row per (category, amount band, zone)
    -> branch, team (desk), primary handler, branch backup handler.
4 loan types x 2 bands x 5 zones = 40 rows. Built once from HANDLERS below.
"""
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get("LOAN_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "loan.db"))
ZONES = ["North", "South", "East", "West", "Central"]
BANDS = ["STANDARD", "HIGH"]
CATEGORY_BRANCH = {"Home": "Home Loans Division", "Vehicle": "Auto Finance Hub",
                   "Personal": "Personal Credit Desk", "Education": "Education & Student Wing"}
TEAM = {"STANDARD": "Standard Desk", "HIGH": "High-Value Desk", "ANY": "Backup Desk"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS handlers(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, branch TEXT NOT NULL, category TEXT NOT NULL,
  zones TEXT NOT NULL, band TEXT NOT NULL, team TEXT NOT NULL, is_backup INTEGER NOT NULL DEFAULT 0,
  max_capacity INTEGER NOT NULL, current_load INTEGER NOT NULL DEFAULT 0, available INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS routing_table(
  id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, band TEXT NOT NULL, zone TEXT NOT NULL,
  branch TEXT NOT NULL, team TEXT NOT NULL,
  primary_id INTEGER NOT NULL REFERENCES handlers(id), backup_id INTEGER NOT NULL REFERENCES handlers(id),
  UNIQUE(category, band, zone));
CREATE TABLE IF NOT EXISTS reports(
  id INTEGER PRIMARY KEY AUTOINCREMENT, report_id TEXT UNIQUE NOT NULL, reporter_name TEXT, reporter_contact TEXT,
  application_code TEXT, income TEXT, amount TEXT, zone TEXT, description TEXT, urgency TEXT, priority INTEGER,
  is_valid INTEGER NOT NULL, category TEXT NOT NULL, band TEXT, routing_key TEXT, reason_code TEXT, reason_text TEXT,
  dfa_accept INTEGER, regex_accept INTEGER, dfa_trace TEXT, conflict_note TEXT,
  status TEXT NOT NULL CHECK(status IN ('Pending','Assigned','In Progress','Resolved')),
  queue TEXT, branch TEXT, handler_id INTEGER REFERENCES handlers(id),
  route_decision TEXT, created_at TEXT NOT NULL, assigned_at TEXT, started_at TEXT, updated_at TEXT NOT NULL, resolved_at TEXT);
-- one *live* application per code; a report parked in the fallback queue (unknown zone) may be resubmitted
CREATE UNIQUE INDEX IF NOT EXISTS ux_valid_code ON reports(application_code)
  WHERE is_valid=1 AND COALESCE(queue,'')<>'CENTRAL_FALLBACK';
CREATE TABLE IF NOT EXISTS routing_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, report_id TEXT, event TEXT NOT NULL, detail TEXT);
"""

NE, SWC, ALL = "North,East", "South,West,Central", ",".join(ZONES)
# (name, category, band, zones served, is_backup, max_capacity)
HANDLERS = [
    ("Kiran Joshi", "Home", "STANDARD", NE, 0, 3), ("Meera Iyer", "Home", "STANDARD", SWC, 0, 3),
    ("Rohit Sharma", "Home", "HIGH", NE, 0, 2), ("Neha Kapoor", "Home", "HIGH", SWC, 0, 2),
    ("Ananya Rao", "Home", "ANY", ALL, 1, 3),
    ("Manoj Tiwari", "Vehicle", "STANDARD", NE, 0, 3), ("Karthik Nair", "Vehicle", "STANDARD", SWC, 0, 3),
    ("Sanjay Gill", "Vehicle", "HIGH", NE, 0, 2), ("Vikram Singh", "Vehicle", "HIGH", SWC, 0, 2),
    ("Deepa Menon", "Vehicle", "ANY", ALL, 1, 3),
    ("Rekha Das", "Personal", "STANDARD", NE, 0, 3), ("Sneha Kulkarni", "Personal", "STANDARD", SWC, 0, 3),
    ("Arjun Mehta", "Personal", "HIGH", NE, 0, 2), ("Tara Bhatt", "Personal", "HIGH", SWC, 0, 2),
    ("Farhan Ali", "Personal", "ANY", ALL, 1, 3),
    ("Amit Saxena", "Education", "STANDARD", NE, 0, 3), ("Priya Natarajan", "Education", "STANDARD", SWC, 0, 3),
    ("Rahul Verma", "Education", "HIGH", NE, 0, 2), ("Lata Pillai", "Education", "HIGH", SWC, 0, 2),
    ("Kavya Reddy", "Education", "ANY", ALL, 1, 3),
]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def get_conn(path=None):
    c = sqlite3.connect(path or DB_PATH, timeout=10, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _build_routing_table(c):
    for cat, branch in CATEGORY_BRANCH.items():
        backup = c.execute("SELECT id FROM handlers WHERE category=? AND is_backup=1", (cat,)).fetchone()[0]
        for band in BANDS:
            for zone in ZONES:
                prim = c.execute("SELECT id FROM handlers WHERE category=? AND band=? AND is_backup=0 "
                                 "AND (','||zones||',') LIKE ?", (cat, band, f"%,{zone},%")).fetchone()[0]
                c.execute("INSERT INTO routing_table(category,band,zone,branch,team,primary_id,backup_id) VALUES(?,?,?,?,?,?,?)",
                          (cat, band, zone, branch, TEAM[band], prim, backup))


def init_db(path=None):
    c = get_conn(path)
    cols = [r[1] for r in c.execute("PRAGMA table_info(handlers)")]
    if cols and "zones" not in cols:
        c.close()
        raise RuntimeError("Old database schema detected - delete backend/loan.db and start again.")
    c.executescript(SCHEMA)
    if c.execute("SELECT COUNT(*) FROM handlers").fetchone()[0] == 0:
        c.executemany("INSERT INTO handlers(name,branch,category,zones,band,team,is_backup,max_capacity) VALUES(?,?,?,?,?,?,?,?)",
                      [(n, CATEGORY_BRANCH[cat], cat, z, b, TEAM[b], bk, cap) for n, cat, b, z, bk, cap in HANDLERS])
    if c.execute("SELECT COUNT(*) FROM routing_table").fetchone()[0] == 0:
        _build_routing_table(c)
    c.commit()
    return c
